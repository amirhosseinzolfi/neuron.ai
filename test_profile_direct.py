#!/usr/bin/env python3
"""Direct test of profile extraction without API server"""
import sys
sys.path.insert(0, '/root/blue-psychology-test')

from app.services.profile_extract_agent_json import process_input
import json

# Test data
TEST_USER_ID = "test_user_123"
TEST_RESULT = """
## نتایج تحلیل روانشناختی
**امتیاز:** ۰ (استرس پایین)
کاربر توانایی بالایی در مدیریت دارد.
"""

EXISTING_PROFILE = {
    "user_id": TEST_USER_ID,
    "core_info": {"name": "Test User", "age": 26, "occupation": "Developer"},
    "professional_profile": {"skills": ["Python"], "career_summary": None, "job_history": []},
    "personal_outlook": {"interests": ["AI"], "goals": [], "values": []}
}

print("🧪 Direct Profile Extraction Test")
print("=" * 60)

try:
    result = process_input(
        user_id=TEST_USER_ID,
        message=TEST_RESULT,
        media=[],
        existing_profile=EXISTING_PROFILE,
        persist=False
    )
    
    print("✅ SUCCESS!")
    print(f"   User ID: {result['user_id']}")
    print(f"   Confidence: {result['confidence']:.2f}")
    print(f"   Action: {result['action']}")
    print(f"\n📊 Profile:")
    profile = result['profile']
    print(f"   Name: {profile.get('core_info', {}).get('name')}")
    print(f"   Age: {profile.get('core_info', {}).get('age')}")
    print("\n✅ Test PASSED")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
