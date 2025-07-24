"""
Telegram bot handlers for Blue Psychology Test Bot.
This module contains all the handler functions for the Telegram bot.
"""
import re
import time
import os
import sqlite3
import logging
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ParseMode, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import CallbackContext
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import psychology_test as pt
import db
import packages
from pdf_utils import generate_pdf
import telegram_ui as ui

# Console for rich logging
console = Console()
logger = logging.getLogger(__name__)

# Import chat_states and admin_only from utils.py
from utils import chat_states, admin_only, escape_markdown_v2, ADMINS

# Helper function to format and send text using HTML formatting
def send_formatted_text(update, text, reply_markup=None):
    """Format markdown text to HTML and send it properly chunked"""
    # Import format_md_for_telegram function
    def _import_format_md_for_telegram():
        from telegrambot import format_md_for_telegram
        return format_md_for_telegram
        
    format_md_for_telegram = _import_format_md_for_telegram()
    message_chunks = format_md_for_telegram(text)
    
    # Determine the reply method based on update type
    if update.callback_query:
        reply_method = update.callback_query.message.reply_text
    else:
        reply_method = update.message.reply_text
    
    # Send each chunk with HTML parsing
    sent_messages = []
    for i, chunk in enumerate(message_chunks):
        sent_message = reply_method(
            chunk,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup if i == len(message_chunks) - 1 else None
        )
        sent_messages.append(sent_message)
        # Small delay between chunks to maintain order
        if i < len(message_chunks) - 1:
            time.sleep(0.5)
    
    return sent_messages

# =============================================================================
# MAIN MENU AND NAVIGATION HANDLERS
# =============================================================================

def start(update: Update, context: CallbackContext):
    """Show main menu with four persistent options."""
    user = update.effective_user
    db.save_user(user.id, user.username, user.first_name, user.last_name)
    console.log("[green]User started the bot[/green]")

    # Import format_md_for_telegram function to properly format the welcome message
    def _import_format_md_for_telegram():
        from telegrambot import format_md_for_telegram
        return format_md_for_telegram
        
    format_md_for_telegram = _import_format_md_for_telegram()
    welcome_chunks = format_md_for_telegram(ui.WELCOME_INTRO)
    welcome_text = welcome_chunks[0] if welcome_chunks else ui.WELCOME_INTRO

    # Persistent reply keyboard with 4 buttons
    reply_keyboard = [
        [
            KeyboardButton("📋 تست‌های روانشناسی"),
            KeyboardButton("🧠 پکیج‌های هوشمند")
        ],
        [
            KeyboardButton("🧑‍💼 پروفایل من"),
            KeyboardButton("💬 جلسه هوشمند درمانی با هوش مصنوعی")
        ]
    ]
    persistent_markup = ReplyKeyboardMarkup(
        reply_keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    # Inline keyboard for the welcome message itself (optional)
    inline_kb = [
        [
            InlineKeyboardButton("📋 تست‌های روانشناسی", callback_data="psychology_tests"),
            InlineKeyboardButton("🧠 پکیج‌های هوشمند", callback_data="smart_packages")
        ],
        [
            InlineKeyboardButton("🕵️ نتایج تست‌های قبلی", callback_data="my_profile"),
            InlineKeyboardButton("💬 جلسه هوشمند درمانی با هوش مصنوعی", callback_data="smart_therapy")
        ]
    ]
    inline_markup = InlineKeyboardMarkup(inline_kb)

    # Check if this is from a command or callback
    if update.message:
        # From direct command - send new message
        image_path = "/root/blue-psychology-test/images/photo_6_2025-04-16_05-26-42.jpg"
        with open(image_path, "rb") as img:
            update.message.reply_photo(
                photo=img,
                caption=welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=inline_markup
            )
        # Ensure persistent keyboard is set (below input box)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=ui.WELCOME_KEYBOARD_HINT,
            reply_markup=persistent_markup
        )
    else:
        # From callback - try to edit message
        try:
            # If we have a callback query, use it to edit the message
            if hasattr(update, 'callback_query') and update.callback_query:
                if update.callback_query.message.photo:
                    # Can't edit photo to text, send new message
                    image_path = "/root/blue-psychology-test/images/photo_6_2025-04-16_05-26-42.jpg"
                    with open(image_path, "rb") as img:
                        context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=img,
                            caption=welcome_text,
                            parse_mode=ParseMode.HTML,
                            reply_markup=inline_markup
                        )
                else:
                    # Edit text message
                    update.callback_query.edit_message_text(
                        text=welcome_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=inline_markup
                    )
        except Exception as e:
            logger.error(f"Error in start function: {e}")
            # Fallback to sending a new message
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=inline_markup
            )

