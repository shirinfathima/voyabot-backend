from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
from pymongo import MongoClient
import openai
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend interaction
bcrypt = Bcrypt(app)
app.config['JWT_SECRET_KEY'] = '8ded9ea94e8a7ecaf5078a0fc2d6df2254b11a33381b915b70ab4f0aa4146ae0'  # Change this to a strong secret key
jwt = JWTManager(app)

# Connect to MongoDB Atlas
MONGO_URI = "mongodb+srv://shirinfathima003:ANhx61RJQ47TKc33@cluster1.9dyv4.mongodb.net/travel_bot?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client.travel_bot

# Collections
users_collection = db.users
responses_collection = db.responses
questionnaire_collection = db.questionnaires  # New collection for questionnaire responses

# OpenAI API Key
openai.api_key = "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"

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

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)
