import datetime
from .client import get_db

DEFAULT_PROFILE = {
    "goal": "Prepare for target race without injury. Improve aerobic threshold and consistency.",
    "target_races": "10k (Sub-40 min target) / Half Marathon",
    "injuries_and_aches": "None currently. Keep an eye on calves after speed sessions.",
    "preferences": "Prefer long runs on weekends. Easy runs should stay strictly Zone 2.",
    "personal_bests": {
        "5k": "",
        "10k": "",
        "half_marathon": "",
        "marathon": ""
    }
}

def get_profile_collection():
    return get_db()["athlete_profile"]

def get_athlete_profile():
    """Returns the athlete's current profile, goals, and injury history."""
    col = get_profile_collection()
    doc = col.find_one({"type": "current_profile"}, {"_id": 0})
    if not doc:
        # Initialize with default
        return DEFAULT_PROFILE
    return doc.get("profile", DEFAULT_PROFILE)

def update_athlete_profile(profile_data):
    """Updates the athlete profile."""
    col = get_profile_collection()
    col.update_one(
        {"type": "current_profile"},
        {"$set": {
            "type": "current_profile",
            "profile": profile_data,
            "updated_at": datetime.datetime.now(datetime.timezone.utc)
        }},
        upsert=True
    )
