from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from pymongo import MongoClient
import os
from dotenv import load_dotenv
import requests
import time
import google.generativeai as genai  # Import Gemini

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend interaction
bcrypt = Bcrypt(app)

# Configure JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
jwt = JWTManager(app)

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # Set Gemini API key

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.travel_bot

# Collections
users_collection = db.users
responses_collection = db.responses
questionnaire_collection = db.questionnaires
questions_collection = db.questions  # New collection for questions

# Amadeus API credentials and URLs
API_KEY = os.getenv("AMADEUS_API_KEY")
API_SECRET = os.getenv("AMADEUS_API_SECRET")
AMADEUS_TOKEN_URL = os.getenv("AMADEUS_TOKEN_URL")
AMADEUS_FLIGHT_SEARCH_URL = os.getenv("AMADEUS_FLIGHT_SEARCH_URL")
AMADEUS_HOTEL_SEARCH_URL = os.getenv("AMADEUS_HOTEL_SEARCH_URL")
AMADEUS_PLACE_RECOMMENDATIONS_URL = os.getenv("AMADEUS_PLACE_RECOMMENDATIONS_URL")

# Store the token and expiry time
access_token = None
token_expiry = 0  # Stores UNIX timestamp

# Amadeus API functions
def get_access_token():
    """Get Amadeus API access token (handles token caching)."""
    global access_token, token_expiry
    if access_token and time.time() < token_expiry:
        return access_token
    url = AMADEUS_TOKEN_URL
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": API_SECRET
    }
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        json_response = response.json()
        access_token = json_response["access_token"]
        token_expiry = time.time() + json_response["expires_in"]
        return access_token
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Amadeus token: {e}")
        return None

def search_flights(origin, destination, departure_date, adults=1):
    """Search for flights using Amadeus API."""
    token = get_access_token()
    if not token:
        return None
    url = AMADEUS_FLIGHT_SEARCH_URL
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": departure_date,
        "adults": adults,
        "currencyCode": "INR",  # Changed to INR
        "max": 5
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching flights: {e}")
        return None

