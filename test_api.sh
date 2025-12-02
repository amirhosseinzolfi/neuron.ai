#!/bin/bash

# Test all API endpoints

BASE_URL="http://localhost:15800"

echo "=========================================="
echo "🧪 Testing Blue Psychology API"
echo "=========================================="
echo ""

# Test 1: Health Check
echo "1️⃣  Testing Health Endpoint..."
curl -s $BASE_URL/health | python3 -m json.tool
echo ""

# Test 2: Root
echo "2️⃣  Testing Root Endpoint..."
curl -s $BASE_URL/ | python3 -m json.tool
echo ""

# Test 3: TTS
echo "3️⃣  Testing TTS Endpoint..."
curl -s -X POST $BASE_URL/tts/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice_model": "gemini-2.5-flash-preview-tts"}' \
  --output /tmp/test_audio.wav
if [ -f /tmp/test_audio.wav ]; then
    echo "✅ TTS working - audio saved to /tmp/test_audio.wav"
else
    echo "❌ TTS failed"
fi
echo ""

# Test 4: Image
echo "4️⃣  Testing Image Generation Endpoint..."
curl -s -X POST $BASE_URL/image/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "A beautiful sunset", "model": "flux", "width": 512, "height": 512}' \
  --output /tmp/test_image.png
if [ -f /tmp/test_image.png ]; then
    echo "✅ Image generation working - image saved to /tmp/test_image.png"
else
    echo "❌ Image generation failed"
fi
echo ""

# Test 5: Profile
echo "5️⃣  Testing Profile Extraction Endpoint..."
curl -s -X POST $BASE_URL/profile/extract-json \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_user", "text_messages": ["I love programming", "Python is my favorite language"]}' \
  | python3 -m json.tool
echo ""

echo "=========================================="
echo "✅ API Testing Complete"
echo "=========================================="
