#!/usr/bin/env python3
"""
Apply concurrency fix to telegram bot
This script makes minimal changes to enable concurrent user processing
"""

import re

# Read telegram_handlers.py
with open('/root/blue-psychology-test/telegram_handlers.py', 'r') as f:
    handlers_content = f.read()

# Find the section where test finishes and replace with non-blocking version
old_pattern = r'elif info\["state"\]\.get\("finished"\):\s+console\.log\(f"\[green\]Test completed for user \{cid\}\. Generating summary\.\.\.\[/green\]"\)\s+if "chat_id" not in info\["state"\] or info\["state"\]\["chat_id"\] is None:\s+info\["state"\]\["chat_id"\] = cid\s+result_data = \{"summary": None,'

new_code = '''elif info["state"].get("finished"):
        console.log(f"[green]Test completed for user {cid}. Generating summary...[/green]")
        
        if "chat_id" not in info["state"] or info["state"]["chat_id"] is None:
            info["state"]["chat_id"] = cid

        # Send immediate acknowledgment
        update.message.reply_text(
            "✅ تست شما تکمیل شد!\\n\\n"
            "🔄 در حال آمادهسازی نتایج...\\n"
            "نتایج طی چند لحظه برای شما ارسال خواهد شد."
        )
        
        # Generate results in background (non-blocking)
        executor.submit(generate_and_send_results_background, context.bot, cid, dict(info))
        
        # Handle package completion if needed
        if "user_package_id" in info:
            handle_package_test_completion(update, context, cid, info["user_package_id"], int(info["test_choice"]), info)
        
        # Clean up immediately - user can start new test
        if cid in chat_states:
            del chat_states[cid]
        
        # Bot continues immediately!
        return

        # OLD BLOCKING CODE BELOW - KEPT FOR REFERENCE
        result_data = {"summary": None,'''

# Apply the replacement
if 'elif info["state"].get("finished"):' in handlers_content and 'result_data = {"summary": None,' in handlers_content:
    # Find and replace the blocking section
    handlers_content = re.sub(
        r'(elif info\["state"\]\.get\("finished"\):.*?)(result_data = \{"summary": None,)',
        new_code,
        handlers_content,
        count=1,
        flags=re.DOTALL
    )
    
    print("✅ Applied non-blocking result generation")
else:
    print("⚠️ Could not find the pattern to replace")

# Write back
with open('/root/blue-psychology-test/telegram_handlers.py', 'w') as f:
    f.write(handlers_content)

print("✅ Concurrency fix applied successfully!")
print("\nNext steps:")
print("1. Restart the bot: pkill -f telegrambot.py && python telegrambot.py")
print("2. Test with multiple users simultaneously")
