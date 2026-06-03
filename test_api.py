import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

print(f"API Key starts with: {api_key[:10]}...")
print("Testing connection to Google...\n")

try:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents="Say hello in one word."
    )
    print("SUCCESS!")
    print(f"Google replied: {response.text}")
except Exception as e:
    print("FAILED!")
    print(f"Exact Google error: {e}")