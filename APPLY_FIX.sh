#!/bin/bash
# Apply critical fix to telegram_handlers.py

FILE="/root/blue-psychology-test/telegram_handlers.py"

# Create backup
cp "$FILE" "${FILE}.backup"

# Apply fix using Python
python3 << 'EOF'
import re

with open('/root/blue-psychology-test/telegram_handlers.py', 'r') as f:
    content = f.read()

# Find and replace the profile update task function
old_pattern = r'def _profile_update_task\(bot, chat_id, summary_text, snap_state, snap_history\):\s+try:\s+ai_utils\.update_user_profile_with_ai\(\s+chat_id,\s+summary_text,\s+conversation_history=snap_history,\s+state=snap_state\s+\)\s+try:\s+bot\.send_message\(\s+chat_id=chat_id,\s+text="✅ پروفایل هوش مصنوعی شما با موفقیت بهروزرسانی شد\."\s+\)\s+except Exception as send_err:\s+logger\.error\(f"Failed to send profile update success message to \{chat_id\}: \{send_err\}"\)\s+except Exception as profile_err:\s+logger\.error\(f"AI profile update failed for \{chat_id\}: \{profile_err\}", exc_info=True\)'

new_text = '''def _profile_update_task(bot, chat_id, summary_text, snap_state, snap_history):
                    try:
                        success = ai_utils.update_user_profile_with_ai(
                            chat_id,
                            summary_text,
                            conversation_history=snap_history,
                            state=snap_state
                        )
                        if success:
                            try:
                                bot.send_message(
                                    chat_id=chat_id,
                                    text="✅ پروفایل هوش مصنوعی شما با موفقیت بهروزرسانی شد."
                                )
                            except Exception as send_err:
                                logger.error(f"Failed to send profile update success message to {chat_id}: {send_err}")
                        else:
                            logger.warning(f"Profile update returned False for user {chat_id}")
                    except Exception as profile_err:
                        logger.error(f"AI profile update failed for {chat_id}: {profile_err}", exc_info=True)'''

# Simple string replacement
content = content.replace(
    '''                def _profile_update_task(bot, chat_id, summary_text, snap_state, snap_history):
                    try:
                        ai_utils.update_user_profile_with_ai(
                            chat_id,
                            summary_text,
                            conversation_history=snap_history,
                            state=snap_state
                        )
                        try:
                            bot.send_message(
                                chat_id=chat_id,
                                text="✅ پروفایل هوش مصنوعی شما با موفقیت بهروزرسانی شد."
                            )
                        except Exception as send_err:
                            logger.error(f"Failed to send profile update success message to {chat_id}: {send_err}")
                    except Exception as profile_err:
                        logger.error(f"AI profile update failed for {chat_id}: {profile_err}", exc_info=True)''',
    new_text
)

with open('/root/blue-psychology-test/telegram_handlers.py', 'w') as f:
    f.write(content)

print("✅ Fix applied successfully")
EOF

echo "Done. Backup saved to ${FILE}.backup"
