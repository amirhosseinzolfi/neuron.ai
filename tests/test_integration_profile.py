#!/usr/bin/env python3
"""
Integration test for profile extraction via FastAPI router.
Tests the complete flow: ai_utils -> FastAPI router -> simplified agent
"""

import requests
import json
import time

API_URL = "http://localhost:15800/profile/extract"

print("="*80)
print("Integration Test: Profile Extraction via FastAPI")
print("="*80)

# Test 1: New profile from scratch
print("\n" + "="*80)
print("TEST 1: Create New Profile (No Existing)")
print("="*80)

test1_data = {
    "user_id": f"test_{int(time.time())}",
    "user_profile": "",  # Empty - no existing profile
    "text_messages": json.dumps(["""
Test Results for امیر (22 years old)

Psychology Assessment Results:
- Stress Level: Low (score: 0/3)
- Personality: Analytical, organized
- Strengths: Time management, flexibility, problem-solving
- Development Areas: Communication, teamwork

Profile Info:
- Name: امیر
- Age: 22
- Interests: Programming, Technology
- Goals: Learn AI/ML, improve work-life balance
    """])
}

print("\n📤 Sending request...")
print(f"  User ID: {test1_data['user_id']}")
print(f"  Has existing profile: No")
print(f"  Message length: {len(test1_data['text_messages'])} chars")

try:
    response1 = requests.post(API_URL, data=test1_data, timeout=60)
    
    if response1.status_code == 200:
        # API returns JSON string, need to parse it
        response_data = response1.json()
        
        # Check if response_data is a string (nested JSON)
        if isinstance(response_data, str):
            profile1 = json.loads(response_data)
        else:
            profile1 = response_data
            
        print("\n✅ SUCCESS - Profile Created")
        print(f"\n📊 Profile Details:")
        print(f"  Name: {profile1.get('core_info', {}).get('name')}")
        print(f"  Age: {profile1.get('core_info', {}).get('age')}")
        print(f"  Interests: {profile1.get('personal_outlook', {}).get('interests', [])}")
        print(f"  Strengths: {profile1.get('psychological_profile', {}).get('strengths', [])}")
        print(f"  Development: {profile1.get('psychological_profile', {}).get('areas_for_development', [])}")
        print(f"  Confidence: {profile1.get('metadata', {}).get('confidence')}")
        
        # Show full profile for debugging
        print(f"\n📋 Full Profile JSON:")
        print(json.dumps(profile1, indent=2, ensure_ascii=False)[:1000] + "...")
    else:
        print(f"\n❌ FAILED - Status: {response1.status_code}")
        print(f"Response: {response1.text[:500]}")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Update existing profile
print("\n" + "="*80)
print("TEST 2: Update Existing Profile (Merge New Info)")
print("="*80)

existing_profile = {
    "user_id": "test_merge",
    "core_info": {
        "name": "امیر",
        "age": 22,
        "occupation": None
    },
    "professional_profile": {
        "skills": ["Python"],
        "job_history": []
    },
    "personal_outlook": {
        "interests": ["Programming"],
        "goals": ["Learn AI"],
        "values": []
    },
    "psychological_profile": {
        "summary": None,
        "strengths": ["Time management"],
        "areas_for_development": []
    },
    "metadata": {
        "confidence": 0.6
    }
}

test2_data = {
    "user_id": "test_merge",
    "user_profile": json.dumps(existing_profile, ensure_ascii=False),
    "text_messages": json.dumps(["""
New Information Update:

Occupation: Software Engineer
New Skills: JavaScript, React, Node.js
New Interest: Reading technical books
New Goal: Build startup
New Values: Innovation, continuous learning
New Strength: Creative problem-solving
Development Area: Public speaking, networking

Recent Test: High stress level detected - needs better work-life balance
    """])
}

print("\n📤 Sending request...")
print(f"  User ID: {test2_data['user_id']}")
print(f"  Has existing profile: Yes")
print(f"  Existing skills: {existing_profile['professional_profile']['skills']}")
print(f"  Existing strengths: {existing_profile['psychological_profile']['strengths']}")

try:
    response2 = requests.post(API_URL, data=test2_data, timeout=60)
    
    if response2.status_code == 200:
        # API returns JSON string, need to parse it
        response_data = response2.json()
        
        # Check if response_data is a string (nested JSON)
        if isinstance(response_data, str):
            profile2 = json.loads(response_data)
        else:
            profile2 = response_data
            
        print("\n✅ SUCCESS - Profile Updated")
        
        # Check what was preserved
        name_preserved = profile2.get('core_info', {}).get('name') == "امیر"
        age_preserved = profile2.get('core_info', {}).get('age') == 22
        
        # Check what was added
        occupation_added = profile2.get('core_info', {}).get('occupation') is not None
        skills = profile2.get('professional_profile', {}).get('skills', [])
        python_preserved = "Python" in skills
        new_skills_added = len(skills) > 1
        
        strengths = profile2.get('psychological_profile', {}).get('strengths', [])
        time_mgmt_preserved = "Time management" in strengths or "time management" in str(strengths).lower()
        new_strengths_added = len(strengths) > 1
        
        print(f"\n📊 Merge Results:")
        print(f"  Name preserved: {'✅' if name_preserved else '❌'} ({profile2.get('core_info', {}).get('name')})")
        print(f"  Age preserved: {'✅' if age_preserved else '❌'} ({profile2.get('core_info', {}).get('age')})")
        print(f"  Occupation added: {'✅' if occupation_added else '❌'} ({profile2.get('core_info', {}).get('occupation')})")
        print(f"  Python skill preserved: {'✅' if python_preserved else '❌'}")
        print(f"  New skills added: {'✅' if new_skills_added else '❌'}")
        print(f"  Skills: {skills}")
        print(f"  Time mgmt preserved: {'✅' if time_mgmt_preserved else '❌'}")
        print(f"  New strengths added: {'✅' if new_strengths_added else '❌'}")
        print(f"  Strengths: {strengths}")
        print(f"  Development areas: {profile2.get('psychological_profile', {}).get('areas_for_development', [])}")
        print(f"  Confidence: {profile2.get('metadata', {}).get('confidence')}")
        
        # Overall verification
        all_preserved = name_preserved and age_preserved
        all_added = occupation_added and new_skills_added
        merge_successful = all_preserved and all_added
        
        if merge_successful:
            print("\n🎉 MERGE VERIFICATION: ✅ PASSED")
            print("   - Existing data preserved correctly")
            print("   - New data added successfully")
        else:
            print("\n⚠️ MERGE VERIFICATION: ❌ ISSUES DETECTED")
            if not all_preserved:
                print("   - Some existing data was lost")
            if not all_added:
                print("   - Some new data was not added")
                
        # Show full profile for debugging
        print(f"\n📋 Full Profile JSON:")
        print(json.dumps(profile2, indent=2, ensure_ascii=False)[:1000] + "...")
    else:
        print(f"\n❌ FAILED - Status: {response2.status_code}")
        print(f"Response: {response2.text[:500]}")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("Integration Test Complete")
print("="*80)
print("\nNote: If tests fail, ensure:")
print("  1. Profile extraction API is running: python run_profile_api.sh")
print("  2. Port 15800 is accessible")
print("  3. Google API key is configured")
