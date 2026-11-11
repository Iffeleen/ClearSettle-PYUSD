import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "clearsettle")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # reject uploads over 5 MB
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set COOKIE_SECURE=1 on the https server. Leave unset locally (http).
    SESSION_COOKIE_SECURE = os.getenv("COOKIE_SECURE") == "1"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set COOKIE_SECURE=1 on the https server. Leave unset locally (http).
    SESSION_COOKIE_SECURE = os.getenv("COOKIE_SECURE") == "1"
