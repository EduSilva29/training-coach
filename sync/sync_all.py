import sys
from pathlib import Path

# Ensure root directory is on Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from sync.sync_activities import sync_activities
from sync.sync_recovery import sync_recovery

def main():
    print("==========================================")
    print("🚀 Starting Garmin Complete Sync Pipeline")
    print("==========================================")
    
    try:
        print("\n--- 1. Syncing Recent Activities ---")
        sync_activities(limit=5)
    except Exception as e:
        print(f"❌ Error during activities sync: {e}")

    try:
        print("\n--- 2. Syncing Recovery & Biometrics ---")
        sync_recovery(days_back=2)
    except Exception as e:
        print(f"❌ Error during recovery sync: {e}")

    print("\n==========================================")
    print("✅ Sync Pipeline Finished!")
    print("==========================================")

if __name__ == "__main__":
    main()
