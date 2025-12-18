"""
Comprehensive test for Profile Extractor API
Tests multimodal input (image + text + audio + JSON profile)
"""
import requests
import json
import os
from pathlib import Path

# API Configuration
BASE_URL = "http://localhost:15801"
PROFILE_ENDPOINT = f"{BASE_URL}/profile/extract"

# Test Data
TEST_USER_ID = "test_user_12345"
TEST_TEXT = """
My name is Sarah Johnson and I'm 28 years old. I work as a software engineer.
I love hiking, photography, and playing guitar. I have brown hair and blue eyes.
My email is sarah.johnson@example.com and I live in San Francisco.
"""

# Existing profile to test refinement
EXISTING_PROFILE = {
    "user_id": TEST_USER_ID,
    "name": "Sarah",
    "age": 27,
    "occupation": "Developer",
    "interests": ["coding", "reading"],
    "contact": {
        "email": "sarah@example.com",
        "phone": None,
        "address": None
    },
    "physical_attributes": {
        "hair_color": None,
        "eye_color": None,
        "height": None,
        "build": None
    },
    "voice_profile": {
        "accent": None,
        "pitch": None,
        "pace": None,
        "tone": None
    },
    "preferences": {},
    "bio": "Software developer",
    "extracted_from": ["text"],
    "last_updated": "2025-01-01T00:00:00",
    "confidence": 0.7
}

def find_test_files():
    """Find available test files in the workspace"""
    workspace = Path("/root/blue-psychology-test")
    
    # Look for image files
    image_paths = [
        workspace / "images" / "photo_1_2025-04-16_05-26-42.jpg",
        workspace / "images" / "photo_2025-07-24_07-51-39.jpg",
        workspace / "images" / "neuron_session.png",
    ]
    test_image = None
    for img in image_paths:
        if img.exists():
            test_image = str(img)
            break
    
    # Look for audio files
    audio_paths = [
        workspace / "tools" / "voice" / "generated_voice_0.wav",
    ]
    test_audio = None
    for aud in audio_paths:
        if aud.exists():
            test_audio = str(aud)
            break
    
    return test_image, test_audio