def psychology_tests(update: Update, context: CallbackContext):
    """Show available psychology tests"""
    console.log("[cyan]Showing psychology tests menu[/cyan]")
    # Record user
    user = update.effective_user
    db.save_user(user.id, user.username, user.first_name, user.last_name)
    tests = pt.all_tests["tests"]
    test_labels = {
        "Example MBTI Personality Test": "🧠 تست شخصیت MBTI",
        "Stress Assessment Test": "🧘 تست سنجش استرس",
        "DISC Personality Assessment": "📊 تست شخصیت DISC"
    }
    keyboard = [
        [InlineKeyboardButton(test_labels.get(t["test_name"], t["test_name"]), callback_data=str(i+1))]
        for i, t in enumerate(tests)
    ]
    # Add back button
    keyboard.append([InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="back_to_home")])
    
    # Import format_md_for_telegram function to properly format the caption
    def _import_format_md_for_telegram():
        from telegrambot import format_md_for_telegram
        return format_md_for_telegram
        
    format_md_for_telegram = _import_format_md_for_telegram()
    caption_chunks = format_md_for_telegram(ui.TEST_SELECTION_CAPTION)
    caption_text = caption_chunks[0] if caption_chunks else ui.TEST_SELECTION_CAPTION
    
    image_path = "/root/blue-psychology-test/images/photo_2_2025-04-16_05-26-42.jpg"
    
    # Check if this is from a callback query
    if update.callback_query:
        try:
            # Try to edit the caption if the message has a photo
            if update.callback_query.message.photo:
                update.callback_query.edit_message_caption(
                    caption=caption_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # If the current message doesn't have a photo, send a new photo message
                with open(image_path, "rb") as img:
                    context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=img,
                        caption=caption_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
        except Exception as e:
            logger.error(f"Error in psychology_tests: {e}")
            # Fallback to sending a new message
            with open(image_path, "rb") as img:
                context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=img,
                    caption=caption_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
    else:
        # From direct command - send new message
        with open(image_path, "rb") as img:
            update.message.reply_photo(
                photo=img,
                caption=caption_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

def smart_therapy_session(update: Update, context: CallbackContext):
    """Placeholder for future smart therapy session feature"""
    send_formatted_text(update, ui.SMART_THERAPY_COMING_SOON)

# Simple callbacks to link buttons to commands
def show_tests_cb(update: Update, context: CallbackContext):
    update.callback_query.answer()
    # Record user
    user = update.effective_user
    db.save_user(user.id, user.username, user.first_name, user.last_name)
    # The psychology_tests function now handles message editing internally
    return psychology_tests(update, context)

def show_profile_cb(update: Update, context: CallbackContext):
    update.callback_query.answer()
    # Record user
    user = update.effective_user
    db.save_user(user.id, user.username, user.first_name, user.last_name)
    # The my_profile function now handles message editing internally
    return my_profile(update, context)
        
def back_to_home_cb(update: Update, context: CallbackContext):
    """Handle back to home button click"""
    query = update.callback_query
    query.answer()
    
    # Get user info
    user = update.effective_user
    db.save_user(user.id, user.username, user.first_name, user.last_name)
    
    # Import format_md_for_telegram function to properly format the welcome message
    def _import_format_md_for_telegram():
        from telegrambot import format_md_for_telegram
        return format_md_for_telegram
        
    format_md_for_telegram = _import_format_md_for_telegram()
    welcome_chunks = format_md_for_telegram(ui.WELCOME_INTRO)
    welcome_text = welcome_chunks[0] if welcome_chunks else ui.WELCOME_INTRO

    # Inline keyboard for the welcome message
    inline_kb = [
        [
            InlineKeyboardButton("📋 تست‌های روانشناسی", callback_data="psychology_tests"),
            InlineKeyboardButton("🧠 پکیج‌های هوشمند", callback_data="smart_packages")
        ],
        [
            InlineKeyboardButton("🕵️ نتایج تست‌های قبلی", callback_data="my_profile"),
            InlineKeyboardButton("💬 جلسه هوشمند درمانی با هوش مصنوعی", callback_data="smart_therapy")
        ]
    ]
    inline_markup = InlineKeyboardMarkup(inline_kb)
    
    # Try to edit the current message instead of deleting and creating a new one
    try:
        # If the message has an image, we need to send a new message with the image
        if query.message.photo:
            # Delete the current message
            try:
                query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
                
            # Send a new message with the image
            image_path = "/root/blue-psychology-test/images/photo_6_2025-04-16_05-26-42.jpg"
            with open(image_path, "rb") as img:
                context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=img,
                    caption=welcome_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=inline_markup
                )
        else:
            # If no image, just edit the text and markup
            query.edit_message_text(
                text=welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=inline_markup
            )
    except Exception as e:
        logger.error(f"Error in back_to_home_cb: {e}")
        # Fallback: send a new message
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=inline_markup
        )

# =============================================================================
# SMART PACKAGES HANDLERS
# =============================================================================

