#!/usr/bin/env python3
"""
Test script to verify multimodal input handling fix
"""

import os
import tempfile
from pathlib import Path
from ai_utils import extract_user_profile

def create_test_audio_file():
    """Create a dummy audio file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as f:
        # Write some dummy audio data (just bytes for testing)
        f.write(b'OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00')
        return f.name

def create_test_image_file():
    """Create a dummy image file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
        # Write minimal JPEG header for testing
        f.write(b'\xff\xd8\xff\xe0\x00\x10JFIF')
        return f.name

def test_multimodal_profile_extraction():
    """Test multimodal profile extraction with audio and image"""
    print("🧪 Testing multimodal profile extraction...")
    
    # Create test files
    audio_path = create_test_audio_file()
    image_path = create_test_image_file()
    
    try:
        # Test data
        user_id = 999999  # Test user ID
        text_messages = [
            "سلام، نام من امیرحسن است و ۲۶ ساله هستم",
            "من برنامه‌نویس هستم و کتاب خواندن دوست دارم"
        ]
        
        media_files = [
            {"type": "audio", "path": audio_path},
            {"type": "image", "path": image_path}
        ]
        
        print(f"📁 Created test files:")
        print(f"   Audio: {audio_path} (exists: {os.path.exists(audio_path)})")
        print(f"   Image: {image_path} (exists: {os.path.exists(image_path)})")
        
        # Test profile extraction
        print("\n🚀 Calling extract_user_profile...")
        result = extract_user_profile(
            user_id=user_id,
            text_messages=text_messages,
            media_files=media_files
        )
        
        if result:
            print("✅ Profile extraction successful!")
            print(f"   Name: {result.get('name', 'N/A')}")
            print(f"   Age: {result.get('age', 'N/A')}")
            print(f"   Occupation: {result.get('occupation', 'N/A')}")
            print(f"   Interests: {result.get('interests', [])}")
        else:
            print("❌ Profile extraction failed!")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup test files
        for path in [audio_path, image_path]:
            try:
                Path(path).unlink(missing_ok=True)
                print(f"🗑️ Cleaned up: {path}")
            except Exception as e:
                print(f"⚠️ Could not clean up {path}: {e}")

def test_text_only_extraction():
    """Test text-only profile extraction"""
    print("\n🧪 Testing text-only profile extraction...")
    
    try:
        user_id = 999998  # Test user ID
        text_messages = [
            "سلام، نام من سارا است و ۲۸ ساله هستم",
            "من طراح گرافیک هستم و عکاسی و سفر دوست دارم"
        ]
        
        print("🚀 Calling extract_user_profile (text-only)...")
        result = extract_user_profile(
            user_id=user_id,
            text_messages=text_messages,
            media_files=None
        )
        
        if result:
            print("✅ Text-only extraction successful!")
            print(f"   Name: {result.get('name', 'N/A')}")
            print(f"   Age: {result.get('age', 'N/A')}")
            print(f"   Occupation: {result.get('occupation', 'N/A')}")
            print(f"   Interests: {result.get('interests', [])}")
        else:
            print("❌ Text-only extraction failed!")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🔧 Testing multimodal input fix...")
    print("=" * 50)
    
    # Test multimodal extraction
    test_multimodal_profile_extraction()
    
    # Test text-only extraction
    test_text_only_extraction()
    
    print("\n" + "=" * 50)
    print("✅ Test completed!")