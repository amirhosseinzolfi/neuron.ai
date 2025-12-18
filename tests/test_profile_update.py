#!/usr/bin/env python3
"""
Quick test for profile extractor API with real test results
"""
import requests
import json

# Test data - simulating a real test result
TEST_USER_ID = "5816681487"
TEST_RESULT = """
## نتایج تحلیل روانشناختی: تست ارزیابی استرس درکشده

**نام کاربر:** تست کاربر
**امتیاز کسب شده:** ۰ (از ۳)
**دستهبندی سطح استرس:** استرس پایین

کاربر توانایی بالایی در مدیریت بار کاری و مرزبندیهای مؤثر دارد.
"""

EXISTING_PROFILE = {
    "user_id": TEST_USER_ID,
    "core_info": {
        "name": "Amir Hossein",
        "age": 26,
        "occupation": "AI Developer"
    },
    "professional_profile": {
        "skills": ["Python", "AI"],
        "career_summary": None,
        "job_history": []
    },
    "personal_outlook": {
        "interests": ["AI", "Books"],
        "goals": [],
        "values": []
    }
}

CONVERSATION = [
    {"role": "user", "content": "۱"},
    {"role": "user", "content": "۱"}
]

def test_profile_extractor():
    """Test the profile extractor API endpoint"""
    
    url = "http://localhost:15800/profile/extract"
    
    # Prepare form data
    form_data = {
        "user_id": TEST_USER_ID,
        "user_profile": json.dumps(EXISTING_PROFILE, ensure_ascii=False),
        "text_messages": json.dumps([TEST_RESULT], ensure_ascii=False)
    }
    
    print("🧪 Testing Profile Extractor API")
    print("=" * 60)
    print(f"📤 Sending request to: {url}")
    print(f"   User ID: {TEST_USER_ID}")
    print(f"   Profile size: {len(form_data['user_profile'])} chars")
    print(f"   Test result size: {len(TEST_RESULT)} chars")
    print()
    
    try:
        response = requests.post(url, data=form_data, timeout=90)
        
        print(f"📥 Response Status: {response.status_code}")
        print()
        
        if response.status_code == 200:
            # Parse response
            try:
                profile = response.json()
                print("✅ SUCCESS - Profile updated!")
                print("=" * 60)
                print(f"📊 Profile Summary:")
                print(f"   Name: {profile.get('core_info', {}).get('name', 'N/A')}")
                print(f"   Age: {profile.get('core_info', {}).get('age', 'N/A')}")
                print(f"   Occupation: {profile.get('core_info', {}).get('occupation', 'N/A')}")
                print(f"   Confidence: {profile.get('metadata', {}).get('confidence', 0):.2f}")
                print(f"   Last Updated: {profile.get('metadata', {}).get('last_updated', 'N/A')}")
                
                # Show psychological profile if present
                psych = profile.get('psychological_profile', {})
                if psych.get('summary'):
                    print(f"\n🧠 Psychological Summary:")
                    print(f"   {psych['summary'][:200]}...")
                
                print("\n✅ Test PASSED")
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ FAILED - Invalid JSON response")
                print(f"   Error: {e}")
                print(f"   Response preview: {response.text[:500]}")
                return False
        else:
            print(f"❌ FAILED - HTTP {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ FAILED - Cannot connect to API")
        print("   Make sure the API is running: python -m app.main")
        return False
    except requests.exceptions.Timeout:
        print("❌ FAILED - Request timeout (90s)")
        return False
    except Exception as e:
        print(f"❌ FAILED - Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_profile_extractor()
    exit(0 if success else 1)
