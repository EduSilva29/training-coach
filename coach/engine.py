import os
import threading
import time
from typing import Optional, Tuple
from dotenv import load_dotenv
from config import get_setting

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

GENERATION_ATTEMPTS = 3

load_dotenv()


def _is_congestion_error(error: Exception) -> bool:
    if getattr(error, "code", None) == 503:
        return True
    err_str = str(error).lower()
    return "503" in err_str or "unavailable" in err_str or "high demand" in err_str


def _generate_content_with_retries(client, model, contents, system_instruction):
    from google.genai import types

    for attempt in range(GENERATION_ATTEMPTS):
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7
                )
            )
            return response.text
        except Exception as error:
            if not _is_congestion_error(error) or attempt == GENERATION_ATTEMPTS - 1:
                raise
            delay = 2 ** attempt
            print(
                f"[Coach Engine ⏳] {model} is congested; "
                f"retrying in {delay} seconds..."
            )
            time.sleep(delay)


def _get_fallback_models(primary_model):
    configured_models = get_setting("GEMINI_FALLBACK_MODELS")
    if configured_models is None:
        configured_models = "gemini-3.8-flash"

    fallback_models = []
    for model in configured_models.split(","):
        model = model.strip()
        if model and model != primary_model and model not in fallback_models:
            fallback_models.append(model)
    return fallback_models


def get_gemini_client():
    """Initializes Google GenAI client."""
    api_key = get_setting("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        return None

def ask_coach(user_message: str) -> Tuple[str, Optional[str]]:
    """
    Main entry point for talking to the AI coach.
    Tries fallback models if Google experiences a 503 high-demand spike.
    """
    api_key = get_setting("GEMINI_API_KEY")
    if not api_key:
        fallback_msg = (
            "⚠️ **Gemini API Key is missing!**\n\n"
            "Please create a free API key at [Google AI Studio](https://aistudio.google.com/) "
            "and add `GEMINI_API_KEY=your_key_here` to your `.env` file or Streamlit secrets."
        )
        return fallback_msg, None

    # 1. Fetch five-week activity context plus recent recovery data from MongoDB
    profile = get_athlete_profile()
    recovery_history = get_recent_recovery_history(limit=30)  # Last 30 days of sleep & HRV trends
    recent_activities = get_recent_activities(limit=100)      # Summarized into five ISO weeks plus recent workout detail

    # 2. Build a compact system instruction with weekly training trends
    system_instruction = build_coach_system_instruction(profile, recovery_history, recent_activities)

    # 3. Retrieve prior conversation history, leaving room for the current message
    chat_history = get_chat_history(limit=49)
    
    # Format messages for Gemini (cleanly skipping any prior error messages)
    formatted_contents = []
    for msg in chat_history:
        content = msg.get("content", "")
        # Do not feed old error messages back into the AI context
        if content.startswith("❌ Error") or content.startswith("❌ Temporary"):
            continue
        role = "user" if msg["role"] == "user" else "model"
        formatted_contents.append({"role": role, "parts": [{"text": content}]})

    formatted_contents.append({"role": "user", "parts": [{"text": user_message}]})

    # 4. Retry congestion briefly, then try configured fallback models in order
    from google import genai

    client = genai.Client(api_key=api_key)
    primary_model = get_setting("GEMINI_MODEL", "gemini-4-hydrogen")
    fallback_models = _get_fallback_models(primary_model)

    coach_reply = None
    model_used = None
    last_error = None

    models = [primary_model] + fallback_models
    for index, model in enumerate(models):
        try:
            coach_reply = _generate_content_with_retries(
                client, model, formatted_contents, system_instruction
            )
            if coach_reply:
                model_used = model
            break
        except Exception as e:
            last_error = e
            if not _is_congestion_error(e):
                break
            if index + 1 == len(models):
                break
            print(f"[Coach Engine 🔄] {model} is congested; moving to the next model...")

    # 5. Persist only successful coach replies to MongoDB
    if coach_reply:
        save_message(role="user", content=user_message)
        save_message(role="assistant", content=coach_reply, model=model_used)
        # 6. Trigger Scribe Agent in background
        threading.Thread(target=run_scribe_extraction, args=(user_message,), daemon=True).start()
        return coach_reply, model_used
    else:
        # Return error message to user, but DO NOT save it to MongoDB
        return (
            f"❌ Temporary Google Server Congestion (503). Please try sending your message again in a moment. ({last_error})",
            None,
        )
