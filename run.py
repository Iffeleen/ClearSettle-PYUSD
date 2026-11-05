import os
from dotenv import load_dotenv
from flask import Flask, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()  # reads the .env file into environment variables

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

mongo_client = MongoClient(os.getenv("MONGODB_URI"), serverSelectionTimeoutMS=2000)
db = mongo_client[os.getenv("DB_NAME", "clearsettle")]


@app.route("/")
def home():
    return "ClearSettle PYUSD is running"


@app.route("/health")
def health():
    try:
        mongo_client.admin.command("ping")
        return jsonify({"status": "ok", "database": "connected"})
    except PyMongoError:
        return jsonify({"status": "error", "database": "unreachable"}), 503


if __name__ == "__main__":
    app.run(port=5001, debug=True)