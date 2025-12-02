#!/usr/bin/env python3
"""Full integration test with realistic psychology test data"""
import sys
sys.path.insert(0, '/root/blue-psychology-test')

from app.services.profile_extract_agent_json import process_input
import json

# Realistic test data from actual PSS-1 test
FULL_TEST_RESULT = """
## نتایج تحلیل روانشناختی: ارزیابی استرس درکشده

**نام آزموندهنده:** کاربر ۱

### نحوه امتیازدهی و نتایج خام

| # | سوال (بعد روانشناختی) | پاسخ دقیق کاربر | انتخاب | امتیاز اختصاص یافته |
|---|---|---|---|---|
| 1 | در ماه گذشته، هر چند وقت یک بار احساس کردهاید که مسئولیتهایتان بیش از حد است؟ | ۱ | هرگز یا بهندرت | ۰ |

**امتیاز محاسبه شده:** ۰ (از ۳)

### ارزیابی سطح استرس

**امتیاز کلی:** ۰
**دستهبندی سطح استرس:** استرس پایین

**توضیحات:** بر اساس پاسخ ارائه شده، سطح استرس درکشده بسیار پایین است.

### بینشها و تفسیر روانشناختی

**تحلیل بُعد بار وظایف و کنترل:**
انتخاب گزینه «هرگز یا بهندرت» نشان میدهد که شما دارای مهارتهای مقابلهای بسیار مؤثر هستید.

**نشانههای مثبت:**
1. **کنترل درکشده بالا:** منابع کافی برای برآورده کردن نیازها
2. **مرزبندی مؤثر:** مرزهای سالم بین زندگی شخصی و کاری
"""

EXISTING_PROFILE = {
    "user_id": "5816681487",
    "core_info": {
        "name": "Amir Hossein Zolfi Khorram",
        "age": 26,
        "occupation": "AI Developer, Programmer (Python)"
    },
    "professional_profile": {
        "career_summary": "AI Developer with Python expertise",
        "skills": ["Python", "AI Development", "Programming"],
        "job_history": []
    },
    "personal_outlook": {
        "interests": ["AI", "Books", "Coffee"],
        "goals": ["Advancing AI expertise"],
        "values": ["Innovation", "Focus", "Balance"]
    },
    "psychological_profile": {
        "summary": None,
        "personality_traits": {},
        "cognitive_biases": [],
        "strengths": [],
        "areas_for_development": []
    }
}

print("🧪 Full Integration Test - Psychology Profile Update")
print("=" * 70)
print(f"📊 Test Data:")
print(f"   User: {EXISTING_PROFILE['core_info']['name']}")
print(f"   Age: {EXISTING_PROFILE['core_info']['age']}")
print(f"   Test Result Length: {len(FULL_TEST_RESULT)} chars")
print()

try:
    result = process_input(
        user_id="5816681487",
        message=FULL_TEST_RESULT,
        media=[],
        existing_profile=EXISTING_PROFILE,
        persist=False
    )
    
    profile = result['profile']
    psych = profile.get('psychological_profile', {})
    
    print("✅ SUCCESS - Profile Updated!")
    print("=" * 70)
    print(f"\n📋 Core Info:")
    print(f"   Name: {profile['core_info']['name']}")
    print(f"   Age: {profile['core_info']['age']}")
    print(f"   Occupation: {profile['core_info']['occupation']}")
    
    print(f"\n💼 Professional:")
    print(f"   Skills: {', '.join(profile['professional_profile']['skills'][:5])}")
    
    print(f"\n🎯 Personal Outlook:")
    print(f"   Interests: {', '.join(profile['personal_outlook']['interests'][:5])}")
    print(f"   Values: {', '.join(profile['personal_outlook']['values'][:5])}")
    
    print(f"\n🧠 Psychological Profile:")
    if psych.get('summary'):
        print(f"   Summary: {psych['summary'][:150]}...")
    print(f"   Strengths: {len(psych.get('strengths', []))} identified")
    print(f"   Development Areas: {len(psych.get('areas_for_development', []))} identified")
    
    print(f"\n📊 Metadata:")
    print(f"   Confidence: {result['confidence']:.2f}")
    print(f"   Action: {result['action']}")
    print(f"   Operations: {result['operations']}")
    
    print("\n" + "=" * 70)
    print("✅ FULL INTEGRATION TEST PASSED")
    print("=" * 70)
    
except Exception as e:
    print(f"\n❌ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
