from .client import get_db

def get_activities_collection():
    return get_db()["activities"]

def upsert_activity(clean_doc):
    """Inserts a new activity or updates if activity_id already exists."""
    col = get_activities_collection()
    return col.update_one(
        {"activity_id": clean_doc["activity_id"]},
        {"$set": clean_doc},
        upsert=True
    )

def get_recent_activities(limit=10):
    """Returns the most recent activities formatted, newest first."""
    col = get_activities_collection()
    cursor = col.find({}, {"_id": 0}).sort("metadata.start_time", -1).limit(limit)
    return list(cursor)

def get_total_distance_last_n_days(days=7):
    """Calculates total running mileage for the last N days."""
    col = get_activities_collection()
    # Simple query or iteration
    activities = get_recent_activities(limit=50)
    # Could filter by start_time if needed
    return sum(a.get("metadata", {}).get("total_distance_km", 0) for a in activities)
