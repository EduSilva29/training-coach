import json
import datetime
import os
from garminconnect import Garmin
from dotenv import load_dotenv
from pymongo import MongoClient

def speed_to_pace(speed_ms):
    """Converts speed in meters/second to 'MM:SS' pace per km."""
    if not speed_ms or speed_ms <= 0:
        return "0:00"
    seconds_per_km = 1000 / speed_ms
    minutes = int(seconds_per_km // 60)
    seconds = int(round(seconds_per_km % 60))
    if seconds == 60:
        minutes += 1
        seconds = 0
    return f"{minutes}:{seconds:02d}"

def format_duration(seconds):
    """Converts raw seconds into 'HH:MM:SS' or 'MM:SS'."""
    if not seconds:
        return "0:00"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(round(seconds % 60))
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"

def parse_hr_zones(raw_zones):
    """Formats Garmin HR zone data into readable time and percentages."""
    if not raw_zones:
        return []
    
    total_zone_secs = sum(z.get("secsInZone", 0) for z in raw_zones)
    formatted_zones = []
    
    # Sort by zoneNumber to ensure Zone 1 -> Zone 5 order
    for z in sorted(raw_zones, key=lambda x: x.get("zoneNumber", 0)):
        secs = z.get("secsInZone", 0)
        pct = round((secs / total_zone_secs) * 100, 1) if total_zone_secs > 0 else 0.0
        formatted_zones.append({
            "zone": z.get("zoneNumber"),
            "min_bpm": z.get("zoneLowBoundary"),
            "time": format_duration(secs),
            "percentage": pct
        })
    return formatted_zones

def generate_llm_summary(metadata, laps):
    """Creates a clean natural language summary for the AI agent."""
    summary = (
        f"{metadata['activity_name']} ({metadata['activity_type']}): "
        f"{metadata['total_distance_km']} km completed in {metadata['duration_formatted']} "
        f"at an average pace of {metadata['average_pace_min_km']}/km. "
    )
    if metadata['average_hr']:
        summary += f"Average HR was {metadata['average_hr']} bpm (max {metadata['max_hr']} bpm). "

    # Highlight the dominant heart rate zone in the text summary
    if metadata.get("hr_zones"):
        top_zone = max(metadata["hr_zones"], key=lambda z: z["percentage"])
        if top_zone["percentage"] > 0:
            summary += f"Primary effort was in Zone {top_zone['zone']} ({top_zone['percentage']}% of run). "
    
    if metadata['total_elevation_gain']:
        summary += f"Total elevation gain: {metadata['total_elevation_gain']}m. "
    
    if laps:
        summary += f"Recorded across {len(laps)} laps."
    return summary

def process_activity(api, activity_data):
    activity_id = activity_data["activityId"]
    
    # Fetch detailed lap data
    raw_laps_data = api.get_activity_laps(activity_id)
    raw_laps = raw_laps_data.get("lapDTOs", [])
    raw_hr_zones = api.get_activity_hr_in_timezones(activity_id)

    # Extract & convert global metadata
    dist_km = round(activity_data.get("distance", 0) / 1000, 2)
    duration_sec = activity_data.get("duration", 0)
    avg_speed = activity_data.get("averageSpeed", 0)
    
    metadata = {
        "activity_name": activity_data.get("activityName", "Untitled Run"),
        "activity_type": activity_data.get("activityType", {}).get("typeKey", "running"),
        "start_time": activity_data.get("startTimeGMT"),
        "total_distance_km": dist_km,
        "duration_formatted": format_duration(duration_sec),
        "average_pace_min_km": speed_to_pace(avg_speed),
        "average_hr": round(activity_data.get("averageHR", 0)) or None,
        "max_hr": round(activity_data.get("maxHR", 0)) or None,
        "hr_zones": parse_hr_zones(raw_hr_zones),
        "total_elevation_gain": round(activity_data.get("elevationGain", 0)),
        "calories": round(activity_data.get("calories", 0))
    }

    # Extract & convert lap-by-lap metrics
    processed_laps = []
    for lap in raw_laps:
        lap_dist = lap.get("distance", 0)
        # Skip empty/zero-distance laps if any exist
        if lap_dist <= 0:
            continue
            
        processed_laps.append({
            "lap": lap.get("lapIndex"),
            "distance_m": round(lap_dist),
            "pace": speed_to_pace(lap.get("averageSpeed", 0)),
            "avg_hr": round(lap.get("averageHR", 0)) or None,
            "max_hr": round(lap.get("maxHR", 0)) or None,
            "cadence": round(lap.get("averageRunCadence", 0)) or None,
            "gct_ms": round(lap.get("groundContactTime", 0), 1) or None,
            "vertical_oscillation_cm": round(lap.get("verticalOscillation", 0), 2) or None
        })

    # Assemble final MongoDB-ready document
    clean_document = {
        "activity_id": activity_id,
        "metadata": metadata,
        "laps": processed_laps,
        "llm_summary": generate_llm_summary(metadata, processed_laps)
    }
    
    return clean_document

if __name__ == "__main__":
    # Initialize and login
    load_dotenv() 
    MONGO_URI = os.getenv("MONGO_URI")
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    api = Garmin(email, password)
    api.login()
    client = MongoClient(MONGO_URI)
    db = client["running_coach"]        # Database name
    collection = db["activities"]       # Collection name

    recent_activities = api.get_activities(start=0, limit=5)
    
    synced_count = 0
    for act in recent_activities:
        if act.get("activityType", {}).get("typeKey") == "running":
            act_name = act.get("activityName", "Untitled")
            print(f"Processing and syncing: {act_name}...")
            
            clean_doc = process_activity(api, act)
            
            # Upsert into MongoDB (inserts if new, updates if activity_id already exists)
            collection.update_one(
                {"activity_id": clean_doc["activity_id"]},
                {"$set": clean_doc},
                upsert=True
            )
            synced_count += 1

    print(f"Successfully synced {synced_count} running activities to MongoDB Atlas!")