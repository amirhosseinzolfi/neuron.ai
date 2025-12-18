#!/usr/bin/env python3
"""
Test script to validate Mem0 memory extraction fixes.
Run this to verify the memory decision logic works correctly.
"""

import sys
from app.chat.smart_chat import _ai_decides_memory_worthy, _extract_text_content
from ai_utils import get_neuron_llm
from langchain_core.messages import AIMessage

def test_memory_decision():
    """Test the memory decision logic with various inputs."""
    
    print("🧪 Testing Memory Decision Logic\n")
    print("=" * 70)
    
    llm = get_neuron_llm()
    
    test_cases = [
        # (user_text, ai_text, expected_result, description)
        ("یادت باشه من برنامه نویسم", "حتماً! من به یاد دارم.", True, "Explicit memory request (Persian)"),
        ("Remember I'm a graphic designer", "Sure, I'll remember that.", True, "Explicit memory request (English)"),
        ("من یک معلم هستم", "خوب است.", True, "Identity statement (Persian)"),
        ("I am a software engineer", "Great!", True, "Identity statement (English)"),
        ("My name is Ali", "Nice to meet you Ali.", True, "Personal info - name"),
        ("I love reading psychology books", "That's interesting!", True, "Personal preference"),
        ("سلام", "سلام! خوش برگشتید.", False, "Simple greeting only"),
        ("خب", "چطور می‌تونم کمکتون کنم؟", False, "Single word response"),
        ("ok", "How can I help?", False, "Single word English"),
        ("", "Hello!", False, "Empty message"),
        ("I work as a teacher in Tehran", "That's wonderful!", True, "Job + location"),
        ("I'm 25 years old", "Got it.", True, "Personal info - age"),
    ]
    
    passed = 0
    failed = 0
    
    for user_text, ai_text, expected, description in test_cases:
        print(f"\n📝 Test: {description}")
        print(f"   User: '{user_text}'")
        print(f"   AI: '{ai_text}'")
        print(f"   Expected: {'✅ STORE' if expected else '❌ SKIP'}")
        
        try:
            result = _ai_decides_memory_worthy(llm, user_text, ai_text)
            actual = "✅ STORE" if result else "❌ SKIP"
            
            if result == expected:
                print(f"   Result: {actual} ✅ PASS")
                passed += 1
            else:
                print(f"   Result: {actual} ❌ FAIL (expected {'STORE' if expected else 'SKIP'})")
                failed += 1
                
        except Exception as e:
            print(f"   Result: ❌ ERROR - {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"\n📊 Test Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    
    if failed == 0:
        print("✅ All tests passed!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1


def test_content_extraction():
    """Test content extraction from different message types."""
    
    print("\n\n🧪 Testing Content Extraction\n")
    print("=" * 70)
    
    test_cases = [
        # String content
        AIMessage(content="Simple string response"),
        # List content (multimodal)
        AIMessage(content=[
            {"type": "text", "text": "First part"},
            {"type": "text", "text": "Second part"}
        ]),
        # Mixed content
        AIMessage(content=[
            {"type": "text", "text": "Text content"},
            {"type": "image_url", "image_url": "data:image/png;base64,abc123"}
        ]),
    ]
    
    for i, msg in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}:")
        print(f"   Content type: {type(msg.content)}")
        print(f"   Content: {msg.content}")
        
        try:
            extracted = _extract_text_content(msg)
            print(f"   Extracted: '{extracted}' ✅")
        except Exception as e:
            print(f"   Error: {e} ❌")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("🚀 Starting Memory Fix Validation Tests\n")
    
    try:
        # Test content extraction first
        test_content_extraction()
        
        # Test memory decision logic
        exit_code = test_memory_decision()
        
        print("\n✅ Testing completed!")
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
