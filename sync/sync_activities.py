import sys
from pathlib import Path

# Ensure root directory is on Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sync.garmin_auth import get_garmin_client
from db import upsert_activity

# Supported Sport Types
RUNNING_TYPES = {"running", "trail_running", "treadmill_running", "track_running"}
CYCLING_TYPES = {"cycling", "indoor_cycling", "virtual_ride", "road_biking", "gravel_cycling", "mountain_biking"}

def speed_to_pace(speed_ms):
    """Converts speed in meters/second to 'MM:SS' pace per km (for running)."""
    if not speed_ms or speed_ms <= 0:
        return "0:00"
    seconds_per_km = 1000 / speed_ms
    minutes = int(seconds_per_km // 60)
    seconds = int(round(seconds_per_km % 60))
    if seconds == 60:
        minutes += 1
        seconds = 0
    return f"{minutes}:{seconds:02d}"

def speed_to_kmh(speed_ms):
    """Converts speed in meters/second to km/h (for cycling)."""
    if not speed_ms or speed_ms <= 0:
        return 0.0
    return round(speed_ms * 3.6, 1)

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
    """Creates a natural language summary tailored for running vs. indoor cycling."""
    sport = metadata.get("sport_category", "running")
    name = metadata.get("activity_name", "Activity")
    dist = metadata.get("total_distance_km", 0)
    dur = metadata.get("duration_formatted", "--")

    if sport == "cycling":
        speed_info = f"at an average speed of {metadata.get('speed_kmh', 0)} km/h"
        power_info = f" (Avg Power: {metadata['average_power_watts']}W)" if metadata.get("average_power_watts") else ""
        cadence_info = f", Cadence: {metadata['cadence']} rpm" if metadata.get("cadence") else ""
        summary = f"{name} (Cross-Training / Cycling): {dist} km in {dur} {speed_info}{power_info}{cadence_info}. "
    else:
        cadence_info = f", Cadence: {metadata['cadence']} spm" if metadata.get("cadence") else ""
        summary = f"{name} (Running): {dist} km completed in {dur} at an average pace of {metadata.get('average_pace_min_km', '--')}/km{cadence_info}. "

    if metadata.get("average_hr"):
        summary += f"Average HR was {metadata['average_hr']} bpm (max {metadata['max_hr']} bpm). "

    if metadata.get("hr_zones"):
        top_zone = max(metadata["hr_zones"], key=lambda z: z["percentage"])
        if top_zone["percentage"] > 0:
            summary += f"Dominant effort in Zone {top_zone['zone']} ({top_zone['percentage']}% of session). "
    
    if metadata.get("total_elevation_gain"):
        summary += f"Elevation gain: {metadata['total_elevation_gain']}m. "
    
    if laps:
        summary += f"Recorded across {len(laps)} laps."
    return summary

def process_activity(api, activity_data):
    """Enriches raw Garmin activity with laps, HR zones, power/speed, and LLM summary."""
    activity_id = activity_data["activityId"]
    raw_type_key = activity_data.get("activityType", {}).get("typeKey", "running").lower()

    # Determine sport category
    is_cycling = raw_type_key in CYCLING_TYPES or "cycl" in raw_type_key or "bike" in raw_type_key
    sport_category = "cycling" if is_cycling else "running"

    # Fetch detailed lap and HR zone data
    raw_laps_data = api.get_activity_laps(activity_id)
    raw_laps = raw_laps_data.get("lapDTOs", []) if isinstance(raw_laps_data, dict) else []
    raw_hr_zones = api.get_activity_hr_in_timezones(activity_id)

    dist_km = round(activity_data.get("distance", 0) / 1000, 2)
    duration_sec = activity_data.get("duration", 0)
    avg_speed = activity_data.get("averageSpeed", 0)

    # Power metrics (indoor smart trainer or power pedals)
    avg_power = round(activity_data.get("averagePower", 0)) or None
    max_power = round(activity_data.get("maxPower", 0)) or None

    # Cadence (spm for running, rpm for cycling)
    if is_cycling:
        cadence = round(activity_data.get("averageBikingCadenceInRevPerMinute") or activity_data.get("averageCadence", 0)) or None
    else:
        cadence = round(activity_data.get("averageRunCadence", 0)) or None
    
    metadata = {
        "activity_name": activity_data.get("activityName", "Workout"),
        "activity_type": raw_type_key,
        "sport_category": sport_category,
        "start_time": activity_data.get("startTimeGMT") or activity_data.get("startTimeLocal"),
        "total_distance_km": dist_km,
        "duration_formatted": format_duration(duration_sec),
        "duration_seconds": duration_sec,
        "average_pace_min_km": speed_to_pace(avg_speed) if not is_cycling else None,
        "speed_kmh": speed_to_kmh(avg_speed),
        "average_power_watts": avg_power,
        "max_power_watts": max_power,
        "cadence": cadence,
        "average_hr": round(activity_data.get("averageHR", 0)) or None,
        "max_hr": round(activity_data.get("maxHR", 0)) or None,
        "hr_zones": parse_hr_zones(raw_hr_zones),
        "total_elevation_gain": round(activity_data.get("elevationGain", 0)),
        "calories": round(activity_data.get("calories", 0)),
        "aerobic_training_effect": activity_data.get("aerobicTrainingEffect"),
        "anaerobic_training_effect": activity_data.get("anaerobicTrainingEffect")
    }

    processed_laps = []
    for lap in raw_laps:
        lap_dist = lap.get("distance", 0)
        if lap_dist <= 0:
            continue
        
        lap_speed = lap.get("averageSpeed", 0)
        processed_laps.append({
            "lap": lap.get("lapIndex"),
            "distance_m": round(lap_dist),
            "pace": speed_to_pace(lap_speed) if not is_cycling else None,
            "speed_kmh": speed_to_kmh(lap_speed),
            "avg_power_watts": round(lap.get("averagePower", 0)) or None,
            "avg_hr": round(lap.get("averageHR", 0)) or None,
            "max_hr": round(lap.get("maxHR", 0)) or None,
            "cadence": round(lap.get("averageRunCadence", 0) or lap.get("averageBikingCadenceInRevPerMinute", 0)) or None,
            "gct_ms": round(lap.get("groundContactTime", 0), 1) or None,
            "vertical_oscillation_cm": round(lap.get("verticalOscillation", 0), 2) or None
        })

    return {
        "activity_id": activity_id,
        "metadata": metadata,
        "laps": processed_laps,
        "llm_summary": generate_llm_summary(metadata, processed_laps)
    }

def sync_activities(limit: int = 10):
    """Fetches the latest activities (running & cycling) from Garmin and upserts them to MongoDB."""
    api = get_garmin_client()
    activities = api.get_activities(start=0, limit=limit)
    
    synced_count = 0
    for act in activities:
        act_type = act.get("activityType", {}).get("typeKey", "").lower()
        is_supported = (
            act_type in RUNNING_TYPES
            or act_type in CYCLING_TYPES
            or "cycl" in act_type
            or "bike" in act_type
            or "run" in act_type
        )
        if is_supported:
            act_name = act.get("activityName", "Activity")
            print(f"[Activities Sync] Processing: {act_name} ({act_type}) (ID: {act.get('activityId')})")
            
            clean_doc = process_activity(api, act)
            upsert_activity(clean_doc)
            synced_count += 1
            
    print(f"[Activities Sync] Completed! Synced {synced_count} activities to MongoDB.")
    return synced_count

if __name__ == "__main__":
    sync_activities(limit=10)
