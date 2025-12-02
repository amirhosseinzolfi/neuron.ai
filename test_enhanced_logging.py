#!/usr/bin/env python3
"""
Quick test to verify enhanced logging for profile extraction.
This will show all the detailed logs we added.
"""

import json
from ai_utils import update_user_profile_with_ai
import db

# Test chat ID
chat_id = 5816681487

# Create/update test user
user = db.get_user(chat_id)
if not user:
    db.add_user(chat_id=chat_id, name="TestUser", progress=0)

# Set up initial profile
initial_profile = {
    "core_info": {
        "name": "علی",
        "age": 28,
        "occupation": "برنامه‌نویس"
    },
    "personal_outlook": {
        "interests": ["فناوری", "ورزش"],
        "goals": ["یادگیری هوش مصنوعی"],
        "values": ["نوآوری"]
    },
    "metadata": {
        "confidence": 0.7,
        "extracted_from": ["initial"]
    }
}

db.save_user_profile(chat_id, json.dumps(initial_profile, ensure_ascii=False))
print("✅ Setup complete - initial profile saved\n")

# Test data
test_result = """
نتایج تست روان‌شناختی شخصیت Big Five

نام: علی رضایی
سن: 29 سال
شغل: توسعه‌دهنده نرم‌افزار

نتایج:
- گشودگی به تجربه: 85%
- وظیفه‌شناسی: 78%
- برون‌گرایی: 42%
- توافق‌پذیری: 65%
- روان‌رنجورخویی: 38%

نقاط قوت:
- تحلیل منطقی
- خلاقیت در حل مسئله
- تمرکز بالا

زمینه‌های رشد:
- مدیریت استرس
- کار تیمی
- سخنرانی عمومی
"""

conversation_history = [
    {"role": "assistant", "content": "سلام! به تست شخصیت‌شناسی خوش آمدید."},
    {"role": "user", "content": "سلام، من علی هستم و 29 سالمه."},
    {"role": "assistant", "content": "شغل شما چیست؟"},
    {"role": "user", "content": "من برنامه‌نویس هستم و با پایتون کار می‌کنم."},
    {"role": "assistant", "content": "علاقه‌مندی‌های شما چیست؟"},
    {"role": "user", "content": "به فناوری، هوش مصنوعی و ورزش علاقه دارم."},
]

state = {
    "history_summary": "کاربر در تست Big Five شرکت کرد و نمرات بالایی در گشودگی و وظیفه‌شناسی کسب کرد.",
    "user_info": "نام: علی رضایی، سن: 29، شغل: توسعه‌دهنده نرم‌افزار"
}

print("🚀 Starting profile update with enhanced logging...\n")
print("="*80)

# Run the update - this will show all the detailed logs
success = update_user_profile_with_ai(
    chat_id=chat_id,
    test_result_text=test_result,
    conversation_history=conversation_history,
    state=state
)

print("="*80)
print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")

# Verify the result
profile_json = db.get_user_profile(chat_id)
if profile_json:
    profile = json.loads(profile_json)
    print(f"\n📋 Final Profile Summary:")
    print(f"   Name: {profile.get('core_info', {}).get('name', 'N/A')}")
    print(f"   Age: {profile.get('core_info', {}).get('age', 'N/A')}")
    print(f"   Occupation: {profile.get('core_info', {}).get('occupation', 'N/A')}")
    print(f"   Confidence: {profile.get('metadata', {}).get('confidence', 0.0)}")
