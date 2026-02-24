"""
Diagnostic script to check Groq, OpenAI, and OpenRouter API key validity.
"""
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

print("=" * 70)
print("MILIX - API KEYS DIAGNOSTIC")
print("=" * 70)

# Test Groq
print("\n[1/3] Testing GROQ_API_KEY...")
groq_key = os.getenv("GROQ_API_KEY")
if not groq_key:
    print("  [SKIP] GROQ_API_KEY not found in .env")
else:
    print(f"  [INFO] Key present: {groq_key[:20]}...{groq_key[-10:]}")
    try:
        client = OpenAI(
            api_key=groq_key,
            base_url="https://api.groq.com/openai/v1",
        )
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=5,
        )
        result = resp.choices[0].message.content if resp.choices else None
        if result:
            print(f"  [SUCCESS] GROQ API key is VALID")
            print(f"     Response: {result}")
        else:
            print("  [WARN] No response from server")
    except Exception as e:
        print(f"  [FAIL] ERROR: {str(e)[:200]}")
        if "401" in str(e) or "Invalid API Key" in str(e):
            print("\n  Solution:")
            print("     1. Go to https://console.groq.com/keys")
            print("     2. Create a new API key")
            print("     3. Update GROQ_API_KEY in .env")

# Test OpenAI
print("\n[2/3] Testing OPENAI_API_KEY...")
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    print("  [SKIP] OPENAI_API_KEY not found in .env")
else:
    print(f"  [INFO] Key present: {openai_key[:20]}...{openai_key[-10:]}")
    try:
        client = OpenAI(api_key=openai_key)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=5,
        )
        result = resp.choices[0].message.content if resp.choices else None
        if result:
            print(f"  [SUCCESS] OPENAI API key is VALID")
            print(f"     Response: {result}")
        else:
            print("  [WARN] No response from server")
    except Exception as e:
        print(f"  [FAIL] ERROR: {str(e)[:200]}")
        if "401" in str(e) or "Invalid API Key" in str(e):
            print("\n  Solution:")
            print("     1. Go to https://platform.openai.com/api-keys")
            print("     2. Create a new API key")
            print("     3. Update OPENAI_API_KEY in .env")

# Test OpenRouter
print("\n[3/3] Testing OPENROUTER_API_KEY...")
openrouter_key = os.getenv("OPENROUTER_API_KEY")
if not openrouter_key:
    print("  [SKIP] OPENROUTER_API_KEY not found in .env")
else:
    print(f"  [INFO] Key present: {openrouter_key[:20]}...{openrouter_key[-10:]}")
    try:
        client = OpenAI(
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
        )
        resp = client.chat.completions.create(
            model="google/gemini-2.0-flash-exp:free",
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=5,
        )
        result = resp.choices[0].message.content if resp.choices else None
        if result:
            print(f"  [SUCCESS] OPENROUTER API key is VALID")
            print(f"     Response: {result}")
        else:
            print("  [WARN] No response from server")
    except Exception as e:
        print(f"  [FAIL] ERROR: {str(e)[:200]}")
        if "401" in str(e) or "Invalid API Key" in str(e):
            print("\n  Solution:")
            print("     1. Go to https://openrouter.ai/keys")
            print("     2. Create a new API key")
            print("     3. Update OPENROUTER_API_KEY in .env")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

groq_ok = groq_key and "401" not in str(groq_key)
openai_ok = openai_key and "401" not in str(openai_key)
openrouter_ok = openrouter_key and "401" not in str(openrouter_key)

print("\nConfigured APIs:")
print(f"  - Groq: {'CONFIGURED' if groq_key else 'NOT configured'}")
print(f"  - OpenAI: {'CONFIGURED' if openai_key else 'NOT configured'}")
print(f"  - OpenRouter: {'CONFIGURED' if openrouter_key else 'NOT configured'}")

print("\nRecommendations:")
print("  1. Use OpenAI for best reliability (Whisper-1 + GPT-4o-mini)")
print("  2. Use Groq for speed (requires ffmpeg for long videos)")
print("  3. OpenRouter is a fallback option (Gemini)")
print("\nNote: At least ONE valid API key is required.")
print("=" * 70)
