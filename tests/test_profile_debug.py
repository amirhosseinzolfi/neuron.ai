#!/usr/bin/env python3
"""
Quick test to demonstrate enhanced debug logging for profile extraction.
This will show all inputs and outputs in detail.
"""

import json
from ai_utils import update_user_profile_with_ai
import db

# Test user ID
TEST_CHAT_ID = 888999

# Ensure user exists
existing = db.get_user(TEST_CHAT_ID)
if not existing:
    db.add_user(
        chat_id=TEST_CHAT_ID,
        name=f"DebugTestUser",
        progress=0
    )

# Create a simple existing profile
existing_profile = {
    "core_info": {
        "name": "Test User",
        "age": 25,
        "occupation": None
    },
    "personal_outlook": {
        "interests": ["Technology"],
        "goals": [],
        "values": []
    },
    "metadata": {
        "confidence": 0.5,
        "extracted_from": ["initial"]
    }
}

db.save_user_profile(TEST_CHAT_ID, json.dumps(existing_profile, ensure_ascii=False))

# Test data - simulating a real psychology test
test_result = """
=== نتایج تست شخصیت شناسی ===

نام: کاربر تست
سن: 25 سال
شغل: برنامه نویس

نتایج تست Big Five:

1. انعطاف پذیری (Openness): 78%
   - فردی خلاق و کنجکاو
   - علاقمند به یادگیری مفاهیم جدید
   - دارای تفکر انتزاعی قوی

2. وظیفه شناسی (Conscientiousness): 85%
   - بسیار منظم و دقیق
   - متعهد به تکمیل پروژه ها
   - برنامه ریزی دقیق

3. برون گرایی (Extraversion): 45%
   - تمایل به گروه های کوچک
   - نیاز به زمان تنهایی
   - رفتار متعادل در جمع

4. همراهی (Agreeableness): 72%
   - همکاری و همدلی خوب
   - ارتباطات مثبت
   - حل تعارض دیپلماتیک

5. روان رنجوری (Neuroticism): 35%
   - ثبات عاطفی مناسب
   - مدیریت استرس خوب
   - اضطراب کم

نقاط قوت:
✓ مهارت های تحلیلی قوی
✓ تفکر خلاق
✓ تمرکز بالا
✓ قابل اعتماد

زمینه های پیشرفت:
• بهبود مهارت های ارتباطی
• کار تیمی بیشتر
• تعادل کار-زندگی
"""

conversation_history = [
    {"role": "assistant", "content": "سلام! به تست شخصیت شناسی خوش آمدید."},
    {"role": "user", "content": "سلام، من برنامه نویس هستم و می خواهم شخصیتم را بهتر بشناسم."},
    {"role": "assistant", "content": "چه خوب! بگویید معمولا وقت آزاد خود را چگونه می گذرانید؟"},
    {"role": "user", "content": "من عاشق یادگیری تکنولوژی های جدید هستم. کتاب می خوانم و پروژه های شخصی دارم."},
    {"role": "assistant", "content": "ترجیح می دهید به تنهایی کار کنید یا در تیم؟"},
    {"role": "user", "content": "بیشتر به تنهایی راحتم ولی می تونم تو تیم هم کار کنم."},
]

state = {
    "history_summary": "کاربر یک برنامه نویس است که علاقمند به یادگیری و پروژه های شخصی است. ترجیح می دهد به تنهایی کار کند ولی می تواند در تیم نیز همکاری کند.",
    "user_info": "نام: کاربر تست، سن: 25، شغل: برنامه نویس",
    "conversation_history": conversation_history
}

print("\n" + "="*80)
print("🔍 RUNNING PROFILE EXTRACTION WITH ENHANCED DEBUG LOGGING")
print("="*80 + "\n")

# Run the update with full logging
success = update_user_profile_with_ai(
    chat_id=TEST_CHAT_ID,
    test_result_text=test_result,
    conversation_history=conversation_history,
    state=state
)

print("\n" + "="*80)
print(f"✅ Test completed - Success: {success}")
print("="*80 + "\n")

# Show final profile
final_profile = db.get_user_profile(TEST_CHAT_ID)
if final_profile:
    profile_data = json.loads(final_profile)
    print("\n📋 FINAL PROFILE IN DATABASE:")
    print(json.dumps(profile_data, ensure_ascii=False, indent=2))
