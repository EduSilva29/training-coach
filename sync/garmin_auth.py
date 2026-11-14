import os
from pathlib import Path
from dotenv import load_dotenv
from garminconnect import (
    Garmin,
    GarminConnectConnectionError,
    GarminConnectAuthenticationError,
    GarminConnectTooManyRequestsError,
)

load_dotenv()

DEFAULT_TOKEN_DIR = os.getenv("GARMIN_TOKEN_DIR", str(Path.home() / ".garminconnect"))

def get_garmin_client(token_dir: str = DEFAULT_TOKEN_DIR) -> Garmin:
    """
    Initializes and returns an authenticated Garmin client.
    Attempts to reuse cached tokens in `token_dir`. If tokens don't exist or expired,
    logs in using GARMIN_EMAIL and GARMIN_PASSWORD, then caches the session.
    """
    email = os.getenv("GARMIN_EMAIL")
    password = os.getenv("GARMIN_PASSWORD")
    token_path = Path(token_dir)

    # 1. Try logging in with cached session tokens first
    try:
        if token_path.exists():
            print(f"[Garmin Auth] Attempting login using cached tokens from {token_path}...")
            client = Garmin()
            client.login(str(token_path))
            print("[Garmin Auth] Successfully authenticated via cached session tokens.")
            return client
    except Exception as e:
        print(f"[Garmin Auth] Cached login failed ({e}). Falling back to credentials...")

    # 2. Login with email & password if no token or expired
    if not email or not password:
        raise ValueError("GARMIN_EMAIL and GARMIN_PASSWORD must be configured in environment or .env.")

    try:
        print(f"[Garmin Auth] Logging in with email: {email}...")
        token_path.mkdir(parents=True, exist_ok=True)
        client = Garmin(email=email, password=password)
        # In garminconnect 0.3+, passing token_path automatically caches session tokens
        client.login(str(token_path))
        print(f"[Garmin Auth] Logged in and session tokens cached in {token_path}.")
        return client

    except (GarminConnectConnectionError, GarminConnectAuthenticationError, GarminConnectTooManyRequestsError) as err:
        print(f"[Garmin Auth] Error connecting to Garmin: {err}")
        raise
