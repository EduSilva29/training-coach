from .client import get_db

def get_recovery_collection():
    return get_db()["daily_recovery"]

def upsert_daily_recovery(recovery_doc):
    """Upserts daily biometric recovery data by calendar_date (YYYY-MM-DD)."""
    col = get_recovery_collection()
    date_key = recovery_doc.get("calendar_date")
    if not date_key:
        raise ValueError("recovery_doc must contain 'calendar_date'")
    return col.update_one(
        {"calendar_date": date_key},
        {"$set": recovery_doc},
        upsert=True
    )

def get_latest_recovery():
    """Returns the most recent day's recovery data."""
    col = get_recovery_collection()
    return col.find_one({}, {"_id": 0}, sort=[("calendar_date", -1)])

def get_recent_recovery_history(limit=7):
    """Returns recent recovery records, newest first."""
    col = get_recovery_collection()
    return list(col.find({}, {"_id": 0}).sort("calendar_date", -1).limit(limit))
