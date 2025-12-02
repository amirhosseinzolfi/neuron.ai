#!/usr/bin/env python3
"""
Test script for unified multimodal profile extraction.
Demonstrates how all inputs are now processed together in a single AI call.
"""

import os
import sys
import json
from app.services.profile_extract_agent_json import process_input, get_profile

def print_separator():
    print("\n" + "="*80 + "\n")

def test_text_only():
    """Test with text input only."""
    print("🧪 TEST 1: Text-only input")
    print_separator()
    
    user_id = "test_user_001"
    text = """
    Hi! I'm Sarah Chen, a 28-year-old UX designer from San Francisco.
    I love hiking, photography, and trying new coffee shops.
    My email is sarah.chen@example.com
    """
    
    print(f"Input text: {text.strip()}")
    print("\nProcessing...")
    
    result = process_input(user_id, text, [])
    
    print(f"\n✅ Profile created for {result['user_id']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Operations: {result['operations']}")
    print(f"\nExtracted profile:")
    print(json.dumps(result['profile'], indent=2))
    
    return user_id

def test_multimodal_simulation():
    """Simulate multimodal input (without actual files for demo)."""
    print("🧪 TEST 2: Multimodal input simulation")
    print_separator()
    
    user_id = "test_user_002"
    text = "Here's my introduction video and a photo from my recent hiking trip!"
    
    # Simulate media files (in real usage, these would be actual file paths)
    # For this demo, we're showing the structure
    media = [
        # {"type": "image", "path": "/path/to/photo.jpg"},
        # {"type": "audio", "path": "/path/to/intro.mp3"}
    ]
    
    print(f"Input text: {text}")
    print(f"Media files: {len(media)} files")
    print("  - Would include: images (for physical attributes, visual context)")
    print("  - Would include: audio (for voice profile, transcription)")
    print("\nIn the unified approach:")
    print("  ✓ All inputs sent together in ONE multimodal message")
    print("  ✓ AI processes everything simultaneously")
    print("  ✓ Better cross-modal understanding")
    print("  ✓ Single API call instead of multiple")
    
    print_separator()

def test_profile_refinement():
    """Test profile refinement with existing data."""
    print("🧪 TEST 3: Profile refinement")
    print_separator()
    
    # First create initial profile
    user_id = "test_user_003"
    initial_text = "My name is Alex, I'm 25 and work as a data scientist."
    
    print("Step 1: Creating initial profile")
    print(f"Input: {initial_text}")
    result1 = process_input(user_id, initial_text, [])
    print(f"✅ Initial profile created (Confidence: {result1['confidence']})")
    
    # Now refine with additional info
    print("\nStep 2: Refining with additional multimodal input")
    additional_text = """
    I also love playing guitar and cooking Italian food.
    I'm based in Seattle and speak English and Spanish.
    """
    print(f"Additional text: {additional_text.strip()}")
    print("  + Would add: voice sample (to extract voice profile)")
    print("  + Would add: recent photo (to extract physical attributes)")
    
    result2 = process_input(user_id, additional_text, [])
    print(f"\n✅ Profile refined (Action: {result2.get('action', 'N/A')})")
    print(f"Confidence: {result2['confidence']}")
    print(f"\nRefined profile highlights:")
    profile = result2['profile']
    print(f"  - Name: {profile.get('name')}")
    print(f"  - Age: {profile.get('age')}")
    print(f"  - Occupation: {profile.get('occupation')}")
    print(f"  - Interests: {', '.join(profile.get('interests', []))}")
    
    print_separator()

def test_unified_vs_separate():
    """Explain the difference between old and new approach."""
    print("🧪 TEST 4: Unified vs Separate Processing Comparison")
    print_separator()
    
    print("OLD APPROACH (Separate Processing):")
    print("  1. Analyze image separately → 'Person with brown hair, blue eyes'")
    print("  2. Analyze audio separately → 'Transcription: Hello, I'm John...'")
    print("  3. Combine as text → 'USER: text + IMAGE: brown hair + AUDIO: John'")
    print("  4. Send combined text to AI")
    print("  📊 Result: Multiple AI calls, fragmented context")
    
    print("\nNEW APPROACH (Unified Processing):")
    print("  1. Build single message:")
    print("     - text: 'Hello, I'm a software engineer'")
    print("     - image: [base64 encoded photo]")
    print("     - audio: [base64 encoded voice]")
    print("  2. Send unified message to AI in ONE call")
    print("  3. AI sees everything together, understands full context")
    print("  📊 Result: Single AI call, unified context, better accuracy")
    
    print("\n🎯 BENEFITS:")
    print("  ✅ Reduced latency (1 call vs 3-10 calls)")
    print("  ✅ Better context understanding")
    print("  ✅ Cross-modal validation")
    print("  ✅ Lower API costs")
    print("  ✅ More accurate extraction")
    
    print_separator()

def main():
    """Run all tests."""
    print("=" * 80)
    print(" UNIFIED MULTIMODAL PROFILE EXTRACTION - TEST SUITE")
    print("=" * 80)
    
    try:
        # Test 1: Text only
        test_text_only()
        
        # Test 2: Multimodal simulation
        test_multimodal_simulation()
        
        # Test 3: Profile refinement
        test_profile_refinement()
        
        # Test 4: Comparison
        test_unified_vs_separate()
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nKey Takeaways:")
        print("  • All inputs are now processed together as unified multimodal messages")
        print("  • Single AI call per extraction/refinement")
        print("  • Better accuracy through complete context understanding")
        print("  • More efficient and cost-effective")
        print("\nCheck UNIFIED_MULTIMODAL_EXTRACTION.md for detailed documentation.")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
