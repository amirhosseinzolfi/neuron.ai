import re
from functools import wraps
from rich.logging import RichHandler

# per-chat state store
chat_states: dict[int, dict] = {}

# your admin IDs
ADMINS = {5816681487}

def admin_only(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        uid = update.effective_user.id
        if uid not in ADMINS:
            update.effective_message.reply_text("🚫 You are not authorized to use this command.")
            return
        return func(update, context, *args, **kwargs)
    return wrapped

def escape_markdown_v2(text: str) -> str:
    """Escapes Telegram MarkdownV2 special chars."""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
