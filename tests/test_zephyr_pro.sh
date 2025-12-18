#!/bin/bash
# Generate Persian TTS with Zephyr voice and Pro model

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎤 TTS Request Details:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Text:  سلام خوبی"
echo "🎵 Voice: zephyr"
echo "🤖 Model: gemini-2.5-pro-preview-tts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⏳ Generating audio..."
echo ""

# Make the request
curl -X POST 'http://localhost:15800/tts/generate' \
  -H 'Content-Type: application/json' \
  -d '{"text": "سلام خوبی", "voice": "zephyr", "voice_model": "gemini-2.5-pro-preview-tts"}' \
  -o /tmp/persian_zephyr_pro.wav \
  -w "\n📊 HTTP Status: %{http_code}\n📥 Size Downloaded: %{size_download} bytes\n⏱️  Total Time: %{time_total}s\n"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📁 Generated File Info:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "/tmp/persian_zephyr_pro.wav" ]; then
    FILE_SIZE=$(ls -lh /tmp/persian_zephyr_pro.wav | awk '{print $5}')
    FILE_TYPE=$(file -b /tmp/persian_zephyr_pro.wav)
    
    # Check if it's actually an audio file or error message
    if [[ "$FILE_TYPE" == *"RIFF"* ]] || [[ "$FILE_TYPE" == *"WAVE"* ]]; then
        echo "✅ SUCCESS!"
        echo ""
        echo "📥 Downloaded Path: /tmp/persian_zephyr_pro.wav"
        echo "📏 File Size:       $FILE_SIZE"
        echo "🎵 File Type:       $FILE_TYPE"
        echo ""
        echo "📂 Server Storage:"
        echo "   Path: /root/blue-psychology-test/tools/voice/"
        echo ""
        echo "   Latest files:"
        ls -lht /root/blue-psychology-test/tools/voice/ | head -4 | tail -3 | awk '{print "   • " $9 " (" $5 ")"}'
    else
        echo "❌ FAILED - Received error response:"
        echo ""
        cat /tmp/persian_zephyr_pro.wav | head -c 500
        echo ""
    fi
else
    echo "❌ File not created"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
