from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from pymongo import MongoClient
import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend interaction
bcrypt = Bcrypt(app)

# ✅ FIXED: Use proper environment variable names
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')  
jwt = JWTManager(app)

# ✅ FIXED: Use the correct MongoDB URI from environment variables
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.travel_bot

# Collections
users_collection = db.users
responses_collection = db.responses
questionnaire_collection = db.questionnaires  # New collection for questionnaire responses

# ✅ FIXED: Use environment variable for OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

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

# Chat route
@app.route('/chat', methods=['POST'])
@jwt_required()
def chat():
    try:
        user_message = request.json.get("message", "").lower()
        username = get_jwt_identity()

        response = responses_collection.find_one({"key": {"$regex": f".*{user_message}.*", "$options": "i"}})

        if response:
            return jsonify({"reply": response['reply'], "user": username})

        openai_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful travel assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        bot_reply = openai_response.choices[0].message['content']
        return jsonify({"reply": bot_reply, "user": username})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

# ✅ FIXED: Ensure the app runs on the correct port
if __name__ == '__main__':
    port = int(os.getenv("PORT", 10000))  # Use Render's assigned port or default to 10000
    app.run(debug=False, host="0.0.0.0", port=port)
