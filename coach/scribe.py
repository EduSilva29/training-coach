import os
import json
from dotenv import load_dotenv
from config import get_setting
from db import get_athlete_profile, update_athlete_profile

load_dotenv()

SCRIBE_SYSTEM_PROMPT = """You are an intelligent Medical & Athletic Scribe for an endurance running coach.
Your SOLE job is to listen to the athlete's messages and extract any NEW, PERMANENT facts to update their Athlete Profile.

CATEGORIES TO WATCH FOR:
1. "injuries_and_aches": New pain, soreness, injury, niggles, or notification that a prior issue is resolved.
2. "target_races": Any new race signed up for, race dates, target times.
3. "goal": Core changes to their overall training goal.
4. "gear": New running shoes, watch model, heart rate monitor, or shoe rotation notes.
5. "preferences": Long-term schedule rules (e.g. "I cannot run on Wednesdays"), surface preferences, etc.

RULES:
- If the message is everyday chitchat, a question about today's workout, or discussing a single run's pace, return {"has_updates": false}.
- Do NOT erase prior info. Merge or append the new fact concisely.
- Return ONLY valid JSON matching this schema:
{
  "has_updates": boolean,
  "reason": "short explanation of what changed",
  "updates": {
    "injuries_and_aches": "string or null",
    "target_races": "string or null",
    "goal": "string or null",
    "gear": "string or null",
    "preferences": "string or null"
  }
}
"""

def run_scribe_extraction(user_message: str):
    """
    Background worker agent that analyzes the athlete's message and
    automatically persists new profile facts to MongoDB.
    """
    api_key = get_setting("GEMINI_API_KEY")
    if not api_key:
        return

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        current_profile = get_athlete_profile()

        user_prompt = f"""
CURRENT ATHLETE PROFILE:
- Goal: {current_profile.get('goal', 'None')}
- Target Races: {current_profile.get('target_races', 'None')}
- Aches & Injuries: {current_profile.get('injuries_and_aches', 'None')}
- Gear & Shoes: {current_profile.get('gear', 'None')}
- Preferences & Constraints: {current_profile.get('preferences', 'None')}

ATHLETE'S NEW MESSAGE:
"{user_message}"
"""

        # Read model from .env (honors GEMINI_MODEL, with optional GEMINI_SCRIBE_MODEL override)
        model_name = get_setting("GEMINI_SCRIBE_MODEL") or get_setting("GEMINI_MODEL", "gemini-3.8-flash")

        # Call Gemini to extract memory with guaranteed JSON output
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SCRIBE_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.1  # Low temperature for deterministic, factual extraction
            )
        )

        result = json.loads(response.text)

        # If the Scribe found new facts, update MongoDB
        if result.get("has_updates") and result.get("updates"):
            updates = result["updates"]
            updated_profile = dict(current_profile)

            changed = False
            for key in ["injuries_and_aches", "target_races", "goal", "gear", "preferences"]:
                new_val = updates.get(key)
                # Only update if the field is a non-empty string and different
                if new_val and isinstance(new_val, str) and new_val.strip():
                    updated_profile[key] = new_val.strip()
                    changed = True

            if changed:
                update_athlete_profile(updated_profile)
                print(f"[Scribe Agent 📝] Auto-updated athlete profile: {result.get('reason')}")

    except Exception as e:
        # Scribe runs quietly in background without interrupting the main chat
        print(f"[Scribe Agent ⚠️] Extraction notice: {e}")
