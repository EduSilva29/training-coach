import datetime
import os
from garminconnect import Garmin
from dotenv import load_dotenv

load_dotenv()  # Reads variables from .env file

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")
api = Garmin(email, password)
api.login()

# 1. Get the latest activity ID
activities = api.get_activities(start=0, limit=1)  # Fetch the most recent activity

# Create a clean, structured dictionary for your database
processed_activity = {
    "activity_id": activities[0].get("activityId"),
    "activity_name": activities[0].get("activityName"),
    "total_distance_meters": activities[0].get("distance"),
    "total_duration_seconds": activities[0].get("duration"),
    "laps": []
}

activity_laps = api.get_activity_laps(processed_activity["activity_id"])['lapDTOs']

# Loop through your laps and extract only what matters
for lap in activity_laps:
    lap_summary = {
        "lap_index": lap.get("lapIndex"),
        "distance_meters": lap.get("distance"),
        "duration_seconds": lap.get("duration"),
        "average_speed_ms": lap.get("averageSpeed"),
        "average_hr": lap.get("averageHR"),
        "max_hr": lap.get("maxHR"),
        "cadence": lap.get("averageRunCadence"),
        "ground_contact_time": lap.get("groundContactTime"),
        "vertical_oscillation": lap.get("verticalOscillation")
    }
    processed_activity["laps"].append(lap_summary)

print(processed_activity)