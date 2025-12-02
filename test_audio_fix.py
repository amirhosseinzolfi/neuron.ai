#!/usr/bin/env python3
"""
Test script to verify audio processing fix
"""

import os
import tempfile
import requests
from pathlib import Path

def create_test_ogg_file():
    """Create a minimal OGG file for testing"""
    # Minimal OGG header for testing
    ogg_header = b'OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as f:
        f.write(ogg_header)
        return f.name

def test_profile_extraction_api():
    """Test the profile extraction API with audio"""
    print("🧪 Testing profile extraction API with audio...")
    
    # Create test audio file
    audio_path = create_test_ogg_file()
    
    try:
        print(f"📁 Created test audio file: {audio_path}")
        print(f"   File exists: {os.path.exists(audio_path)}")
        print(f"   File size: {os.path.getsize(audio_path)} bytes")
        
        # Test data
        data = {
            "user_id": "test_999999",
            "text_messages": '["سلام، نام من امیرحسن است و ۲۶ ساله هستم", "من برنامهنویس هستم"]'
        }
        
        # Test with audio file
        with open(audio_path, 'rb') as audio_file:
            files = [('audios', audio_file)]
            
            print("\n🚀 Calling profile extraction API...")
            response = requests.post(
                "http://localhost:15800/profile/extract",
                data=data,
                files=files,
                timeout=30
            )
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API call successful!")
            print(f"   User ID: {result.get('user_id')}")
            print(f"   Action: {result.get('action')}")
            print(f"   Confidence: {result.get('confidence')}")
            
            profile = result.get('profile', {})
            print(f"   Name: {profile.get('name', 'N/A')}")
            print(f"   Age: {profile.get('age', 'N/A')}")
            print(f"   Occupation: {profile.get('occupation', 'N/A')}")
            
            # Check if voice profile was extracted
            voice_profile = profile.get('voice_profile', {})
            if any(voice_profile.values()):
                print(f"   Voice Profile: {voice_profile}")
            else:
                print("   Voice Profile: Not extracted")
                
        else:
            print(f"❌ API call failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to profile extraction API")
        print("   Make sure the API is running on http://localhost:15800")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        try:
            Path(audio_path).unlink(missing_ok=True)
            print(f"🗑️ Cleaned up test file: {audio_path}")
        except Exception as e:
            print(f"⚠️ Could not clean up {audio_path}: {e}")

def test_api_health():
    """Test if the profile extraction API is running"""
    print("🏥 Testing API health...")
    
    try:
        response = requests.get("http://localhost:15800/docs", timeout=5)
        if response.status_code == 200:
            print("✅ Profile extraction API is running")
            return True
        else:
            print(f"⚠️ API responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Profile extraction API is not running")
        print("   Start it with: python -m uvicorn app.main:app --host 0.0.0.0 --port 15800")
        return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testing audio processing fix...")
    print("=" * 50)
    
    # Test API health first
    if test_api_health():
        print()
        # Test profile extraction with audio
        test_profile_extraction_api()
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")