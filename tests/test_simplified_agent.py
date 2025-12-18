#!/usr/bin/env python3
"""
Quick test to verify the simplified profile agent works correctly.
Tests both empty profile and existing profile scenarios.
"""

import json
import sys
sys.path.insert(0, '/root/blue-psychology-test')

from app.services.profile_extract_agent_json import process_input

print("="*80)
print("Testing Simplified Profile Extraction Agent")
print("="*80)

# Test 1: Empty profile (should generate new)
print("\n" + "="*80)
print("TEST 1: Generate New Profile (No Existing Profile)")
print("="*80)

result1 = process_input(
    user_id="test_001",
    message="""
    Test Results: امیر، 22 ساله
    نتایج تست استرس: سطح استرس پایین
    نقاط قوت: مدیریت زمان، انعطاف‌پذیری
    زمینه‌های پیشرفت: ارتباطات، کار تیمی
    """,
    media=[],
    existing_profile=None,
    persist=False
)

print("\n📊 Result:")
print(f"  Action: {result1['action']}")
print(f"  Confidence: {result1['confidence']}")
print(f"  Operations: {result1['operations']}")
print(f"\n📄 Profile Preview:")
profile1 = result1['profile']
print(f"  Name: {profile1.get('core_info', {}).get('name')}")
print(f"  Age: {profile1.get('core_info', {}).get('age')}")
print(f"  Strengths: {profile1.get('psychological_profile', {}).get('strengths')}")
print(f"  Development: {profile1.get('psychological_profile', {}).get('areas_for_development')}")

# Test 2: Update existing profile (should merge)
print("\n" + "="*80)
print("TEST 2: Update Existing Profile (Should Merge)")
print("="*80)

existing_profile = {
    "user_id": "test_002",
    "core_info": {
        "name": "امیر",
        "age": 22,
        "occupation": None
    },
    "professional_profile": {
        "career_summary": None,
        "skills": ["Python"],
        "job_history": []
    },
    "psychological_profile": {
        "summary": None,
        "personality_traits": {},
        "strengths": ["time management"],
        "areas_for_development": []
    },
    "metadata": {
        "confidence": 0.6
    }
}

result2 = process_input(
    user_id="test_002",
    message="""
    New Test Results:
    Occupation: برنامه‌نویس
    New Skills: JavaScript، React
    Stress Level: High (need work-life balance)
    New Strength: Problem-solving
    Development Area: Communication skills
    """,
    media=[],
    existing_profile=existing_profile,
    persist=False
)

print("\n📊 Result:")
print(f"  Action: {result2['action']}")
print(f"  Confidence: {result2['confidence']}")
print(f"  Operations: {result2['operations']}")
print(f"\n📄 Profile Preview:")
profile2 = result2['profile']
print(f"  Name: {profile2.get('core_info', {}).get('name')} (should be preserved)")
print(f"  Age: {profile2.get('core_info', {}).get('age')} (should be preserved)")
print(f"  Occupation: {profile2.get('core_info', {}).get('occupation')} (should be NEW)")
print(f"  Skills: {profile2.get('professional_profile', {}).get('skills')} (should have Python + new)")
print(f"  Strengths: {profile2.get('psychological_profile', {}).get('strengths')} (should have time management + new)")
print(f"  Development: {profile2.get('psychological_profile', {}).get('areas_for_development')} (should have new items)")

# Verification
print("\n" + "="*80)
print("VERIFICATION")
print("="*80)

# Check Test 1
if profile1.get('core_info', {}).get('name') and profile1.get('core_info', {}).get('age'):
    print("✅ Test 1: Profile generated with basic info")
else:
    print("❌ Test 1: Failed to extract basic info")

# Check Test 2 - preservation
name_preserved = profile2.get('core_info', {}).get('name') == "امیر"
age_preserved = profile2.get('core_info', {}).get('age') == 22
occupation_added = profile2.get('core_info', {}).get('occupation') is not None

skills = profile2.get('professional_profile', {}).get('skills', [])
skills_merged = "Python" in skills and len(skills) > 1

strengths = profile2.get('psychological_profile', {}).get('strengths', [])
strengths_merged = "time management" in strengths and len(strengths) > 1

if name_preserved and age_preserved:
    print("✅ Test 2: Existing data preserved (name, age)")
else:
    print("❌ Test 2: Failed to preserve existing data")

if occupation_added:
    print("✅ Test 2: New data added (occupation)")
else:
    print("❌ Test 2: Failed to add new data")

if skills_merged:
    print("✅ Test 2: Skills merged correctly")
else:
    print(f"❌ Test 2: Skills NOT merged - got: {skills}")

if strengths_merged:
    print("✅ Test 2: Strengths merged correctly")
else:
    print(f"❌ Test 2: Strengths NOT merged - got: {strengths}")

print("\n" + "="*80)
print("Full Profile JSON (Test 2):")
print("="*80)
print(json.dumps(profile2, ensure_ascii=False, indent=2))
