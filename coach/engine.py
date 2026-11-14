import os
from dotenv import load_dotenv
from db.profile_repo import get_athlete_profile
from db.recovery_repo import get_latest_recovery
from db.activities_repo import get_recent_activities
from db.conversations_repo import get_chat_history, save_message
from coach.prompts import build_coach_system_instruction

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
    1. Loads profile, latest recovery, recent activities from MongoDB.
    2. Constructs the contextual system instruction.
    3. Loads chat history for conversational memory.
    4. Calls Google Gemini.
    5. Saves both user and assistant turns to MongoDB.
    """
    # Save user message to DB
    save_message(role="user", content=user_message)

    # Check for Gemini API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        fallback_msg = (
            "⚠️ **Gemini API Key is missing!**\n\n"
            "Please create a free API key at [Google AI Studio](https://aistudio.google.com/) "
            "and add `GEMINI_API_KEY=your_key_here` to your `.env` file or Streamlit secrets."
        )
        save_message(role="assistant", content=fallback_msg)
        return fallback_msg

    # 1. Fetch context data from MongoDB
    profile = get_athlete_profile()
    latest_recovery = get_latest_recovery()
    recent_activities = get_recent_activities(limit=7)

    # 2. Build system instruction
    system_instruction = build_coach_system_instruction(profile, latest_recovery, recent_activities)

    # 3. Retrieve past conversation history (last 20 turns)
    chat_history = get_chat_history(limit=20)
    
    # Format messages for Gemini
    formatted_contents = []
    for msg in chat_history:
        # Gemini expects 'user' or 'model'
        role = "user" if msg["role"] == "user" else "model"
        formatted_contents.append({"role": role, "parts": [{"text": msg["content"]}]})

    # 4. Call Gemini
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        
        # Use the model specified in the .env file or default to "gemini-4-hydrogen"
        model_name = os.getenv("GEMINI_MODEL", "gemini-4-hydrogen")
        
        response = client.models.generate_content(
            model=model_name,
            contents=formatted_contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
        coach_reply = response.text

    except Exception as e:
        coach_reply = f"❌ Error contacting AI Coach: {str(e)}"

    # 5. Persist coach response in MongoDB
    save_message(role="assistant", content=coach_reply)
    return coach_reply
