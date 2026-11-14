import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB_NAME", "running_coach")

_client = None

def get_db():
    """Returns a singleton MongoDB database instance."""
    global _client
    if _client is None:
        if not MONGO_URI:
            raise ValueError("MONGO_URI is not set in environment or .env file.")
        _client = MongoClient(MONGO_URI)
    return _client[DB_NAME]
