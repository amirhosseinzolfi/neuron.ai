#!/usr/bin/env python3
"""
Quick test for Profile Extractor API
Tests basic functionality with text only first, then multimodal
"""

import requests
import json
import os

API_BASE = "http://localhost:15801"

def test_text_only():
    """Quick test with text only"""
    print("=" * 60)
    print("🧪 TEST 1: Text-Only Profile Extraction")
    print("=" * 60)
    
    endpoint = f"{API_BASE}/profile/extract"
    
    data = {
        'user_id': 'quick_test_001',
        'text_messages': 'My name is Alex and I am 25 years old. I work as a data scientist.'
    }
    
    print(f"📝 Text: {data['text_messages']}")
    print(f"🚀 Sending to {endpoint}")
    
    try:
        response = requests.post(endpoint, data=data, timeout=30)
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print(f"   User ID: {result['user_id']}")
            print(f"   Name: {result['profile'].get('name')}")
            print(f"   Age: {result['profile'].get('age')}")
            print(f"   Occupation: {result['profile'].get('occupation')}")
            print(f"   Confidence: {result['confidence']}")
            return True
        else:
            print(f"❌ FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_with_image():
    """Test with image + text"""
    print("\n" + "=" * 60)
    print("🧪 TEST 2: Image + Text Profile Extraction")
    print("=" * 60)
    
    endpoint = f"{API_BASE}/profile/extract"
    image_path = "images/photo_1_2025-04-16_05-26-42.jpg"
    
    if not os.path.exists(image_path):
        print(f"⚠️  Image not found: {image_path}")
        return None
    
    files = {
        'images': ('test.jpg', open(image_path, 'rb'), 'image/jpeg')
    }
    
    data = {
        'user_id': 'quick_test_002',
        'text_messages': 'Analyze this image and extract information.'
    }
    
    print(f"📷 Image: {image_path}")
    print(f"🚀 Sending to {endpoint}")
    
    try:
        response = requests.post(endpoint, data=data, files=files, timeout=60)
        files['images'][1].close()
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print(f"   User ID: {result['user_id']}")
            print(f"   Action: {result.get('action')}")
            print(f"   Confidence: {result['confidence']}")
            print(f"   Extracted from: {result['profile'].get('extracted_from')}")
            return True
        else:
            print(f"❌ FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_multimodal_full():
    """Test with image + audio + text + JSON profile"""
    print("\n" + "=" * 60)
    print("🧪 TEST 3: Full Multimodal (Image+Audio+Text+JSON)")
    print("=" * 60)
    
    endpoint = f"{API_BASE}/profile/extract"
    image_path = "images/photo_1_2025-04-16_05-26-42.jpg"
    audio_path = "tools/voice/generated_voice_0.wav"
    
    # Check files
    if not os.path.exists(image_path):
        print(f"⚠️  Image not found: {image_path}")
        return None
    
    if not os.path.exists(audio_path):
        print(f"⚠️  Audio not found: {audio_path}")
        return None
    
    existing_profile = {
        "name": "Test User",
        "age": 30,
        "occupation": "Engineer",
        "interests": ["tech"]
    }
    
    files = {
        'images': ('photo.jpg', open(image_path, 'rb'), 'image/jpeg'),
        'audios': ('voice.wav', open(audio_path, 'rb'), 'audio/wav')
    }
    
    data = {
        'user_id': 'quick_test_003',
        'user_profile': json.dumps(existing_profile),
        'text_messages': json.dumps([
            "I'm a senior software engineer with 10 years experience",
            "I love hiking and photography"
        ])
    }
    
    print(f"📷 Image: {image_path}")
    print(f"🎵 Audio: {audio_path}")
    print(f"📝 Text: 2 messages")
    print(f"📋 Profile: Yes")
    print(f"🚀 Sending to {endpoint}")
    
    try:
        response = requests.post(endpoint, data=data, files=files, timeout=90)
        
        # Close files
        files['images'][1].close()
        files['audios'][1].close()
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS!")
            print(f"   User ID: {result['user_id']}")
            print(f"   Action: {result.get('action')}")
            print(f"   Confidence: {result['confidence']:.2f}")
            print(f"   Name: {result['profile'].get('name')}")
            print(f"   Age: {result['profile'].get('age')}")
            print(f"   Occupation: {result['profile'].get('occupation')}")
            print(f"   Interests: {result['profile'].get('interests')}")
            print(f"   Extracted from: {result['profile'].get('extracted_from')}")
            
            # Check saved file
            profile_file = f"database/user_profiles/{result['user_id']}_profile.json"
            if os.path.exists(profile_file):
                print(f"\n✅ Profile saved to: {profile_file}")
            
            return True
        else:
            print(f"❌ FAILED: {response.text}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    print("\n🔬 QUICK PROFILE EXTRACTOR API TEST")
    print(f"🌐 API: {API_BASE}\n")
    
    # Check API
    try:
        response = requests.get(f"{API_BASE}/docs", timeout=5)
        print(f"✅ API is running (status: {response.status_code})\n")
    except:
        print(f"❌ API not available at {API_BASE}\n")
        return
    
    results = []
    
    # Run tests
    results.append(("Text Only", test_text_only()))
    
    result2 = test_with_image()
    if result2 is not None:
        results.append(("Image + Text", result2))
    
    result3 = test_multimodal_full()
    if result3 is not None:
        results.append(("Full Multimodal", result3))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {name}")
    
    passed = sum(1 for _, r in results if r)
    print(f"\n🎯 {passed}/{len(results)} tests passed")


if __name__ == "__main__":
    main()
