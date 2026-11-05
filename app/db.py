from pymongo import MongoClient

_client = None
_db = None


def init_db(app):
    global _client, _db
    _client = MongoClient(app.config["MONGODB_URI"], serverSelectionTimeoutMS=3000)
    _db = _client[app.config["DB_NAME"]]


def get_db():
    return _db


def ping_db():
    _client.admin.command("ping")
