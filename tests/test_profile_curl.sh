#!/bin/bash

# Test Profile Extractor API using cURL
# This tests multimodal input: image + text + audio + JSON profile

echo "=========================================="
echo "Profile Extractor API - cURL Test"
echo "=========================================="

# Configuration
API_URL="http://localhost:8000/profile/extract"
USER_ID="curl_test_user_001"

# Find test files
IMAGE_FILE=""
AUDIO_FILE=""

if [ -f "/root/blue-psychology-test/images/photo_2025-07-24_07-51-39.jpg" ]; then
    IMAGE_FILE="/root/blue-psychology-test/images/photo_2025-07-24_07-51-39.jpg"
elif [ -f "/root/blue-psychology-test/images/neuron_session.png" ]; then
    IMAGE_FILE="/root/blue-psychology-test/images/neuron_session.png"
fi

if [ -f "/root/blue-psychology-test/tools/voice/generated_voice_0.wav" ]; then
    AUDIO_FILE="/root/blue-psychology-test/tools/voice/generated_voice_0.wav"
fi

# Test text message
TEXT_MESSAGE="My name is Alex Martinez and I'm 30 years old. I work as a data scientist and I love machine learning, yoga, and travel."

# Existing profile JSON
EXISTING_PROFILE='{
  "user_id": "'$USER_ID'",
  "name": "Alex",
  "age": 29,
  "occupation": "Data Analyst",
  "interests": ["statistics", "running"],
  "contact": {
    "email": "alex@example.com",
    "phone": null,
    "address": null
  },
  "physical_attributes": {
    "hair_color": null,
    "eye_color": null,
    "height": null,
    "build": null
  },
  "voice_profile": {
    "accent": null,
    "pitch": null,
    "pace": null,
    "tone": null
  },
  "preferences": {},
  "bio": "Data analyst",
  "extracted_from": ["text"],
  "last_updated": "2025-01-01T00:00:00",
  "confidence": 0.7
}'

echo ""
echo "📋 Test Configuration:"
echo "  User ID: $USER_ID"
echo "  API URL: $API_URL"
echo "  Image: ${IMAGE_FILE:-"Not found"}"
echo "  Audio: ${AUDIO_FILE:-"Not found"}"
echo "  Text: ${TEXT_MESSAGE:0:50}..."
echo ""

# Build curl command
CURL_CMD="curl -X POST \"$API_URL\" \\"

# Add form fields
CURL_CMD="$CURL_CMD
  -F \"user_id=$USER_ID\" \\"

CURL_CMD="$CURL_CMD
  -F \"user_profile=$EXISTING_PROFILE\" \\"

CURL_CMD="$CURL_CMD
  -F \"text_messages=$TEXT_MESSAGE\" \\"

# Add image if available
if [ -n "$IMAGE_FILE" ]; then
    echo "📷 Adding image: $IMAGE_FILE"
    CURL_CMD="$CURL_CMD
  -F \"images=@$IMAGE_FILE\" \\"
fi

# Add audio if available
if [ -n "$AUDIO_FILE" ]; then
    echo "🎵 Adding audio: $AUDIO_FILE"
    CURL_CMD="$CURL_CMD
  -F \"audios=@$AUDIO_FILE\" \\"
fi

# Test with voice file
if [ -n "$AUDIO_FILE" ]; then
    echo "🎵 Testing voice profile extraction..."
    CURL_CMD="$CURL_CMD
  -F \"audios=@$AUDIO_FILE\" \\"
fi

# Remove trailing backslash and add output formatting
CURL_CMD="${CURL_CMD%\\*}"
CURL_CMD="$CURL_CMD
  -H \"Accept: application/json\" \\"

CURL_CMD="$CURL_CMD
  -w \"\\n\\n📊 HTTP Status: %{http_code}\\n\" \\"

CURL_CMD="$CURL_CMD
  -o /tmp/profile_response.json"

echo ""
echo "🚀 Sending request..."
echo ""

# Execute curl command
eval $CURL_CMD

# Display response
echo ""
echo "📄 Response:"
if [ -f "/tmp/profile_response.json" ]; then
    cat /tmp/profile_response.json | python3 -m json.tool
    echo ""
    
    # Check if profile was saved
    PROFILE_PATH="/root/blue-psychology-test/database/user_profiles/${USER_ID}_profile.json"
    echo ""
    echo "🔍 Checking saved profile..."
    if [ -f "$PROFILE_PATH" ]; then
        echo "✅ Profile saved to: $PROFILE_PATH"
        echo ""
        echo "📁 Saved Profile:"
        cat "$PROFILE_PATH" | python3 -m json.tool
    else
        echo "❌ Profile file not found at: $PROFILE_PATH"
    fi
else
    echo "❌ No response received"
fi

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
