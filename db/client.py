import os
from dotenv import load_dotenv
from pymongo import MongoClient
from config import get_setting

# Load environment variables
load_dotenv()

_client = None

def get_db():
    """Returns a singleton MongoDB database instance."""
    global _client
    if _client is None:
        mongo_uri = get_setting("MONGO_URI")
        if not mongo_uri:
            raise ValueError("MONGO_URI is not set in environment or .env file.")
        _client = MongoClient(mongo_uri)
    return _client[get_setting("MONGO_DB_NAME", "running_coach")]
