import sys
import datetime
from pathlib import Path

# Ensure root directory is on Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sync.garmin_auth import get_garmin_client
from db.recovery_repo import upsert_daily_recovery

def parse_sleep_data(raw_sleep):
    """Safely extracts sleep score and duration from Garmin sleep DTO."""
    if not raw_sleep or not isinstance(raw_sleep, dict):
        return {}

    daily_dto = raw_sleep.get("dailySleepDTO", {})
    sleep_scores = daily_dto.get("sleepScores", {})
    overall_score = sleep_scores.get("overall", {}).get("value") or daily_dto.get("sleepScore")

    duration_sec = daily_dto.get("sleepTimeSeconds", 0)
    hours = round(duration_sec / 3600, 1) if duration_sec else 0

    return {
        "sleep_score": overall_score,
        "sleep_duration_hours": hours,
        "deep_sleep_sec": daily_dto.get("deepSleepSeconds"),
        "light_sleep_sec": daily_dto.get("lightSleepSeconds"),
        "rem_sleep_sec": daily_dto.get("remSleepSeconds"),
        "awake_sleep_sec": daily_dto.get("awakeSleepSeconds"),
        "sleep_qualifier": sleep_scores.get("overall", {}).get("qualifierKey")
    }

def parse_hrv_data(raw_hrv):
    """Safely extracts overnight HRV metrics and status."""
    if not raw_hrv or not isinstance(raw_hrv, dict):
        return {}

    summary = raw_hrv.get("hrvSummary", {})
    return {
        "hrv_status": summary.get("status"),              # e.g., BALANCED, UNBALANCED, LOW
        "last_night_avg_ms": summary.get("lastNightAvg"),
        "weekly_avg_ms": summary.get("weeklyAvg"),
        "baseline_balanced_low": summary.get("baseline", {}).get("balancedLow"),
        "baseline_balanced_upper": summary.get("baseline", {}).get("balancedUpper")
    }

def parse_daily_summary(raw_summary):
    """Extracts resting heart rate and stress metrics."""
    if not raw_summary or not isinstance(raw_summary, dict):
        return {}
    
    return {
        "resting_hr": raw_summary.get("restingHeartRate"),
        "max_hr": raw_summary.get("maxHeartRate"),
        "avg_stress_level": raw_summary.get("averageStressLevel"),
        "max_stress_level": raw_summary.get("maxStressLevel"),
        "body_battery_charged": raw_summary.get("bodyBatteryChargedValue"),
        "body_battery_drained": raw_summary.get("bodyBatteryDrainedValue")
    }

def parse_body_battery_current(raw_bb):
    """Extracts latest body battery reading if available."""
    if not raw_bb or not isinstance(raw_bb, list):
        return None
    # Latest item in time series list
    if raw_bb:
        latest = raw_bb[-1]
        if isinstance(latest, dict):
            # Garmin body battery entries typically have [timestamp, value] or dict with charged/drained
            return latest.get("bodyBatteryValue") or latest.get("value")
    return None

def sync_recovery_for_date(api, target_date: datetime.date):
    """Fetches sleep, HRV, and daily biometrics for a given date."""
    date_str = target_date.strftime("%Y-%m-%d")
    print(f"[Recovery Sync] Fetching metrics for {date_str}...")

    # 1. Sleep data
    try:
        raw_sleep = api.get_sleep_data(date_str)
        sleep_metrics = parse_sleep_data(raw_sleep)
    except Exception as e:
        print(f"[Recovery Sync] Notice: Could not fetch sleep for {date_str} ({e})")
        sleep_metrics = {}

    # 2. HRV data
    try:
        raw_hrv = api.get_hrv_data(date_str)
        hrv_metrics = parse_hrv_data(raw_hrv)
    except Exception as e:
        print(f"[Recovery Sync] Notice: Could not fetch HRV for {date_str} ({e})")
        hrv_metrics = {}

    # 3. Daily user summary (Resting HR, stress)
    try:
        raw_summary = api.get_user_summary(date_str)
        summary_metrics = parse_daily_summary(raw_summary)
    except Exception as e:
        print(f"[Recovery Sync] Notice: Could not fetch summary for {date_str} ({e})")
        summary_metrics = {}

    # 4. Body Battery
    body_battery_val = None
    try:
        raw_bb = api.get_body_battery(date_str)
        body_battery_val = parse_body_battery_current(raw_bb)
    except Exception:
        pass

    recovery_doc = {
        "calendar_date": date_str,
        "synced_at": datetime.datetime.now(datetime.timezone.utc),
        "sleep": sleep_metrics,
        "hrv": hrv_metrics,
        "biometrics": summary_metrics,
        "current_body_battery": body_battery_val
    }

    upsert_daily_recovery(recovery_doc)
    print(f"[Recovery Sync] Successfully saved recovery metrics for {date_str}!")
    return recovery_doc

def sync_recovery(days_back: int = 2):
    """Syncs recovery data for today and the past N days."""
    api = get_garmin_client()
    today = datetime.date.today()
    
    for i in range(days_back + 1):
        target_date = today - datetime.timedelta(days=i)
        sync_recovery_for_date(api, target_date)

if __name__ == "__main__":
    sync_recovery(days_back=2)
