import os
from dotenv import load_dotenv
from google import genai

# Load environment variables (reads your GEMINI_API_KEY from .env)
load_dotenv()

# Initialize the Gemini client
client = genai.Client()

# 1. Read your training log file from disk (File I/O)
log_path = "Training_Log.md"
try:
    with open(log_path, "r", encoding="utf-8") as f:
        training_history = f.read()
except FileNotFoundError:
    training_history = "No training logs found yet."

# 2. Craft the system persona and prompt context
prompt = f"""
You are an expert endurance running coach specializing in transitioning athletes from marathon-specific endurance to 9k/10k speed.

Here is my recent training history from my vault:
{training_history}

Context: I recently ran a 3:14:26 marathon in late November, and I am now pivoting to shorter, sharper 9k/10k races in December (Guarda on Dec 13 and Porto on Dec 20). 

Based on my training log, give me:
1. A short assessment of my recent workouts and recovery.
2. One specific, tactical focus for my next running session to build fast-twitch speed and cadence without burning out.
Keep the tone direct, empirical, and focused on athletic metrics.
"""

print("Sending your training vault to your AI coach...")

# 3. Send the prompt to Gemini (using the fast flash model)
response = client.models.generate_content(
    model='gemini-3.8-flash',
    contents=prompt,
)

# 4. Print results and save to a markdown file
print("\n" + "="*40)
print("AI COACH FEEDBACK:")
print("="*40)
print(response.text)
print("="*40 + "\n")

feedback_file = "Coach_Feedback.md"
with open(feedback_file, "w", encoding="utf-8") as f:
    f.write(f"# AI Coaching Review\n\n{response.text}")

print(f"Successfully saved coach feedback to {feedback_file}!")