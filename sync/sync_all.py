import sys
from pathlib import Path

# Ensure root directory is on Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sync.sync_activities import sync_activities
from sync.sync_recovery import sync_recovery

def main():
    # If '--backfill' is passed, fetch 30 days of data; otherwise fetch recent (daily sync)
    is_backfill = "--backfill" in sys.argv
    activity_limit = 30 if is_backfill else 10
    recovery_days = 30 if is_backfill else 3

    mode_label = "FULL 30-DAY BACKFILL" if is_backfill else "DAILY RECENT SYNC"
    print("==========================================")
    print(f"🚀 Starting Garmin Pipeline ({mode_label})")
    print("==========================================")
    
    try:
        print(f"\n--- 1. Syncing Activities (Up to {activity_limit}) ---")
        sync_activities(limit=activity_limit)
    except Exception as e:
        print(f"❌ Error during activities sync: {e}")

    try:
        print(f"\n--- 2. Syncing Recovery & Biometrics ({recovery_days} Days) ---")
        sync_recovery(days_back=recovery_days)
    except Exception as e:
        print(f"❌ Error during recovery sync: {e}")

    print("\n==========================================")
    print("✅ Sync Pipeline Finished!")
    print("==========================================")

if __name__ == "__main__":
    main()
