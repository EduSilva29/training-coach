import os
import time
import threading
from dotenv import load_dotenv

# Clean package imports: We talk to the 'db' package front door
from db import (
    get_athlete_profile,
    get_recent_recovery_history,
    get_recent_activities,
    get_chat_history,
    save_message,
)

# Relative sibling imports: '.' means "look in the current folder (coach)"
from .prompts import build_coach_system_instruction
from .scribe import run_scribe_extraction

load_dotenv()

def get_gemini_client():
    """Initializes Google GenAI client."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        return None

def ask_coach(user_message: str) -> str:
    """
    Main entry point for talking to the AI coach.
    Includes automatic retry and fallback if Google experiences a 503 high-demand spike.
    """
    # Save user message to DB
    save_message(role="user", content=user_message)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        fallback_msg = (
            "⚠️ **Gemini API Key is missing!**\n\n"
            "Please create a free API key at [Google AI Studio](https://aistudio.google.com/) "
            "and add `GEMINI_API_KEY=your_key_here` to your `.env` file or Streamlit secrets."
        )
        return fallback_msg

    # 1. Fetch multi-week context data from MongoDB
    profile = get_athlete_profile()
    recovery_history = get_recent_recovery_history(limit=30)  # Last 30 days of sleep & HRV trends
    recent_activities = get_recent_activities(limit=20)       # Last 20 workouts (~1 month training block)

    # 2. Build system instruction with full 30-day training history
    system_instruction = build_coach_system_instruction(profile, recovery_history, recent_activities)

    # 3. Retrieve extended conversation history (last 50 messages)
    chat_history = get_chat_history(limit=50)
    
    # Format messages for Gemini (cleanly skipping any prior error messages)
    formatted_contents = []
    for msg in chat_history:
        content = msg.get("content", "")
        # Do not feed old error messages back into the AI context
        if content.startswith("❌ Error") or content.startswith("❌ Temporary"):
            continue
        role = "user" if msg["role"] == "user" else "model"
        formatted_contents.append({"role": role, "parts": [{"text": content}]})

    # 4. Call Gemini with Auto-Retry and Fallback
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    primary_model = os.getenv("GEMINI_MODEL", "gemini-4-hydrogen")
    fallback_model = "gemini-3.8-flash"

    coach_reply = None
    last_error = None

    # Step A: Try primary model with 1 auto-retry on 503 (wait 2.5 seconds)
    for attempt in range(2):
        try:
            response = client.models.generate_content(
                model=primary_model,
                contents=formatted_contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7
                )
            )
            coach_reply = response.text
            break
        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if ("503" in err_str or "unavailable" in err_str or "high demand" in err_str) and attempt == 0:
                print(f"[Coach Engine ⏳] {primary_model} busy (503). Retrying in 2.5 seconds...")
                time.sleep(2.5)
                continue
            break

    # Step B: If primary model is still unavailable on 503, auto-fallback to flash
    if not coach_reply and primary_model != fallback_model:
        err_str = str(last_error).lower() if last_error else ""
        if "503" in err_str or "unavailable" in err_str or "high demand" in err_str:
            print(f"[Coach Engine 🔄] Falling back to {fallback_model} to avoid downtime...")
            try:
                response = client.models.generate_content(
                    model=fallback_model,
                    contents=formatted_contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7
                    )
                )
                coach_reply = response.text
            except Exception as e:
                last_error = e

    # 5. Persist only successful coach replies to MongoDB
    if coach_reply:
        save_message(role="assistant", content=coach_reply)
        # 6. Trigger Scribe Agent in background
        threading.Thread(target=run_scribe_extraction, args=(user_message,), daemon=True).start()
        return coach_reply
    else:
        # Return error message to user, but DO NOT save it to MongoDB
        return f"❌ Temporary Google Server Congestion (503). Please try sending your message again in a moment. ({last_error})"
