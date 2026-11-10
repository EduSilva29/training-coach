import os
from dotenv import load_dotenv
from google import genai

# Load variables from .env file
load_dotenv()

# Initialize the Gemini client (it automatically picks up GEMINI_API_KEY from environment variables)
client = genai.Client()

print("Sending prompt to Gemini Flash...")

# Call the model (using the fast, free-tier flash model)
response = client.models.generate_content(
    model='gemini-3.8-flash',
    contents='Give a brief, 2-sentence motivational quote for a distance runner transitioning to 10k speed training.',
)

print("\nAI Response:")
print(response.text)