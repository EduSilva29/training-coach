import datetime
from .client import get_db

def get_conversations_collection():
    return get_db()["conversations"]

def save_message(role, content):
    """Saves a single turn (user or assistant) to MongoDB."""
    col = get_conversations_collection()
    doc = {
        "role": role,
        "content": content,
        "timestamp": datetime.datetime.now(datetime.timezone.utc)
    }
    col.insert_one(doc)
    return doc

def get_chat_history(limit=50):
    """Fetches recent chat messages in chronological order for display & AI context (filters out transient error messages)."""
    col = get_conversations_collection()
    # Filter out any transient error strings starting with ❌ so they never pollute UI or prompts
    cursor = col.find(
        {"content": {"$not": {"$regex": "^❌"}}},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit)
    messages = list(cursor)
    messages.reverse()
    return messages

def clear_chat_history():
    """Wipes conversation history if the athlete wants a clean slate."""
    col = get_conversations_collection()
    col.delete_many({})