def test_profile_extraction_multimodal():
    """
    Test 1: Full multimodal extraction (image + text + audio + JSON profile)
    """
    print("=" * 80)
    print("TEST 1: Multimodal Profile Extraction (Image + Text + Audio + JSON Profile)")
    print("=" * 80)
    
    test_image, test_audio = find_test_files()
    
    if not test_image:
        print("⚠️  No test image found, continuing with text only")
    if not test_audio:
        print("⚠️  No test audio found, continuing without audio")
    
    # Prepare multipart form data
    files = []
    data = {
        'user_id': TEST_USER_ID,
        'user_profile': json.dumps(EXISTING_PROFILE),
        'text_messages': TEST_TEXT
    }
    
    # Add image if available
    if test_image:
        files.append(('images', ('test_image.jpg', open(test_image, 'rb'), 'image/jpeg')))
        print(f"📷 Using image: {test_image}")
    
    # Add audio if available
    if test_audio:
        files.append(('audios', ('test_audio.wav', open(test_audio, 'rb'), 'audio/wav')))
        print(f"🎵 Using audio: {test_audio}")
    
    print(f"📝 Using text: {TEST_TEXT[:50]}...")
    print(f"👤 User ID: {TEST_USER_ID}")
    print(f"📋 Existing profile provided: Yes")
    print("\n🚀 Sending request to API...")
    
    try:
        response = requests.post(PROFILE_ENDPOINT, data=data, files=files)
        
        # Close file handles
        for _, file_tuple in files:
            file_tuple[1].close()
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS! Profile extracted/refined")
            print("\n📄 Response Data:")
            print(json.dumps(result, indent=2))
            
            # Verify key fields
            profile = result.get('profile', {})
            print("\n🔍 Profile Verification:")
            print(f"  - User ID: {result.get('user_id')}")
            print(f"  - Name: {profile.get('name')}")
            print(f"  - Age: {profile.get('age')}")
            print(f"  - Occupation: {profile.get('occupation')}")
            print(f"  - Interests: {profile.get('interests')}")
            print(f"  - Email: {profile.get('contact', {}).get('email')}")
            print(f"  - Hair Color: {profile.get('physical_attributes', {}).get('hair_color')}")
            print(f"  - Eye Color: {profile.get('physical_attributes', {}).get('eye_color')}")
            print(f"  - Action: {result.get('action')}")
            print(f"  - Confidence: {result.get('confidence')}")
            print(f"  - Extracted From: {profile.get('extracted_from')}")
            
            return True
        else:
            print(f"\n❌ FAILED! Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

def test_text_only_extraction():
    """
    Test 2: Text-only extraction (no existing profile)
    """
    print("\n" + "=" * 80)
    print("TEST 2: Text-Only Profile Extraction (New User)")
    print("=" * 80)
    
    new_user_id = "new_user_67890"
    text = "Hi! I'm John Smith, a 35-year-old architect from New York. I enjoy running and cooking."
    
    data = {
        'user_id': new_user_id,
        'text_messages': text
    }
    
    print(f"📝 Text: {text}")
    print(f"👤 User ID: {new_user_id}")
    print("📋 Existing profile: None")
    print("\n🚀 Sending request...")
    
    try:
        response = requests.post(PROFILE_ENDPOINT, data=data)
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS! New profile created")
            print("\n📄 Response:")
            print(json.dumps(result, indent=2))
            return True
        else:
            print(f"\n❌ FAILED! Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

def test_image_only_extraction():
    """
    Test 3: Image-only extraction
    """
    print("\n" + "=" * 80)
    print("TEST 3: Image-Only Profile Extraction")
    print("=" * 80)
    
    test_image, _ = find_test_files()
    
    if not test_image:
        print("⚠️  No test image found, skipping test")
        return None
    
    image_user_id = "image_user_111"
    
    files = [
        ('images', ('test_image.jpg', open(test_image, 'rb'), 'image/jpeg'))
    ]
    
    data = {
        'user_id': image_user_id,
        'text_messages': 'Please analyze this image and extract profile information.'
    }
    
    print(f"📷 Image: {test_image}")
    print(f"👤 User ID: {image_user_id}")
    print("\n🚀 Sending request...")
    
    try:
        response = requests.post(PROFILE_ENDPOINT, data=data, files=files)
        files[0][1][1].close()
        
        print(f"\n📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS! Profile extracted from image")
            print("\n📄 Response:")
            print(json.dumps(result, indent=2))
            return True
        else:
            print(f"\n❌ FAILED! Status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return False

def check_saved_profile(user_id: str):
    """
    Verify that profile was saved to file
    """
    print("\n" + "=" * 80)
    print(f"VERIFICATION: Checking saved profile for {user_id}")
    print("=" * 80)
    
    profile_path = f"/root/blue-psychology-test/database/user_profiles/{user_id}_profile.json"
    
    if os.path.exists(profile_path):
        print(f"✅ Profile file exists: {profile_path}")
        
        with open(profile_path, 'r') as f:
            profile_data = json.load(f)
        
        print("\n📄 Saved Profile Content:")
        print(json.dumps(profile_data, indent=2))
        return True
    else:
        print(f"❌ Profile file NOT found: {profile_path}")
        return False

def run_all_tests():
    """Run all tests"""
    print("\n" + "🧪" * 40)
    print("PROFILE EXTRACTOR API - COMPREHENSIVE TEST SUITE")
    print("🧪" * 40)
    
    # Check if API is running
    print("\n🔍 Checking API availability...")
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print(f"✅ API is running at {BASE_URL}")
        else:
            print(f"⚠️  API responded with status {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to API at {BASE_URL}")
        print(f"   Error: {str(e)}")
        print("\n💡 Make sure to start the API first:")
        print("   python -m uvicorn app.main:app --reload --port 8000")
        return
    
    results = []
    
    # Test 1: Full multimodal
    results.append(("Multimodal Extraction", test_profile_extraction_multimodal()))
    check_saved_profile(TEST_USER_ID)
    
    # Test 2: Text only
    results.append(("Text-Only Extraction", test_text_only_extraction()))
    check_saved_profile("new_user_67890")
    
    # Test 3: Image only
    image_result = test_image_only_extraction()
    if image_result is not None:
        results.append(("Image-Only Extraction", image_result))
        check_saved_profile("image_user_111")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {test_name}")
    
    total = len(results)
    passed = sum(1 for _, r in results if r)
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed successfully!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    run_all_tests()
