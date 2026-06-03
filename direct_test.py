from google import genai

print("PASTE YOUR NEW API KEY RIGHT HERE (include the AIza... part):")
api_key = input("> ").strip()

if len(api_key) < 10:
    print("That's not a valid key.")
    exit()

print("\nTesting directly (ignoring .env file)...")
try:
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents="Say OK"
    )
    print("✅ SUCCESS! Your new key works perfectly!")
    print("\nNow copy this exact line into your .env file (NO QUOTES):")
    print(f"GOOGLE_API_KEY={api_key}")
except Exception as e:
    print(f"❌ FAILED. Error: {e}")