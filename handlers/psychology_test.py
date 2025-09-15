from telegram import Update
from typing import Any, TYPE_CHECKING
try:  # Provide broad compatibility across python-telegram-bot versions
    from telegram.ext import ContextTypes, ConversationHandler  # type: ignore
    CTX_BASE = getattr(ContextTypes, "DEFAULT_TYPE", object)  # may not exist
except Exception:  # pragma: no cover - defensive
    from telegram.ext import ConversationHandler  # type: ignore
    CTX_BASE = object

# Avoid hard import errors during test collection if db or other runtime
# components are absent; import lazily.
try:  # pragma: no cover - simple safeguard
    import db  # type: ignore
except Exception:  # Fallback shim so attribute access fails clearly at runtime
    class _DBShim:  # noqa: D401 - internal shim
        """Fallback db shim used only when real db module missing."""
        def __getattr__(self, name):  # pragma: no cover - defensive
            raise RuntimeError("Database layer not available: attempted attribute '" + name + "'")
    db = _DBShim()  # type: ignore

# Define states
WAITING_FOR_NAME, QUESTION_1, QUESTION_2, QUESTION_3, TEST_COMPLETED = range(5)

async def start_test(update: Update, context) -> int:
    user_id = update.effective_user.id
    await db.update_user_state(user_id, "WAITING_FOR_NAME")
    await update.message.reply_text("Welcome to the Psychology Test. Please enter your name:")
    return WAITING_FOR_NAME

async def process_name(update: Update, context) -> int:
    user_id = update.effective_user.id
    user_name = update.message.text
    
    # Save user's name
    await db.save_test_response(user_id, "name", user_name)
    
    # Critical fix: Update the user's state to proceed to the first question
    await db.update_user_state(user_id, "QUESTION_1")
    
    # Get the first question from your questions list
    first_question = await db.get_question(1)
    
    # Send the first question to the user
    await update.message.reply_text(f"Thanks, {user_name}! Let's begin.\n\nQuestion 1: {first_question['text']}")
    
    # Return the next state
    return QUESTION_1

async def process_question(update: Update, context) -> int:
    user_id = update.effective_user.id
    answer = update.message.text
    
    # Get current question number from user state
    current_state = await db.get_user_state(user_id)
    current_q_num = int(current_state.replace("QUESTION_", ""))
    
    # Save the answer
    await db.save_test_response(user_id, f"q{current_q_num}", answer)
    
    # Check if this was the last question
    total_questions = await db.get_total_questions()
    
    if current_q_num < total_questions:
        # Move to next question
        next_q_num = current_q_num + 1
        next_question = await db.get_question(next_q_num)
        
        # Update user state
        await db.update_user_state(user_id, f"QUESTION_{next_q_num}")
        
        # Send next question
        await update.message.reply_text(f"Question {next_q_num}: {next_question['text']}")
        return globals()[f"QUESTION_{next_q_num}"]
    else:
        # Test completed
        await db.update_user_state(user_id, "TEST_COMPLETED")
        # Call optional results processor if defined
        try:  # pragma: no cover - optional path
            from . import process_test_results  # type: ignore
            await process_test_results(update, context)  # type: ignore
        except Exception:
            pass
        return ConversationHandler.END