import datetime
import os
from garminconnect import Garmin
from dotenv import load_dotenv

load_dotenv()  # Reads variables from .env file

email = os.getenv("GARMIN_EMAIL")
password = os.getenv("GARMIN_PASSWORD")
client = Garmin(email, password)


def fetch_latest_run():

    print("Fetching latest activity...")
    # Get the 1 most recent activity (index 0, count 1)
    activities = client.get_activities(0, 1)

    if not activities:
        print("No activities found.")
        return

    latest = activities[0]

    # Extract key raw fields from Garmin's response dictionary
    activity_name = latest.get("activityName", "Workout")
    start_time = latest.get("startTimeLocal", "")[:10]  # Extracts YYYY-MM-DD
    distance_meters = latest.get("distance", 0)
    avg_hr = latest.get("averageHR", 0)
    avg_speed_mps = latest.get("averageSpeed", 0)  # meters per second

    # 2. Transform the data into user-friendly metrics
    distance_km = round(distance_meters / 1000, 2)

    if avg_speed_mps > 0:
        avg_pace_sec = 1000 / avg_speed_mps
        pace_min = int(avg_pace_sec // 60)
        pace_sec = int(avg_pace_sec % 60)
        pace_str = f"{pace_min}:{pace_sec:02d}/km"
    else:
        pace_str = "N/A"

    # 3. Format as a clean Markdown string
    log_line = f"- **{start_time} ({activity_name})**: {distance_km} km @ {pace_str} | Avg HR: {avg_hr} bpm\n"
    print(f"Formatted Log Entry:\n{log_line}")

    # 4. Append to your local Markdown training log file
    log_file_path = "Training_Log.md"
    with open(log_file_path, "a", encoding="utf-8") as f:
        f.write(log_line)

    print(f"Successfully saved to {log_file_path}!")

if __name__ == "__main__":
    fetch_latest_run()