def search_hotels(city_code, check_in, check_out, adults=1):
    """Search for hotels using Amadeus API."""
    token = get_access_token()
    if not token:
        return None
    url = AMADEUS_HOTEL_SEARCH_URL
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    params = {
        "cityCode": city_code,
        "checkInDate": check_in,
        "checkOutDate": check_out,
        "adults": adults,
        "currency": "INR",  # Changed to INR
        "radius": 5,
        "radiusUnit": "KM",
        "paymentPolicy": "NONE",
        "includeClosed": False,
        "bestRateOnly": True,
        "view": "FULL"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching hotels: {e}")
        return None

def get_place_recommendations(latitude, longitude):
    """Get place recommendations using Amadeus API."""
    token = get_access_token()
    if not token:
        return None
    url = AMADEUS_PLACE_RECOMMENDATIONS_URL
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "radius": 10,
        "category": "SIGHTS",  # Options: SIGHTS, NIGHTLIFE, RESTAURANT, SHOPPING
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching places: {e}")
        return None

# Home route
@app.route('/')
def home():
    return jsonify({"message": "Voyabot backend is running!"})

# Signup route
@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({"message": "Username and password are required"}), 400
        if users_collection.find_one({'username': username}):
            return jsonify({"message": "Username already exists"}), 400
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        users_collection.insert_one({'username': username, 'password': hashed_password})
        return jsonify({"message": "User registered successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Login route
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({"message": "Username and password are required"}), 400
        user = users_collection.find_one({'username': username})
        if user and bcrypt.check_password_hash(user['password'], password):
            access_token = create_access_token(identity=username)
            return jsonify({"message": "Login successful", "token": access_token}), 200
        return jsonify({"message": "Invalid username or password"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Webhook route for Dialogflow
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "No data received"}), 400

        intent_name = data['queryResult']['intent']['displayName']
        parameters = data['queryResult']['parameters']

        if intent_name == "Find_Flight":
            departure_city = parameters.get("departure_city", "")
            destination_city = parameters.get("destination_city", "")
            departure_date = parameters.get("date-time", "")

            if not departure_city or not destination_city or not departure_date:
                return jsonify({"fulfillmentText": "Please provide departure city, destination, and date."})

            # Call the Amadeus API
            flight_data = search_flights(departure_city, destination_city, departure_date)
            if flight_data and "data" in flight_data and flight_data["data"]:
                flights = flight_data["data"]
                response_text = f"Found {len(flights)} flights from {departure_city} to {destination_city}:\n"
                for flight in flights:
                    airline = flight["itineraries"][0]["segments"][0]["carrierCode"]
                    price = float(flight["price"]["total"])
                    departure_time = flight["itineraries"][0]["segments"][0]["departure"]["at"]
                    response_text += f"- {airline} flight at {departure_time} for ₹{price:.2f}\n"
            else:
                response_text = "No flights found for the given details."

            return jsonify({"fulfillmentText": response_text})

        elif intent_name == "Find_Hotel":
            city = parameters.get("city", "")
            check_in = parameters.get("date-checkin", "")
            check_out = parameters.get("date-checkout", "")

            if not city or not check_in or not check_out:
                return jsonify({"fulfillmentText": "Please provide city, check-in date, and check-out date."})

            # Call the Amadeus API
            hotel_data = search_hotels(city, check_in, check_out)
            if hotel_data and "data" in hotel_data and hotel_data["data"]:
                hotels = hotel_data["data"]
                response_text = f"Found {len(hotels)} hotels in {city}:\n"
                for hotel in hotels:
                    name = hotel["name"]
                    price = float(hotel["price"]["total"])
                    response_text += f"- {name} for ₹{price:.2f}\n"
            else:
                response_text = "No hotels found for the given details."

            return jsonify({"fulfillmentText": response_text})

        elif intent_name == "Place_Recommendation":
            city = parameters.get("city", "")
            place_type = parameters.get("place-type", "")

            if not city:
                return jsonify({"fulfillmentText": "Please provide a city."})

            # Call the Amadeus API
            place_data = get_place_recommendations(city, place_type)
            if place_data and "data" in place_data and place_data["data"]:
                places = place_data["data"]
                response_text = f"Found {len(places)} {place_type} recommendations in {city}:\n"
                for place in places:
                    name = place["name"]
                    response_text += f"- {name}\n"
            else:
                response_text = "No recommendations found for the given details."

            return jsonify({"fulfillmentText": response_text})

        else:
            return jsonify({"fulfillmentText": "I'm not sure how to help with that."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Chat route with Gemini integration
@app.route("/chat", methods=["POST"])
@jwt_required()
def chat():
    user_message = request.json.get("message")
    username = get_jwt_identity()

    if not user_message:
        return jsonify({"error": "Message is required"}), 400

    try:
        # Call the /webhook route directly
        with app.test_request_context(json={"message": user_message}):
            webhook_response = webhook()
            webhook_data = webhook_response.get_json()

            # Check if the response is a fallback message
            if webhook_data and "fulfillmentText" in webhook_data:
                fulfillment_text = webhook_data["fulfillmentText"]
                # If the response is a fallback message, fall back to Gemini
                if fulfillment_text.lower() in ["i'm not sure how to help with that.", "no matching intent found."]:
                    pass  # Fall back to Gemini
                else:
                    return jsonify({"reply": fulfillment_text, "user": username})

        # If /webhook doesn't have a meaningful response, fall back to Gemini
        for model in ["models/gemini-1.5-pro-latest", "models/gemini-1.5-flash-latest"]:
            try:
                response = genai.GenerativeModel(model_name=model).generate_content(user_message)
                if response and response.text:
                    return jsonify({"reply": response.text, "user": username})
                else:
                    continue  # Try the next model if no response
            except Exception as e:
                error_message = str(e)
                if "model_not_found" in error_message or "quota_exceeded" in error_message:
                    print(f"{model} not available, switching to next model...")
                    continue  # Try the next model
                else:
                    return jsonify({"error": f"Gemini API error: {error_message}"}), 500

        return jsonify({"error": "Both Gemini-1.5-pro and Gemini-1.5-flash failed. Please try again later."}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

# Questionnaire submission route
@app.route('/submit_questionnaire', methods=['POST'])
@jwt_required()
def submit_questionnaire():
    try:
        data = request.json
        username = get_jwt_identity()
        if not data:
            return jsonify({"message": "No data provided"}), 400
        questionnaire_data = {
            "username": username,
            "responses": data
        }
        questionnaire_collection.insert_one(questionnaire_data)
        return jsonify({"message": "Questionnaire submitted successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Fetch questions from MongoDB
@app.route('/get_questions', methods=['GET'])
def get_questions():
    try:
        questions = list(questions_collection.find({}, {"_id": 0}))
        return jsonify(questions), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the app
if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))
    app.run(debug=False, host="0.0.0.0", port=port)
