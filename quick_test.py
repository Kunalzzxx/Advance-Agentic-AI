import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

try:
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents="Say hello in one word."
    )
    print("SUCCESS! Model replied:", response.text)
except Exception as e:
    print("FAILED! Error:", e)