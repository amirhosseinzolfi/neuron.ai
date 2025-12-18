#!/usr/bin/env python3
"""Test script for Image Generation API"""

import requests
import json
from pathlib import Path


def test_image_generation():
    """Test the image generation endpoint"""
    
    # API endpoint
    url = "http://localhost:15800/image/generate"
    
    # Test prompt
    payload = {
        "text": "A 3D cute character representing a calm and creative personality, blue and purple background, minimalist style",
        "model": "flux",
        "width": 512,
        "height": 512,
        "num_images": 1
    }
    
    print("🎨 Testing Image Generation API...")
    print(f"📝 Prompt: {payload['text']}")
    print(f"🎯 Model: {payload['model']}")
    print(f"📐 Size: {payload['width']}x{payload['height']}")
    print("\n⏳ Generating image...")
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        
        if response.status_code == 200:
            # Save the image
            output_path = Path("test_generated_image.png")
            output_path.write_bytes(response.content)
            print(f"✅ Success! Image saved to: {output_path}")
            print(f"📊 File size: {len(response.content)} bytes")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out. Image generation may take longer.")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_multiple_images():
    """Test generating multiple images"""
    
    url = "http://localhost:15800/image/generate-multiple"
    
    payload = {
        "text": "Abstract 3D personality visualization with blue tones",
        "model": "flux",
        "width": 512,
        "height": 512,
        "num_images": 2
    }
    
    print("\n🎨 Testing Multiple Image Generation...")
    print(f"📝 Prompt: {payload['text']}")
    print(f"🔢 Number of images: {payload['num_images']}")
    print("\n⏳ Generating images...")
    
    try:
        response = requests.post(url, json=payload, timeout=240)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Generated {data['count']} images")
            print("\n📁 Generated files:")
            for img in data['images']:
                print(f"  - {img['filename']}")
                print(f"    URL: {img['url']}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def test_health():
    """Test API health endpoint"""
    
    print("\n🏥 Testing API Health...")
    
    try:
        response = requests.get("http://localhost:15800/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ API is healthy: {response.json()}")
        else:
            print(f"⚠️ API returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach API: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Image Generation API Test Suite")
    print("=" * 60)
    
    # Test health first
    test_health()
    
    # Test single image generation
    test_image_generation()
    
    # Test multiple images
    test_multiple_images()
    
    print("\n" + "=" * 60)
    print("✨ Test suite completed!")
    print("=" * 60)