def smart_packages(update: Update, context: CallbackContext):
    """Show smart AI packages explanation and package options."""
    # Import format_md_for_telegram function to properly format the intro
    def _import_format_md_for_telegram():
        from telegrambot import format_md_for_telegram
        return format_md_for_telegram
        
    format_md_for_telegram = _import_format_md_for_telegram()
    intro_chunks = format_md_for_telegram(ui.SMART_PACKAGES_INTRO)
    intro_text = intro_chunks[0] if intro_chunks else ui.SMART_PACKAGES_INTRO
    
    keyboard = [
        [InlineKeyboardButton("1️⃣ پکیج خودآگاهی", callback_data="smart_pack_selfaware")],
        [InlineKeyboardButton("2️⃣ پکیج کسب‌وکار و شغلی", callback_data="smart_pack_business")],
        [InlineKeyboardButton("3️⃣ پکیج استعدادها و آینده", callback_data="smart_pack_talents")],
        [InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="back_to_home")]
    ]
    
    # If update is from callback query, try to edit the message
    if update.callback_query:
        try:
            # Check if the message has a photo
            if update.callback_query.message.photo:
                # For photo messages, we need to delete and send a new message
                # since we can't convert a photo message to a text message
                try:
                    update.callback_query.message.delete()
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")
                
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=intro_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # For text messages, we can edit directly
                update.callback_query.edit_message_text(
                    text=intro_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            logger.error(f"Could not edit message: {e}")
            update.callback_query.message.reply_text(
                text=intro_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        # From direct command
        update.message.reply_text(
            intro_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def smart_package_selected(update: Update, context: CallbackContext):
    """Handle smart package selection - show package card"""
    console.log(f"[DEBUG] smart_package_selected called with callback_data: {update.callback_query.data}")
    return show_package_card(update, context)

def show_package_card(update: Update, context: CallbackContext):
    """Show package card with details and purchase option"""
    query = update.callback_query
    query.answer()
    
    logger.info(f"[DEBUG] show_package_card called with callback_data: {query.data}")
    
    # Extract package ID from callback data
    package_id = query.data.split("_")[-1]  # e.g., "smart_pack_selfaware" -> "selfaware"
    logger.info(f"[DEBUG] Extracted package_id: '{package_id}'")
    
    # Get package details
    package = packages.get_package_by_id(package_id)
    logger.info(f"[DEBUG] Package lookup result: {package}")
    
    if not package:
        logger.error(f"[ERROR] Package not found for ID: '{package_id}'")
        query.message.reply_text("پکیج مورد نظر یافت نشد.")
        return
    
    # Format package details for HTML
    name = package["name"]
    desc = package["description"]
    time = package["estimated_time"]
    outcome = package["outcome"]
    usage = package["usage"]
    price = package.get("price", 0)
    num_tests = len(package["tests"])
    
    info_msg = f"""<b>🧠 {name}</b>

<b>💲 قیمت:</b> {price} هزار تومان
<b>🧮 تعداد تست‌ها:</b> {num_tests} عدد
<b>⏰ زمان تخمینی:</b> {time}

<b>📝 توضیحات:</b>
{desc}

<b>💡 هدف و مزایا:</b>
{outcome}

<b>🎯 کاربرد:</b>
{usage}"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 خرید و شروع پکیج", callback_data=f"start_package_{package_id}")],
        [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="charge_wallet")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="smart_packages")]
    ]
    
    # Try to edit the current message if possible
    try:
        query.edit_message_text(
            info_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Could not edit message in show_package_card: {e}")
        query.message.reply_text(
            info_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def start_package_callback(update: Update, context: CallbackContext):
    """Handle starting a package"""
    query = update.callback_query
    cid = query.message.chat_id
    
    logger.info(f"[DEBUG] start_package_callback called with callback_data: {query.data}")
    
    # Extract package ID from callback data
    package_id = query.data.split("_")[-1]  # e.g., "start_package_selfaware" -> "selfaware"
    logger.info(f"[DEBUG] Extracted package_id: '{package_id}'")
    
    # Get package details
    package = packages.get_package_by_id(package_id)
    logger.info(f"[DEBUG] Package lookup result: {package}")
    
    if not package:
        logger.error(f"[ERROR] Package not found for ID: '{package_id}'")
        query.answer("❌ پکیج مورد نظر یافت نشد.", show_alert=True)
        return
    
    # Check balance
    price = package.get("price", 0)
    balance = db.get_balance(cid)
    
    if balance < price:
        # Show alert on insufficient funds
        return query.answer(
            text=(
            f"⚠️ موجودی کیف پول شما کافی نیست!\n\n"
            f"موجودی فعلی: {balance} هزار تومان\n"
            f"هزینه پکیج: {price} هزار تومان\n\n"
            "لطفاً ابتدا کیف پول خود را شارژ کنید."
            ),
            show_alert=True
        )
    
    # Record package purchase in database
    try:
        # Deduct price and confirm
        db.update_balance(cid, -price)
        user_package_id = db.purchase_package(cid, package_id)
        db.add_package_tests(user_package_id, package["tests"])
        
        # Show success alert instead of message
        query.answer("✅ پکیج با موفقیت خریداری شد!", show_alert=True)
        
        # Show package guide and test list
        show_package_guide(update, context, user_package_id, package)
        
    except Exception as e:
        logger.error(f"Error purchasing package: {e}")
        # Show error alert and refund the user
        query.answer("❌ خطا در خرید پکیج. لطفاً دوباره تلاش کنید.", show_alert=True)
        db.update_balance(cid, price)

def smart_package_guide(update: Update, context: CallbackContext, user_package_id: int, package: dict):
    """Show package guide and test list"""
    query = update.callback_query
    
    # Format and send the guide using our helper function
    guide_text = package["guide"]
    send_formatted_text(update, guide_text)
    
    # Get tests in this package
    package_tests = db.get_package_tests(user_package_id)
    
    # Create keyboard with test buttons
    keyboard = []
    for pt_test in package_tests:
        test_id = pt_test["test_id"]
        test_completed = pt_test["completed"] == 1
        
        # Get test details from all_tests - bounds check
        if test_id < 1 or test_id > len(pt.all_tests["tests"]):
            continue
        test_data = pt.all_tests["tests"][test_id - 1]
        test_name = test_data["test_name"]
        
        # Add checkmark for completed tests
        status_icon = "✅ " if test_completed else ""
        
        keyboard.append([
            InlineKeyboardButton(
                f"{status_icon}{test_name}", 
                callback_data=f"package_test_{user_package_id}_{test_id}"
            )
        ])
    
    # Add buttons for navigation
    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت به پکیج‌ها", callback_data="purchased_packages"),
        InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_home")
    ])
    
    # Send the test selection keyboard with formatted text
    send_formatted_text(
        update, 
        ui.PACKAGE_TEST_SELECTION,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def package_test_selected(update: Update, context: CallbackContext):
    """Handle selection of a test within a package"""
    query = update.callback_query
    
    logger.info(f"[DEBUG] package_test_selected called with callback_data: {query.data}")
    
    # Extract package_id and test_id from callback data
    parts = query.data.split("_")  # "package_test_<user_package_id>_<test_id>"
    logger.info(f"[DEBUG] Callback data parts: {parts}")
    
    user_package_id = int(parts[2])
    test_id = int(parts[3])
    logger.info(f"[DEBUG] Extracted user_package_id: {user_package_id}, test_id: {test_id}")
    
    # Get test details - test_id is 1-based, array is 0-based
    if test_id < 1 or test_id > len(pt.all_tests["tests"]):
        query.answer("❌ تست مورد نظر یافت نشد.", show_alert=True)
        return
    test_data = pt.all_tests["tests"][test_id - 1]  # Adjust for 0-based index
    
    # Check if test is already completed
    package_test = db.get_package_test_by_test_id(user_package_id, test_id)
    if package_test["completed"] == 1:
        query.answer(
            f"✅ شما قبلاً تست «{test_data['test_name']}» را انجام داده‌اید.\nمی‌توانید تست دیگری را انتخاب کنید.",
            show_alert=True
        )
        return
    
    # Acknowledge callback
    query.answer()
    
    # Format test details for HTML
    test_name = test_data["test_name"]
    time_est = test_data["estimated_time"]
    outcome = test_data["outcome"]
    usage = test_data["usage"]
    num_questions = len(test_data["questions"])
    
    info_msg = f"""<b>🎯 {test_name}</b>

<b>🧮 تعداد سوالات:</b> {num_questions} عدد
<b>⏰ زمان تخمینی:</b> {time_est}

<b>💡 هدف و مزایای تست:</b>
{outcome}

<b>🎯 کاربرد:</b>
{usage}"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 شروع تست", callback_data=f"start_package_test_{user_package_id}_{test_id}")],
        [InlineKeyboardButton("🔙 بازگشت به لیست تست‌ها", callback_data=f"view_package_{user_package_id}")],
    ]
    
    # Try to edit the current message if possible, otherwise send a new one
    try:
        query.edit_message_text(
            info_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Could not edit message: {e}")
        query.message.reply_text(
            info_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def start_package_test_callback(update: Update, context: CallbackContext):
    """Start a test from within a package"""
    query = update.callback_query
    cid = query.message.chat_id
    
    logger.info(f"[DEBUG] start_package_test_callback called with callback_data: {query.data}")
    
    # Extract user_package_id and test_id from callback data
    # Format: "start_package_test_<user_package_id>_<test_id>"
    parts = query.data.split("_")
    logger.info(f"[DEBUG] Callback data parts: {parts}")
    
    if len(parts) >= 5:
        user_package_id = int(parts[3])
        test_id = int(parts[4])
        logger.info(f"[DEBUG] Extracted user_package_id: {user_package_id}, test_id: {test_id}")
    else:
        logger.error(f"[ERROR] Invalid callback data format: {query.data}")
        query.answer("❌ خطا در پردازش درخواست", show_alert=True)
        return
    
    # Acknowledge callback
    query.answer()
    
    # Proceed to ask name (similar to regular test flow)
    chat_states[cid] = {"stage": "ask_name", "test_choice": str(test_id), "user_package_id": user_package_id}
    logger.info(f"[DEBUG] Set chat_state for user {cid}: {chat_states[cid]}")
    
    # Format and send the name prompt
    name_prompt = ui.ASK_NAME
    send_formatted_text(update, name_prompt)

def view_package_callback(update: Update, context: CallbackContext):
    """Show package guide and test list for an existing package"""
    query = update.callback_query
    query.answer()
    
    # Extract user_package_id from callback data
    user_package_id = int(query.data.split("_")[-1])
    
    # Get package details from database
    package_info = db.get_user_package(user_package_id)
    if not package_info:
        query.message.reply_text("❌ پکیج مورد نظر یافت نشد.")
        return
    
    # Get package details
    package = packages.get_package_by_id(package_info["package_id"])
    if not package:
        query.message.reply_text("❌ اطلاعات پکیج یافت نشد.")
        return
    
    # Show package guide and test list
    smart_package_guide(update, context, user_package_id, package)

def handle_package_test_completion(update: Update, context: CallbackContext,
                                   chat_id: int, user_package_id: int, test_id: int):
    """Handle completion of a test within a package"""
    # Get tests in this specific package
    package_tests = db.get_package_tests(user_package_id)
    
    for pt_test in package_tests:
        if pt_test["test_id"] == test_id and pt_test["completed"] == 0:
            # Mark this test as completed
            db.mark_package_test_completed(pt_test["id"])
            
            # Check if all tests in the package are completed
            all_tests = db.get_package_tests(user_package_id)
            all_completed = all(test["completed"] == 1 for test in all_tests)
            
            # Format messages using format_md_for_telegram
            def _import_format_md_for_telegram():
                from telegrambot import format_md_for_telegram
                return format_md_for_telegram
                
            format_md_for_telegram = _import_format_md_for_telegram()
            
            if all_completed:
                # All done → send final package summary
                pkg_info = packages.get_package_by_id(
                    db.get_user_package(user_package_id)["package_id"]
                )
                completion_msg = ui.PACKAGE_ALL_TESTS_COMPLETED.format(package_name=pkg_info['name'])
                completion_chunks = format_md_for_telegram(completion_msg)
                
                for chunk in completion_chunks:
                    context.bot.send_message(
                        chat_id=chat_id,
                        text=chunk,
                        parse_mode=ParseMode.HTML
                    )
            else:
                # Partial completion → prompt next test
                pkg_info = packages.get_package_by_id(
                    db.get_user_package(user_package_id)["package_id"]
                )
                completion_msg = ui.PACKAGE_TEST_COMPLETED
                completion_chunks = format_md_for_telegram(completion_msg)
                
                for chunk in completion_chunks:
                    context.bot.send_message(
                        chat_id=chat_id,
                        text=chunk,
                        parse_mode=ParseMode.HTML
                    )
                show_package_guide_by_id(context, chat_id, user_package_id, pkg_info)
            return

def show_package_guide_by_id(context: CallbackContext, chat_id: int, user_package_id: int, package: dict):
    """Show package guide and test list by IDs"""
    # Format the guide using format_md_for_telegram
    def _import_format_md_for_telegram():
        from telegrambot import format_md_for_telegram
        return format_md_for_telegram
        
    format_md_for_telegram = _import_format_md_for_telegram()
    guide_chunks = format_md_for_telegram(package["guide"])
    
    # Send each chunk of the guide
    for chunk in guide_chunks:
        context.bot.send_message(
            chat_id=chat_id,
            text=chunk,
            parse_mode=ParseMode.HTML
        )
        time.sleep(0.5)  # Small delay between chunks
    
    # Get tests in this package
    package_tests = db.get_package_tests(user_package_id)
    
    # Create keyboard with test buttons
    keyboard = []
    for pt_test in package_tests:
        test_id = pt_test["test_id"]
        test_completed = pt_test["completed"] == 1
        
        # Get test details from all_tests - bounds check
        if test_id < 1 or test_id > len(pt.all_tests["tests"]):
            continue
        test_data = pt.all_tests["tests"][test_id - 1]
        test_name = test_data["test_name"]
        
        # Add checkmark for completed tests
        status_icon = "✅ " if test_completed else ""
        
        keyboard.append([
            InlineKeyboardButton(
                f"{status_icon}{test_name}", 
                callback_data=f"package_test_{user_package_id}_{test_id}"
            )
        ])
    
    # Add button to return to main menu
    keyboard.append([InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="psychology_tests")])
    
    # Format and send the test selection message
    selection_chunks = format_md_for_telegram(ui.PACKAGE_TEST_SELECTION)
    selection_text = selection_chunks[0] if selection_chunks else ui.PACKAGE_TEST_SELECTION
    
    # Send the test selection keyboard
    context.bot.send_message(
        chat_id=chat_id,
        text=selection_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def purchased_packages_callback(update: Update, context: CallbackContext):
    """Show user's purchased packages"""
    query = update.callback_query
    query.answer()
    cid = query.message.chat_id
    
    # Get user's purchased packages
    user_packages = db.get_user_packages(cid)
    
    if not user_packages:
        # Try to edit the message if possible
        try:
            # Check if the message has a photo
            if query.message.photo:
                # For photo messages, we need to delete and send a new message
                try:
                    query.message.delete()
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")
                
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=ui.NO_PACKAGES_PURCHASED,
                    parse_mode=ParseMode.HTML
                )
            else:
                # For text messages, we can edit directly
                query.edit_message_text(
                    text=ui.NO_PACKAGES_PURCHASED,
                    parse_mode=ParseMode.HTML
                )
        except Exception as e:
            logger.error(f"Could not edit message in purchased_packages_callback: {e}")
            query.message.reply_text(
                text=ui.NO_PACKAGES_PURCHASED,
                parse_mode=ParseMode.HTML
            )
        return
    
    keyboard = []
    for pkg in user_packages:
        package_info = packages.get_package_by_id(pkg["package_id"])
        if package_info:
            # Check completion status
            package_tests = db.get_package_tests(pkg["id"])
            completed_tests = sum(1 for test in package_tests if test["completed"] == 1)
            total_tests = len(package_tests)
            
            status_icon = "✅" if completed_tests == total_tests else "🔄"
            progress = f"({completed_tests}/{total_tests})"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_icon} {package_info['name']} {progress}",
                    callback_data=f"view_package_{pkg['id']}"
                )
            ])
    
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="my_profile")])
    
    # Try to edit the message if possible
    try:
        # Check if the message has a photo
        if query.message.photo:
            # For photo messages, we need to delete and send a new message
            try:
                query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
            
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=ui.PURCHASED_PACKAGES_TITLE,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # For text messages, we can edit directly
            query.edit_message_text(
                text=ui.PURCHASED_PACKAGES_TITLE,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Could not edit message in purchased_packages_callback: {e}")
        query.message.reply_text(
            text=ui.PURCHASED_PACKAGES_TITLE,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# =============================================================================
# USER PROFILE AND WALLET HANDLERS
# =============================================================================

def my_profile(update: Update, context: CallbackContext):
    """Show profile intro and buttons for previous results and wallet."""
    cid = update.effective_chat.id
    user = update.effective_user
    db.save_user(user.id, user.username, user.first_name, user.last_name)
    console.log(f"[blue]User {cid} requested profile (intro)[/blue]")

    # Import format_md_for_telegram function to properly format the intro
    def _import_format_md_for_telegram():
        from telegrambot import format_md_for_telegram
        return format_md_for_telegram
        
    format_md_for_telegram = _import_format_md_for_telegram()
    intro_chunks = format_md_for_telegram(ui.PROFILE_INTRO)
    intro_text = intro_chunks[0] if intro_chunks else ui.PROFILE_INTRO
    
    keyboard = [
        [InlineKeyboardButton("📚 نتایج تست‌های قبلی", callback_data="previous_test_results")],
        [InlineKeyboardButton("🧠 پکیج‌های خریداری شده", callback_data="purchased_packages")],
        [InlineKeyboardButton("💰 کیف پول من", callback_data="wallet_info")],
        [InlineKeyboardButton("➕ شارژ کیف پول", callback_data="charge_wallet")],
        [InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="back_to_home")]
    ]
    
    # If update is from callback query, try to edit the message
    if update.callback_query:
        try:
            # Check if the message has a photo
            if update.callback_query.message.photo:
                # For photo messages, we need to delete and send a new message
                try:
                    update.callback_query.message.delete()
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")
                
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=intro_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # For text messages, we can edit directly
                update.callback_query.edit_message_text(
                    text=intro_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            logger.error(f"Could not edit message: {e}")
            update.callback_query.message.reply_text(
                intro_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        # From direct command
        update.message.reply_text(
            intro_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def previous_test_results(update: Update, context: CallbackContext):
    """Show all previous test results."""
    cid = update.effective_chat.id if update.message else update.effective_chat.id
    user = update.effective_user
    db.save_user(user.id, user.username, user.first_name, user.last_name)
    console.log(f"[blue]User {cid} requested previous test results[/blue]")
    tests = db.get_user_tests(cid)
    if not tests:
        send_formatted_text(update, ui.NO_PREVIOUS_TESTS)
        return

    keyboard = [
        [InlineKeyboardButton(f"📝 {row['test_name']}", callback_data=f"view_result_{row['id']}")]
        for row in tests
    ]
    # Add back button
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="my_profile")])
    
    # Format message text
    message_text = ui.PREVIOUS_TESTS_TITLE
    
    # If update is from callback query, try to edit the message
    if update.callback_query:
        try:
            # Check if the message has a photo
            if update.callback_query.message.photo:
                # For photo messages, we need to delete and send a new message
                try:
                    update.callback_query.message.delete()
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")
                
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # For text messages, we can edit directly
                update.callback_query.edit_message_text(
                    text=message_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except Exception as e:
            logger.error(f"Could not edit message in previous_test_results: {e}")
            update.callback_query.message.reply_text(
                text=message_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        # From direct command
        update.message.reply_text(
            text=message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def previous_test_results_cb(update: Update, context: CallbackContext):
    update.callback_query.answer()
    return previous_test_results(update, context)

def wallet(update: Update, context: CallbackContext):
    """Show wallet balance and charge option"""
    cid = update.effective_chat.id
    console.log(f"[yellow]User {cid} accessed wallet[/yellow]")
    user_balance = db.get_balance(cid)
    message_text = ui.WALLET_BALANCE.format(balance=user_balance)

    # Create inline keyboard with charge button and back button
    keyboard = [
        [InlineKeyboardButton("➕ شارژ کیف پول", callback_data='charge_wallet')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="my_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # If update is from callback query, try to edit the message
    if update.callback_query:
        try:
            # Check if the message has a photo
            if update.callback_query.message.photo:
                # For photo messages, we need to delete and send a new message
                try:
                    update.callback_query.message.delete()
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")
                
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
            else:
                # For text messages, we can edit directly
                update.callback_query.edit_message_text(
                    text=message_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Could not edit message in wallet: {e}")
            update.callback_query.message.reply_text(
                text=message_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
    else:
        # From direct command
        update.message.reply_text(
            text=message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )

def wallet_info_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    return wallet(update, context)

def charge_wallet_callback(update: Update, context: CallbackContext):
    """Handle charge wallet button click"""
    query = update.callback_query
    query.answer() # Acknowledge the button press
    cid = query.message.chat_id
    
    # Try to edit the message with payment instructions
    try:
        # Check if the message has a photo
        if query.message.photo:
            # For photo messages, we need to delete and send a new message
            try:
                query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
            
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=ui.CHARGE_WALLET_INSTRUCTIONS,
                parse_mode=ParseMode.HTML
            )
        else:
            # For text messages, we can edit directly
            query.edit_message_text(
                text=ui.CHARGE_WALLET_INSTRUCTIONS,
                parse_mode=ParseMode.HTML
            )
    except Exception as e:
        logger.error(f"Could not edit message in charge_wallet_callback: {e}")
        query.message.reply_text(
            text=ui.CHARGE_WALLET_INSTRUCTIONS,
            parse_mode=ParseMode.HTML
        )
    
    # Set state to await payment screenshot
    chat_states[cid] = {"stage": "await_payment_screenshot"}
    return

def handle_payment_screenshot(update: Update, context: CallbackContext):
    """Handle incoming payment screenshot and save file."""
    cid = update.effective_chat.id
    info = chat_states.get(cid)
    # Only process if awaiting payment screenshot
    if info and info.get("stage") == "await_payment_screenshot":
        try:
            # get highest-res photo
            photo = update.message.photo[-1]
            file = context.bot.getFile(photo.file_id)
            # ensure payments directory exists
            os.makedirs("payments", exist_ok=True)
            # construct filepath
            filepath = os.path.join("payments", f"{cid}_{int(time.time())}.jpg")
            file.download(filepath)
            # record screenshot in DB
            db.save_payment_screenshot(cid, filepath)
            # forward screenshot to admin(s)
            user = update.message.from_user
            uname = f"@{user.username}" if user.username else str(cid)
            for admin_id in ADMINS:
                with open(filepath, "rb") as img_f:
                    context.bot.send_photo(
                        chat_id=admin_id,
                        photo=img_f,
                        caption=f"📸 Payment screenshot from {uname}"
                    )
            
            # Show success message as regular message (this one should stay as message)
            send_formatted_text(update, ui.PAYMENT_RECEIVED)
            # clear state
            del chat_states[cid]
            
        except Exception as e:
            logger.error(f"Error processing payment screenshot: {e}")
            update.message.reply_text("❌ خطا در پردازش عکس پرداخت. لطفاً دوباره تلاش کنید.")
    else:
        # fallback to normal answer handler
        return handle_answer(update, context)

# =============================================================================
# INDIVIDUAL TEST HANDLERS
# =============================================================================

def test_selection(update: Update, context: CallbackContext):
    """Handle test selection from the list"""
    query = update.callback_query
    query.answer()
    # Record user
    user = query.from_user
    db.save_user(user.id, user.username, user.first_name, user.last_name)
    cid = query.message.chat_id
    choice = query.data  # "1", "2", ...
    test_data = pt.all_tests["tests"][int(choice)-1]
    # store for later
    chat_states[cid] = {
        "stage": "test_info",
        "test_choice": choice,
        "test_name": test_data["test_name"]
    }
    
    # Build HTML formatted message instead of using markdown escaping
    test_name = test_data["test_name"]
    time_est = test_data["estimated_time"]
    outcome = test_data["outcome"]
    usage = test_data["usage"]
    price = test_data.get("price", 0)
    num_questions = len(test_data["questions"])
    
    # Create HTML formatted message
    info_msg = f"""<b>🎯 {test_name}</b>

💲 <b>قیمت:</b> {price} هزار تومان
🧮 <b>تعداد سوالات:</b> {num_questions} عدد
⏰ <b>زمان تخمینی:</b> {time_est}

📝 <b>توضیحات:</b>
{outcome}

💡 <b>کاربرد:</b>
{usage}"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 شروع تست", callback_data=f"start_test_{choice}")],
        [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="charge_wallet")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="psychology_tests")],
    ]
    
    # Try to edit the current message if possible, otherwise send a new one
    try:
        # Check if the message has a photo
        if query.message.photo:
            # For photo messages, we need to delete and send a new message
            try:
                query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
            
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=info_msg,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # For text messages, we can edit directly
            query.edit_message_text(
                text=info_msg,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Could not edit message: {e}")
        query.message.reply_text(
            info_msg,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def start_test_callback(update: Update, context: CallbackContext):
    """Handle start test button click"""
    query = update.callback_query
    cid = query.message.chat_id
    # retrieve choice and test info
    choice = query.data.split("_")[-1]
    test_data = pt.all_tests["tests"][int(choice)-1]
    price = test_data.get("price", 0)
    # check balance
    balance = db.get_balance(cid)
    if balance < price:
        # show alert only on insufficient funds
        return query.answer(
            text=ui.INSUFFICIENT_BALANCE.format(balance=balance, price=price),
            show_alert=True
        )
    
    # Record test purchase in database
    try:
        # deduct price and confirm
        db.update_balance(cid, -price)
        new_bal = db.get_balance(cid)
        
        # Show success alert instead of message
        query.answer("✅ تست با موفقیت خریداری شد!", show_alert=True)
        
        # proceed to ask name
        chat_states[cid].update({"stage": "ask_name", "test_choice": choice})
        
        # Format and send name prompt
        send_formatted_text(update, ui.ASK_NAME)
        
    except Exception as e:
        logger.error(f"Error purchasing test: {e}")
        # Show error alert and refund the user
        query.answer("❌ خطا در خرید تست. لطفاً دوباره تلاش کنید.", show_alert=True)

def view_result_callback(update: Update, context: CallbackContext):
    """Handle view result button click"""
    query = update.callback_query
    query.answer()
    data = query.data
    record_id = int(data.split("_")[-1])
    console.log(f"[cyan]User requested result ID: {record_id}[/cyan]")
    
    result = db.get_test_result(record_id)
    if result:
        # Use our new formatting function for saved results too
        stored_summary = result['result_text']
        test_name = result['test_name']
        
        # Send formatted result using the enhanced function
        def _import_send_styled_test_result():
            from telegrambot import send_styled_test_result
            return send_styled_test_result
            
        send_styled_test_result = _import_send_styled_test_result()
        send_styled_test_result(update, context, test_name, stored_summary)
        
        # Send PDF if available
        pdf_path = result.get('pdf_path')
        if pdf_path and os.path.exists(pdf_path):
            # Use query.message.reply_document for callback queries
            query.message.reply_document(
                open(pdf_path, 'rb'),
                filename=f"{test_name}_result.pdf",
                caption=ui.PDF_CAPTION
            )
        
        # Add back button after showing results
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به نتایج", callback_data="previous_test_results")]]
        query.message.reply_text(
            "برای بازگشت به لیست نتایج دکمه زیر را لمس کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        console.log(f"[red]Result not found for ID: {record_id}[/red]")
        query.message.reply_text(ui.RESULT_NOT_FOUND)

def handle_answer(update: Update, context: CallbackContext):
    """Handle user text messages based on current state"""
    cid = update.effective_chat.id
    info = chat_states.get(cid)
    text = update.message.text.strip() # Get text early for admin checks

    # Check for admin-specific stages first
    if info and info.get("stage") == "admin_charge_amount":
        return handle_admin_charge_input(update, context, text, info)
    if info and info.get("stage") == "admin_reduce_amount":
        return handle_admin_reduce_input(update, context, text, info)

    if not info or info["stage"] not in ["ask_name", "ask_age", "answering"]:
        # No active conversation, let the main handler in telegrambot.py handle it
        return None

    if info["stage"] == "ask_name":
        info["name"] = text
        info["stage"] = "ask_age"
        console.log(f"[blue]User {cid} set name: {text}[/blue]")
        update.message.reply_text(ui.ASK_AGE)
        return

    if info["stage"] == "ask_age":
        # validate age is numeric
        if not text.isdigit():
            update.message.reply_text(ui.INVALID_AGE)
            return
        info["age"] = text
        console.log(f"[blue]User {cid} set age: {text}[/blue]")

        # initialize test state with name, age, chat_id and selected test choice
        state = pt.tele_initialize(info["name"], int(info["age"]), info["test_choice"], chat_id=cid)
        console.log(f"[green]Initialized test for {info['name']}, age {info['age']}, test choice {info['test_choice']}, chat_id {cid}[/green]")

        # Double-check that chat_id is actually set in the state
        if "chat_id" not in state or state["chat_id"] is None:
            state["chat_id"] = cid
            console.log(f"[yellow]Added missing chat_id {cid} to state[/yellow]")

        info["state"] = state
        info["stage"] = "answering"
        
        # send first question
        first_q = pt.tele_get_question(state)
        
        console.print(Panel(
            f"[cyan]To User {info['name']}:[/cyan]\n[purple]{first_q}[/purple]",
            title="Bot Sends (First Question)",
            border_style="magenta",
            expand=False
        ))
        
        # Import format_md_for_telegram function to properly format the message
        def _import_format_md_for_telegram():
            from telegrambot import format_md_for_telegram
            return format_md_for_telegram
            
        format_md_for_telegram = _import_format_md_for_telegram()
        message_chunks = format_md_for_telegram(first_q)
        
        for chunk in message_chunks:
            update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
        return

    # Stage is "answering"
    console.log(f"[green]User {cid} answered: {text}[/green]")
    
    console.print(Panel(
        f"[cyan]User response:[/cyan]\n[yellow]{text}[/yellow]",
        title="User Answer",
        border_style="green",
        expand=False
    ))
    
    wait = update.message.reply_text(ui.ANALYZING_ANSWER)
    
    console.log("[yellow]Analyzing user response...[/yellow]")
    
    res = pt.tele_process_answer(info["state"], text) # res is {"ack": str|None, "next": str|None}
    
    # Ensure test_data is included in the state
    if not info["state"].get("test_data") and "test_data" in globals():
        try:
            from psychology_test import test_data
            info["state"]["test_data"] = test_data
            console.log("Added test_data to state for analysis")
        except ImportError:
            console.log("Could not import test_data from psychology_test module")
    
    # --- new: detect and log history summary/trim events ---
    history_summary = info["state"].get("history_summary")
    if history_summary:
        console.log(f"[magenta]Conversation summary generated:[/magenta]\n{history_summary}")
        kept = len(info["state"]["conversation_history"])
        console.log(f"[magenta]History trimmed, kept last {kept} messages[/magenta]")
    # --- end new ---
    
    # --- existing: show full conversation history in a table ---
    table = Table(title="Full Conversation History", show_header=True, header_style="bold magenta")
    table.add_column("Role", style="cyan", no_wrap=True)
    table.add_column("Message", style="white", overflow="fold")
    for msg in info["state"]["conversation_history"]:
        table.add_row(msg.get("role", ""), msg.get("content", ""))
    console.print(table)
    # --- end existing ---
    
    wait.delete()

    ack_message = res.get("ack")
    next_question_message = res.get("next")

    # Import format_md_for_telegram function to properly format the messages
    def _import_format_md_for_telegram():
        from telegrambot import format_md_for_telegram
        return format_md_for_telegram
        
    format_md_for_telegram = _import_format_md_for_telegram()

    if ack_message:
        console.print(Panel(
            f"[cyan]To User {cid}:[/cyan]\n[purple]{ack_message}[/purple]",
            title="Bot Sends (Acknowledgment/Retry)",
            border_style="magenta",
            expand=False
        ))
        message_chunks = format_md_for_telegram(ack_message)
        for chunk in message_chunks:
            update.message.reply_text(chunk, parse_mode=ParseMode.HTML)

    if next_question_message:
        console.print(Panel(
            f"[cyan]To User {cid}:[/cyan]\n[purple]{next_question_message}[/purple]",
            title="Bot Sends (Next Question)",
            border_style="magenta",
            expand=False
        ))
        message_chunks = format_md_for_telegram(next_question_message)
        for chunk in message_chunks:
            update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
    elif info["state"].get("finished"): # No next question, and state is finished
        console.log(f"[green]Test completed for user {cid}. Generating summary...[/green]")
        
        # Ensure chat_id is set in state before summary generation
        if "chat_id" not in info["state"] or info["state"]["chat_id"] is None:
            info["state"]["chat_id"] = cid
            console.log(f"[yellow]Added missing chat_id {cid} to state before summary[/yellow]")
        
        waiting_messages = ui.PROCESSING_MESSAGES

        # Show and hide messages sequentially instead of keeping all visible
        current_message = None
        for i, msg_text in enumerate(waiting_messages):
            # Delete previous message if it exists
            if current_message:
                try:
                    current_message.delete()
                except Exception as e:
                    logger.error(f"Error deleting previous waiting message: {e}")
            
            # Send new message
            current_message = update.message.reply_text(msg_text)
            
            # Wait after showing each message (including the last one)
            time.sleep(7)  # Wait for 5 seconds after each message
        
        # Delete the final waiting message before showing results
        if current_message:
            try:
                current_message.delete()
            except Exception as e:
                logger.error(f"Error deleting final waiting message: {e}")

        # Generate summary
        console.log("[magenta]Generating final summary...[/magenta]")
        
        try:
            summary_content = pt.tele_summarize(info["state"]) 
            
            console.print(Panel(
                f"[cyan]Final analysis for {info['name']}:[/cyan]\n[purple]{summary_content[:500]}...[/purple]",
                title="Bot Sends (Test Summary)",
                border_style="magenta",
                expand=False
            ))
            
            test_name = info["test_name"] # Get test_name early

            # 1. Generate and send Image with result as caption
            try:
                img_prompt = pt.generate_image_prompt(summary_content)
                images = pt.generate_images_for_prompt(
                    img_prompt,
                    cid,
                    "/tmp",
                    model="dall-e-3",
                    num_images=1,
                    width=512,
                    height=512
                )
                if images:
                    # Format the summary for image caption (with length limit)
                    def _import_format_caption_for_telegram():
                        from telegrambot import format_caption_for_telegram
                        return format_caption_for_telegram
                        
                    format_caption_for_telegram = _import_format_caption_for_telegram()
                    caption_text = format_caption_for_telegram(test_name, summary_content)
                    
                    with open(images[0], "rb") as img_f:
                        update.message.reply_photo(
                            photo=img_f,
                            caption=caption_text,
                            parse_mode=ParseMode.HTML
                        )
                else:
                    # Fallback: send styled text if image generation fails
                    def _import_send_styled_test_result():
                        from telegrambot import send_styled_test_result
                        return send_styled_test_result
                        
                    send_styled_test_result = _import_send_styled_test_result()
                    send_styled_test_result(update, context, test_name, summary_content)
            except Exception as e:
                console.log(f"[red]Image error: {e}[/red]")
                # Fallback: send styled text if image generation fails
                def _import_send_styled_test_result():
                    from telegrambot import send_styled_test_result
                    return send_styled_test_result
                    
                send_styled_test_result = _import_send_styled_test_result()
                send_styled_test_result(update, context, test_name, summary_content)

            # 2. Generate PDF, save result to DB, then send PDF
            safe_name = test_name.replace(" ", "_")
            pdf_path = f"/tmp/{safe_name}_result.pdf"
            generate_pdf(summary_content, info["name"], info["age"], test_name, pdf_path)

            # update user metadata in users table
            user = update.effective_user
            db.save_user(user.id, user.username, user.first_name, user.last_name)
            # save test result with PDF path - save the raw summary without escaping for PDF generation
            db.save_test_result(cid, test_name, summary_content, pdf_path)
            console.log(f"[blue]Saved test result for user {cid}[/blue]")
            
            # Send PDF after image
            with open(pdf_path, "rb") as pdf_f:
                update.message.reply_document(
                    pdf_f,
                    filename=f"{test_name}_result.pdf",
                    caption=ui.PDF_CAPTION
                )

            del chat_states[cid]
        except Exception as e:
            console.log(f"[red]Error generating or sending summary: {e}[/red]")
            update.message.reply_text(ui.ERROR_GENERATING_RESULT)
            
        # Add safety check before deleting chat state
        if cid in chat_states:
            info = chat_states[cid]
            # if this was a package test completion, include both IDs
            if "user_package_id" in info:
                handle_package_test_completion(
                    update, context,
                    cid,
                    info["user_package_id"],
                    int(info["test_choice"])
                )
            del chat_states[cid]
        else:
            console.log(f"Attempted to delete non-existent chat state for user {cid}")

# =============================================================================
# ADMIN HANDLERS
# =============================================================================

@admin_only
def admin_panel(update: Update, context: CallbackContext):
    """Admin main menu"""
    keyboard = [
        [InlineKeyboardButton("📋 Users", callback_data="admin_users")]
    ]
    update.message.reply_text(ui.ADMIN_PANEL_TITLE, reply_markup=InlineKeyboardMarkup(keyboard))

@admin_only
def admin_users_list(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    users = db.get_all_users()
    if not users:
        query.message.reply_text(ui.ADMIN_NO_USERS)
        return
    keyboard = []
    for u in users:
        uid = u['chat_id']
        try:
            chat = context.bot.get_chat(uid)
            uname = f"@{chat.username}" if chat.username else str(uid)
        except:
            uname = str(uid)
        keyboard.append([InlineKeyboardButton(uname, callback_data=f"admin_user_{uid}")])
    query.message.reply_text(ui.ADMIN_USERS_LIST_TITLE, reply_markup=InlineKeyboardMarkup(keyboard))

@admin_only
def admin_user_options(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    chat_id = query.data.split("_")[-1]
    keyboard = [
        [
            InlineKeyboardButton("💬 Messages", callback_data=f"admin_user_{chat_id}_messages"),
            InlineKeyboardButton("➕ Charge Wallet", callback_data=f"admin_user_{chat_id}_charge"),
            InlineKeyboardButton("➖ Reduce Wallet", callback_data=f"admin_user_{chat_id}_reduce")
        ]
    ]
    query.message.reply_text(
        ui.ADMIN_USER_ACTIONS_TITLE.format(user_id=chat_id), 
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@admin_only
def admin_charge_prompt(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    admin_id = query.message.chat_id
    parts = query.data.split("_")  # ['admin','user','<chat_id>','charge']
    target = parts[2]
    chat_states[admin_id] = {"stage":"admin_charge_amount","target":int(target)}
    query.message.reply_text(ui.ADMIN_CHARGE_PROMPT.format(user_id=target))

@admin_only
def admin_reduce_prompt(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    admin_id = query.message.chat_id
    parts = query.data.split("_")  # ['admin','user','<chat_id>','reduce']
    target = parts[2]
    chat_states[admin_id] = {"stage": "admin_reduce_amount", "target": int(target)}
    query.message.reply_text(ui.ADMIN_REDUCE_PROMPT.format(user_id=target))

@admin_only
def handle_admin_charge_input(update: Update, context: CallbackContext, amount_text: str, admin_info: dict):
    admin_id = update.effective_chat.id
    target_user_id = admin_info.get("target")

    if not target_user_id:
        update.message.reply_text("❌ خطای داخلی: شناسه کاربر هدف یافت نشد.")
        del chat_states[admin_id]
        return

    try:
        amount = int(amount_text)
        if amount <= 0:
            update.message.reply_text(ui.ADMIN_AMOUNT_MUST_BE_POSITIVE)
            return # Keep state to allow re-entry

        db.update_balance(target_user_id, amount)
        new_balance = db.get_balance(target_user_id)
        
        update.message.reply_text(
            ui.ADMIN_CHARGE_SUCCESS.format(
                user_id=target_user_id,
                amount=amount,
                balance=new_balance
            )
        )
        
        # Notify the user with alert popup instead of message
        try:
            # Send a simple notification message first
            context.bot.send_message(
                chat_id=target_user_id,
                text=f"🎉 کیف پول شما به مبلغ {amount} هزار تومان شارژ شد.\nموجودی جدید: {new_balance} هزار تومان"
            )
        except Exception as e:
            console.log(f"Failed to notify user {target_user_id} about charge: {e}")
            update.message.reply_text(f"⚠️ اخطار: موفق به اطلاع‌رسانی به کاربر {target_user_id} نشدیم.")

        del chat_states[admin_id] # Clear admin state

    except ValueError:
        update.message.reply_text(ui.ADMIN_INVALID_AMOUNT)
        return # Keep state to allow re-entry
    except sqlite3.Error as e:
        console.log(f"Database error during admin charge: {e}")
        update.message.reply_text("❌ خطای پایگاه داده هنگام شارژ کیف پول رخ داد.")
        if admin_id in chat_states:
            del chat_states[admin_id]
    except Exception as e:
        console.log(f"Unexpected error during admin charge: {e}")
        update.message.reply_text("❌ یک خطای پیش‌بینی نشده رخ داد.")
        if admin_id in chat_states:
            del chat_states[admin_id]

@admin_only
def handle_admin_reduce_input(update: Update, context: CallbackContext, amount_text: str, admin_info: dict):
    admin_id = update.effective_chat.id
    target_user_id = admin_info.get("target")

    if not target_user_id:
        update.message.reply_text("❌ خطای داخلی: شناسه کاربر هدف یافت نشد.")
        del chat_states[admin_id]
        return

    try:
        amount = int(amount_text)
        if amount <= 0:
            update.message.reply_text(ui.ADMIN_AMOUNT_MUST_BE_POSITIVE)
            return # Keep state to allow re-entry

        current_balance = db.get_balance(target_user_id)
        if amount > current_balance:
            update.message.reply_text(
                ui.ADMIN_AMOUNT_EXCEEDS_BALANCE.format(
                    amount=amount,
                    balance=current_balance
                )
            )
            return # Keep state to allow re-entry

        db.update_balance(target_user_id, -amount) # Reduce balance
        new_balance = db.get_balance(target_user_id)
        
        update.message.reply_text(
            ui.ADMIN_REDUCE_SUCCESS.format(
                user_id=target_user_id,
                amount=amount,
                balance=new_balance
            )
        )
        
        # Notify the user with simple message instead of alert
        try:
            context.bot.send_message(
                chat_id=target_user_id,
                text=f"ℹ️ مبلغ {amount} هزار تومان از کیف پول شما کسر شد.\nموجودی جدید: {new_balance} هزار تومان"
            )
        except Exception as e:
            console.log(f"Failed to notify user {target_user_id} about balance reduction: {e}")
            update.message.reply_text(f"⚠️ اخطار: موفق به اطلاع‌رسانی به کاربر {target_user_id} نشدیم.")
            
        del chat_states[admin_id] # Clear admin state

    except ValueError:
        update.message.reply_text(ui.ADMIN_INVALID_AMOUNT)
        return # Keep state to allow re-entry
    except sqlite3.Error as e:
        console.log(f"Database error during admin balance reduction: {e}")
        update.message.reply_text("❌ خطای پایگاه داده هنگام کاهش موجودی رخ داد.")
        if admin_id in chat_states:
            del chat_states[admin_id]
    except Exception as e:
        console.log(f"Unexpected error during admin balance reduction: {e}")
        update.message.reply_text("❌ یک خطای پیش‌بینی نشده رخ داد.")
        if admin_id in chat_states:
            del chat_states[admin_id]