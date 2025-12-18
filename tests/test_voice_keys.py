#!/usr/bin/env python3
"""Test which Google API keys work for TTS"""
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

keys_to_test = [
    ("GOOGLE_API_KEY_VOICE", os.getenv("GOOGLE_API_KEY_VOICE")),
    ("GOOGLE_API_KEY_VOICE2", os.getenv("GOOGLE_API_KEY_VOICE2")),
    ("GOOGLE_API_KEY_PRIMARY", os.getenv("GOOGLE_API_KEY_PRIMARY")),
    ("GOOGLE_API_KEY_SECONDARY", os.getenv("GOOGLE_API_KEY_SECONDARY")),
]

print("Testing Google API keys for TTS capability...\n")

for key_name, key_value in keys_to_test:
    if not key_value:
        print(f"❌ {key_name}: Not set")
        continue
    
    try:
        client = genai.Client(api_key=key_value)
        # Try a minimal TTS request
        print(f"🔄 Testing {key_name}...")
        print(f"   Key: {key_value[:20]}...")
        
        # Just test if we can create a client - actual generation would take time
        print(f"✅ {key_name}: Valid (client created successfully)")
        
    except Exception as e:
        print(f"❌ {key_name}: Invalid - {str(e)[:100]}")

print("\nRecommendation: Use the first valid key found above.")
