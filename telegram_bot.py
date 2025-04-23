import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
# Import new functions from psychology-test
from psychology_test import tele_initialize, tele_get_question, tele_process_answer, tele_summarize

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Telegram Bot Token
TOKEN = "7810952815:AAETk8FaU6rtq8_ICAJuwLGLJA8ZcMILrMM"

# Global dictionary to hold test sessions by chat id
user_tests = {}

def start(update: Update, context: CallbackContext) -> None:
    # Attractive greeting with test selection menu
    keyboard = [[ "1 - Test MBTI", "2 - Test DISC" ], [ "/help", "/login" ]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text(
        "Welcome to the Attractive Psychology Test Bot!\n\n"
        "Please choose a test by sending one of the options below:\n"
        "1 - MBTI Personality Test\n"
        "2 - DISC Personality Test\n\n"
        "Or use /help and /login for additional commands.",
        reply_markup=reply_markup
    )

def help_command(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("دستورات موجود: /start, /help, /login, /start_test, /آزمون_روانشناسی, /آزمون_شخصیتی")

def login(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("در حال ورود از طریق ترمینال. لطفاً ترمینال خود را بررسی کنید.")

def start_test(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_chat.id
    user_name = update.effective_user.first_name or "User"
    user_input = update.message.text.strip()
    test_type = None
    # Determine test type based on user input
    if user_input == "1":
        test_type = "MBTI"
    elif user_input == "2":
        test_type = "DISK"
    # Initialize a new test session with selected test type.
    state = tele_initialize(user_name, test_type) if test_type else tele_initialize(user_name)
    user_tests[user_id] = state
    q_text = tele_get_question(state)
    update.message.reply_text(f"Hello {user_name}, your {test_type if test_type else 'Psychology'} test is starting:\n\n{q_text}")

def test_message_handler(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_chat.id
    if user_id in user_tests:
        state = user_tests[user_id]
        user_input = update.message.text
        result = tele_process_answer(state, user_input)
        # Send the acknowledgment message
        update.message.reply_text(result["ack"])
        # If there is a next question, send it; otherwise, summarize the test
        if result["next"]:
            update.message.reply_text(result["next"])
        else:
            summary = tele_summarize(state)
            update.message.reply_text(f"آزمون به پایان رسید!\n\nخلاصه:\n{summary}")
            # Optionally, remove finished test session
            user_tests.pop(user_id, None)
    else:
        # If no test session is active, ignore or prompt user with instructions
        update.message.reply_text("برای شروع آزمون، لطفاً /start_test را وارد کنید.")

def message_handler(update: Update, context: CallbackContext) -> None:
    # Default message handler for non-test messages
    user_id = update.effective_chat.id
    if user_id not in user_tests:
        user_text = update.message.text
        response = f"پیام شما: {user_text}"
        update.message.reply_text(response)
    # If there is an active test session, let test_message_handler handle user responses.

def main():
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("login", login))
    # Retain the generic test start command.
    dispatcher.add_handler(CommandHandler("start_test", start_test))
    # New handler for test selection by sending "1" or "2"
    dispatcher.add_handler(MessageHandler(Filters.regex('^(1|2)$') & ~Filters.command, start_test))
    # Handler for test responses; it should be placed before the default message handler.
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, test_message_handler))
    # Fallback message handler for non-test messages.
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
