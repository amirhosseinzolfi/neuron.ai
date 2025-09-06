"""
Optimized Telegram bot handlers for Blue Psychology Test Bot.
This module contains all the handler functions for the Telegram bot.
"""
import re
import time
import os
import sqlite3
import logging
import threading
from pathlib import Path
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
import package_ai
from pdf_utils import generate_pdf
import telegram_ui as ui

# Console for rich logging
console = Console()
logger = logging.getLogger(__name__)

# Import chat_states and admin_only from utils.py
from utils import chat_states, admin_only, escape_markdown_v2, ADMINS

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def sanitize_for_log(text: str) -> str:
    """Sanitize user input before logging to prevent log injection."""
    if not isinstance(text, str):
        text = str(text)
    # Remove newlines and control characters
    return re.sub(r'[\r\n\t\x00-\x1f\x7f-\x9f]', ' ', text)

def save_user_info(user):
    """Extract and save user information safely."""
    try:
        db.save_user(user.id, user.username, user.first_name, user.last_name)
    except AttributeError as e:
        logger.error(f"Error accessing user attributes: {e}")

def get_safe_file_path(base_dir: str, filename: str) -> str:
    """Create a safe file path preventing path traversal attacks."""
    base_path = Path(base_dir).resolve()
    safe_filename = re.sub(r'[^\w\-_\.]', '_', filename)
    file_path = base_path / safe_filename
    
    # Ensure the file path is within the base directory
    if not str(file_path.resolve()).startswith(str(base_path)):
        raise ValueError("Invalid file path")
    
    return str(file_path)

def import_formatter():
    """Dynamically import formatter to avoid circular dependencies."""
    from telegrambot import format_md_for_telegram
    return format_md_for_telegram

def send_formatted_text(update: Update, text: str, reply_markup=None):
    """Formats markdown text to HTML and sends it, handling message editing."""
    format_md_for_telegram = import_formatter()
    message_chunks = format_md_for_telegram(text)
    
    is_callback = update.callback_query is not None
    reply_method = (update.callback_query.message.reply_text if is_callback 
                   else update.message.reply_text)
    edit_method = update.callback_query.edit_message_text if is_callback else None

    sent_messages = []
    for i, chunk in enumerate(message_chunks):
        current_markup = reply_markup if i == len(message_chunks) - 1 else None
        
        try:
            if i == 0 and is_callback and edit_method:
                sent_message = edit_method(
                    text=chunk,
                    parse_mode=ParseMode.HTML,
                    reply_markup=current_markup
                )
            else:
                sent_message = reply_method(
                    text=chunk,
                    parse_mode=ParseMode.HTML,
                    reply_markup=current_markup
                )
            sent_messages.append(sent_message)
        except Exception as e:
            logger.error(f"Error sending/editing formatted text chunk: {e}")
            if is_callback:
                sent_message = update.callback_query.message.reply_text(
                    text=chunk,
                    parse_mode=ParseMode.HTML,
                    reply_markup=current_markup
                )
                sent_messages.append(sent_message)

        if len(message_chunks) > 1 and i < len(message_chunks) - 1:
            time.sleep(0.6)
            
    return sent_messages

# =============================================================================
# MAIN MENU AND NAVIGATION HANDLERS
# =============================================================================

def start(update: Update, context: CallbackContext):
    """Show main menu with four persistent options."""
    user = update.effective_user
    save_user_info(user)
    console.log("[green]User started the bot[/green]")

    format_md_for_telegram = import_formatter()
    welcome_chunks = format_md_for_telegram(ui.WELCOME_INTRO)
    welcome_text = welcome_chunks[0] if welcome_chunks else ui.WELCOME_INTRO

    # Persistent reply keyboard with 4 buttons
    reply_keyboard = [
        [
            KeyboardButton("📋 تستهای روانشناسی"),
            KeyboardButton("🧠 پکیجهای هوشمند")
        ],
        [
            KeyboardButton("🧑💼 پروفایل من"),
            KeyboardButton("💬 جلسه هوشمند درمانی با هوش مصنوعی")
        ]
    ]
    persistent_markup = ReplyKeyboardMarkup(
        reply_keyboard,
        resize_keyboard=True,
        one_time_keyboard=False
    )

    # Inline keyboard for the welcome message itself
    inline_kb = [
        [
            InlineKeyboardButton("📋 تستهای روانشناسی", callback_data="psychology_tests"),
            InlineKeyboardButton("🧠 پکیجهای هوشمند", callback_data="smart_packages")
        ],
        [
            InlineKeyboardButton("🕵️ نتایج تستهای قبلی", callback_data="my_profile"),
            InlineKeyboardButton("💬 جلسه هوشمند درمانی با هوش مصنوعی", callback_data="smart_therapy")
        ]
    ]
    inline_markup = InlineKeyboardMarkup(inline_kb)

    # Use relative path for images
    gif_path = "images/neuron_intro.gif"
    
    if update.message:
        # From direct command - send new message with GIF animation
        try:
            with open(gif_path, "rb") as gif:
                update.message.reply_animation(
                    animation=gif,
                    caption=welcome_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=inline_markup
                )
        except FileNotFoundError:
            logger.warning(f"GIF file not found: {gif_path}")
            update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=inline_markup
            )
        
        # Ensure persistent keyboard is set
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=ui.WELCOME_KEYBOARD_HINT,
            reply_markup=persistent_markup
        )
    else:
        # From callback - try to edit message
        try:
            if hasattr(update, 'callback_query') and update.callback_query:
                if update.callback_query.message.photo or update.callback_query.message.animation:
                    try:
                        with open(gif_path, "rb") as gif:
                            context.bot.send_animation(
                                chat_id=update.effective_chat.id,
                                animation=gif,
                                caption=welcome_text,
                                parse_mode=ParseMode.HTML,
                                reply_markup=inline_markup
                            )
                    except FileNotFoundError:
                        context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=welcome_text,
                            parse_mode=ParseMode.HTML,
                            reply_markup=inline_markup
                        )
                else:
                    update.callback_query.edit_message_text(
                        text=welcome_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=inline_markup
                    )
        except Exception as e:
            logger.error(f"Error in start function: {e}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=inline_markup
            )

def psychology_tests(update: Update, context: CallbackContext):
    """Show available psychology tests"""
    console.log("[cyan]Showing psychology tests menu[/cyan]")
    user = update.effective_user
    save_user_info(user)
    
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
    keyboard.append([InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="back_to_home")])
    
    format_md_for_telegram = import_formatter()
    caption_chunks = format_md_for_telegram(ui.TEST_SELECTION_CAPTION)
    caption_text = caption_chunks[0] if caption_chunks else ui.TEST_SELECTION_CAPTION
    
    image_path = "images/neuron_session.png"
    
    if update.callback_query:
        try:
            if update.callback_query.message.photo:
                update.callback_query.edit_message_caption(
                    caption=caption_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                try:
                    with open(image_path, "rb") as img:
                        context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=img,
                            caption=caption_text,
                            parse_mode=ParseMode.HTML,
                            reply_markup=InlineKeyboardMarkup(keyboard)
                        )
                except FileNotFoundError:
                    logger.warning(f"Image file not found: {image_path}")
                    context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=caption_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
        except Exception as e:
            logger.error(f"Error in psychology_tests: {e}")
            context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=caption_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        try:
            with open(image_path, "rb") as img:
                update.message.reply_photo(
                    photo=img,
                    caption=caption_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        except FileNotFoundError:
            logger.warning(f"Image file not found: {image_path}")
            update.message.reply_text(
                caption_text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

def smart_therapy_session(update: Update, context: CallbackContext):
    """Placeholder for future smart therapy session feature"""
    send_formatted_text(update, ui.SMART_THERAPY_COMING_SOON)

def show_tests_cb(update: Update, context: CallbackContext):
    update.callback_query.answer()
    user = update.effective_user
    save_user_info(user)
    return psychology_tests(update, context)

def show_profile_cb(update: Update, context: CallbackContext):
    update.callback_query.answer()
    user = update.effective_user
    save_user_info(user)
    return my_profile(update, context)
        
def back_to_home_cb(update: Update, context: CallbackContext):
    """Handle back to home button click"""
    query = update.callback_query
    query.answer()
    
    user = update.effective_user
    save_user_info(user)
    
    format_md_for_telegram = import_formatter()
    welcome_chunks = format_md_for_telegram(ui.WELCOME_INTRO)
    welcome_text = welcome_chunks[0] if welcome_chunks else ui.WELCOME_INTRO

    inline_kb = [
        [
            InlineKeyboardButton("📋 تستهای روانشناسی", callback_data="psychology_tests"),
            InlineKeyboardButton("🧠 پکیجهای هوشمند", callback_data="smart_packages")
        ],
        [
            InlineKeyboardButton("🕵️ نتایج تستهای قبلی", callback_data="my_profile"),
            InlineKeyboardButton("💬 جلسه هوشمند درمانی با هوش مصنوعی", callback_data="smart_therapy")
        ]
    ]
    inline_markup = InlineKeyboardMarkup(inline_kb)
    
    try:
        if query.message.photo or query.message.animation:
            try:
                query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
                
            gif_path = "images/neuron_intro.gif"
            try:
                with open(gif_path, "rb") as gif:
                    context.bot.send_animation(
                        chat_id=update.effective_chat.id,
                        animation=gif,
                        caption=welcome_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=inline_markup
                    )
            except FileNotFoundError:
                context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=welcome_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=inline_markup
                )
        else:
            query.edit_message_text(
                text=welcome_text,
                parse_mode=ParseMode.HTML,
                reply_markup=inline_markup
            )
    except Exception as e:
        logger.error(f"Error in back_to_home_cb: {e}")
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
    format_md_for_telegram = import_formatter()
    intro_chunks = format_md_for_telegram(ui.SMART_PACKAGES_INTRO)
    intro_text = intro_chunks[0] if intro_chunks else ui.SMART_PACKAGES_INTRO
    
    keyboard = [
        [InlineKeyboardButton("🍃 پکیج خودآگاهی", callback_data="smart_pack_selfaware")],
        [InlineKeyboardButton("💼پکیج کسبوکار و شغلی", callback_data="smart_pack_business")],
        [InlineKeyboardButton("💫پکیج استعدادها و آینده", callback_data="smart_pack_talents")],
        [InlineKeyboardButton("🧪 پکیج تست", callback_data="smart_pack_test")],
        [InlineKeyboardButton("🏠 بازگشت خانه", callback_data="back_to_home")]
    ]
    
    if update.callback_query:
        try:
            if update.callback_query.message.photo:
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
        update.message.reply_text(
            intro_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def smart_package_selected(update: Update, context: CallbackContext):
    """Handle smart package selection - show package card"""
    console.log(f"[DEBUG] smart_package_selected called with callback_data: {sanitize_for_log(update.callback_query.data)}")
    return show_package_card(update, context)

def show_package_card(update: Update, context: CallbackContext):
    """Show package card with details and purchase option"""
    query = update.callback_query
    query.answer()
    
    logger.info(f"[DEBUG] show_package_card called with callback_data: {sanitize_for_log(query.data)}")
    
    package_id = query.data.split("_")[-1]
    logger.info(f"[DEBUG] Extracted package_id: '{sanitize_for_log(package_id)}'")
    
    try:
        package = packages.get_package_by_id(package_id)
        logger.info(f"[DEBUG] Package lookup result: {package is not None}")
        
        if not package:
            logger.error(f"[ERROR] Package not found for ID: '{sanitize_for_log(package_id)}'")
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
        
        # Get test names for this package
        test_list = ""
        for i, test_id in enumerate(package["tests"], 1):
            if 1 <= test_id <= len(pt.all_tests["tests"]):
                test_data = pt.all_tests["tests"][test_id - 1]
                test_name = test_data["test_name"]
                test_list += f"{i}. {test_name}\n"
            else:
                test_list += f"{i}. تست شماره {test_id}\n"
        
        info_msg = f"""<b>🧠 {name}</b>

<b>💲 قیمت:</b> {price} هزار تومان
<b>🧮 تعداد تستها:</b> {num_tests} عدد
<b>⏰ زمان تخمینی:</b> {time}

<b>📝 توضیحات:</b>
{desc}

<b>💡 هدف و مزایا:</b>
{outcome}

<b>🎯 کاربرد:</b>
{usage}

<b>📋 تستهای شامل در این پکیج:</b>
{test_list}"""
        
        keyboard = [
            [InlineKeyboardButton("🚀 خرید و شروع پکیج", callback_data=f"start_package_{package_id}")],
            [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="charge_wallet")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="smart_packages")]
        ]
        
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
    except (KeyError, IndexError) as e:
        logger.error(f"Error accessing package data: {e}")
        query.message.reply_text("خطا در دریافت اطلاعات پکیج.")

def start_package_callback(update: Update, context: CallbackContext):
    """Handle starting a package"""
    query = update.callback_query
    cid = query.message.chat_id
    
    logger.info(f"[DEBUG] start_package_callback called with callback_data: {sanitize_for_log(query.data)}")
    
    package_id = query.data.split("_")[-1]
    logger.info(f"[DEBUG] Extracted package_id: '{sanitize_for_log(package_id)}'")
    
    try:
        package = packages.get_package_by_id(package_id)
        logger.info(f"[DEBUG] Package lookup result: {package is not None}")
        
        if not package:
            logger.error(f"[ERROR] Package not found for ID: '{sanitize_for_log(package_id)}'")
            query.answer("❌ پکیج مورد نظر یافت نشد.", show_alert=True)
            return
        
        # Check balance
        price = package.get("price", 0)
        balance = db.get_balance(cid)
        
        if balance < price:
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
            db.update_balance(cid, -price)
            user_package_id = db.purchase_package(cid, package_id)
            db.add_package_tests(user_package_id, package["tests"])
            
            query.answer("✅ پکیج با موفقیت خریداری شد!", show_alert=True)
            
            # Send package guide as a new message
            guide_text = package["guide"]
            send_formatted_text(update, guide_text)
            
            # Get tests in this package
            package_tests = db.get_package_tests(user_package_id)
            
            # Create keyboard with test buttons
            keyboard = []
            for pt_test in package_tests:
                test_id = pt_test["test_id"]
                test_completed = pt_test["completed"] == 1
                
                if 1 <= test_id <= len(pt.all_tests["tests"]):
                    test_data = pt.all_tests["tests"][test_id - 1]
                    test_name = test_data["test_name"]
                    
                    status_icon = "✅ " if test_completed else ""
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{status_icon}{test_name}", 
                            callback_data=f"package_test_{user_package_id}_{test_id}"
                        )
                    ])
            
            keyboard.append([
                InlineKeyboardButton("🏠 بازگشت به خانه", callback_data="back_to_home")
            ])
            
            query.message.reply_text(
                ui.PACKAGE_TEST_SELECTION,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error purchasing package: {e}")
            query.answer("❌ خطا در خرید پکیج. لطفاً دوباره تلاش کنید.", show_alert=True)
            db.update_balance(cid, price)  # Refund
    except (KeyError, IndexError) as e:
        logger.error(f"Error accessing package data: {e}")
        query.answer("❌ خطا در پردازش درخواست", show_alert=True)

def package_test_selected(update: Update, context: CallbackContext):
    """Handle selection of a test within a package"""
    query = update.callback_query
    
    logger.info(f"[DEBUG] package_test_selected called with callback_data: {sanitize_for_log(query.data)}")
    
    parts = query.data.split("_")
    logger.info(f"[DEBUG] Callback data parts: {len(parts)} parts")
    
    if len(parts) < 4:
        query.answer("❌ خطا در پردازش درخواست", show_alert=True)
        return
    
    try:
        user_package_id = int(parts[2])
        test_id = int(parts[3])
        logger.info(f"[DEBUG] Extracted user_package_id: {user_package_id}, test_id: {test_id}")
        
        if not (1 <= test_id <= len(pt.all_tests["tests"])):
            query.answer("❌ تست مورد نظر یافت نشد.", show_alert=True)
            return
            
        test_data = pt.all_tests["tests"][test_id - 1]
        
        # Check if test is already completed
        package_test = db.get_package_test_by_test_id(user_package_id, test_id)
        if package_test and package_test["completed"] == 1:
            query.answer(
                f"✅ شما قبلاً تست «{test_data['test_name']}» را انجام دادهاید.\nمیتوانید تست دیگری را انتخاب کنید.",
                show_alert=True
            )
            return
        
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
            [InlineKeyboardButton("🔙 بازگشت به لیست تستها", callback_data=f"view_package_{user_package_id}")],
        ]
        
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
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing callback data: {e}")
        query.answer("❌ خطا در پردازش درخواست", show_alert=True)

def start_package_test_callback(update: Update, context: CallbackContext):
    """Start a test from within a package"""
    query = update.callback_query
    cid = query.message.chat_id
    
    logger.info(f"[DEBUG] start_package_test_callback called with callback_data: {sanitize_for_log(query.data)}")
    
    parts = query.data.split("_")
    logger.info(f"[DEBUG] Callback data parts: {len(parts)} parts")
    
    if len(parts) < 5:
        logger.error(f"[ERROR] Invalid callback data format: {sanitize_for_log(query.data)}")
        query.answer("❌ خطا در پردازش درخواست", show_alert=True)
        return
    
    try:
        user_package_id = int(parts[3])
        test_id = int(parts[4])
        logger.info(f"[DEBUG] Extracted user_package_id: {user_package_id}, test_id: {test_id}")
    except (ValueError, IndexError) as e:
        logger.error(f"[ERROR] Error parsing callback data: {e}")
        query.answer("❌ خطا در پردازش درخواست", show_alert=True)
        return
    
    query.answer()
    
    # Proceed to ask name/age
    chat_states[cid] = {"stage": "ask_name_age", "test_choice": str(test_id), "user_package_id": user_package_id}
    logger.info(f"[DEBUG] Set chat_state for user {cid}: stage=ask_name_age")
    
    # Format and send the name/age prompt
    send_formatted_text(update, ui.ASK_NAME_AGE)

def view_package_callback(update: Update, context: CallbackContext):
    """Show package guide and test list for an existing package"""
    query = update.callback_query
    query.answer()
    
    try:
        user_package_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        query.message.reply_text("❌ خطا در پردازش درخواست.")
        return
    
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
        
        if 1 <= test_id <= len(pt.all_tests["tests"]):
            test_data = pt.all_tests["tests"][test_id - 1]
            test_name = test_data["test_name"]
            
            status_icon = "✅ " if test_completed else ""
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_icon}{test_name}", 
                    callback_data=f"package_test_{user_package_id}_{test_id}"
                )
            ])
    
    keyboard.extend([
        [InlineKeyboardButton("🔙 بازگشت به پکیجها", callback_data="purchased_packages")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_home")]
    ])
    
    send_formatted_text(
        update, 
        ui.PACKAGE_TEST_SELECTION,
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
        try:
            if query.message.photo:
                try:
                    query.message.delete()
                except Exception as e:
                    logger.error(f"Error deleting message: {e}")
            
            context.bot.send_message(
                chat_id=update.effective_chat.id,
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
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="my_profile")])
    
    try:
        if query.message.photo:
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
    save_user_info(user)
    console.log(f"[blue]User {cid} requested profile (intro)[/blue]")

    format_md_for_telegram = import_formatter()
    intro_chunks = format_md_for_telegram(ui.PROFILE_INTRO)
    intro_text = intro_chunks[0] if intro_chunks else ui.PROFILE_INTRO
    
    keyboard = [
        [InlineKeyboardButton("📚 نتایج تستهای قبلی", callback_data="previous_test_results")],
        [InlineKeyboardButton("🧠 پکیجهای خریداری شده", callback_data="purchased_packages")],
        [InlineKeyboardButton("💰 کیف پول من", callback_data="wallet_info")],
        [InlineKeyboardButton("➕ شارژ کیف پول", callback_data="charge_wallet")],
        [InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="back_to_home")]
    ]
    
    if update.callback_query:
        try:
            if update.callback_query.message.photo:
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
        update.message.reply_text(
            intro_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def previous_test_results(update: Update, context: CallbackContext):
    """Show all previous test results."""
    cid = update.effective_chat.id if update.message else update.effective_chat.id
    user = update.effective_user
    save_user_info(user)
    console.log(f"[blue]User {cid} requested previous test results[/blue]")
    
    tests = db.get_user_tests(cid)
    if not tests:
        send_formatted_text(update, ui.NO_PREVIOUS_TESTS)
        return

    keyboard = [
        [InlineKeyboardButton(f"📝 {row['test_name']}", callback_data=f"view_result_{row['id']}")]
        for row in tests
    ]
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="my_profile")])
    
    message_text = ui.PREVIOUS_TESTS_TITLE
    
    if update.callback_query:
        try:
            if update.callback_query.message.photo:
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

    keyboard = [
        [InlineKeyboardButton("➕ شارژ کیف پول", callback_data='charge_wallet')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="my_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        try:
            if update.callback_query.message.photo:
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
    query.answer()
    cid = query.message.chat_id
    
    try:
        if query.message.photo:
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

def handle_payment_screenshot(update: Update, context: CallbackContext):
    """Handle incoming payment screenshot and save file."""
    cid = update.effective_chat.id
    info = chat_states.get(cid)
    
    if info and info.get("stage") == "await_payment_screenshot":
        try:
            # Get highest-res photo
            photo = update.message.photo[-1]
            file = context.bot.getFile(photo.file_id)
            
            # Ensure payments directory exists
            os.makedirs("payments", exist_ok=True)
            
            # Construct safe filepath
            filename = f"{cid}_{int(time.time())}.jpg"
            filepath = get_safe_file_path("payments", filename)
            
            # Download and save file
            file.download(filepath)
            
            # Record screenshot in DB
            db.save_payment_screenshot(cid, filepath)
            
            # Forward screenshot to admin(s)
            user = update.message.from_user
            uname = f"@{user.username}" if user.username else str(cid)
            for admin_id in ADMINS:
                try:
                    with open(filepath, "rb") as img_f:
                        context.bot.send_photo(
                            chat_id=admin_id,
                            photo=img_f,
                            caption=f"📸 Payment screenshot from {uname}"
                        )
                except Exception as e:
                    logger.error(f"Error forwarding screenshot to admin {admin_id}: {e}")
            
            # Show success message
            send_formatted_text(update, ui.PAYMENT_RECEIVED)
            # Clear state
            del chat_states[cid]
            
        except Exception as e:
            logger.error(f"Error processing payment screenshot: {e}")
            update.message.reply_text("❌ خطا در پردازش عکس پرداخت. لطفاً دوباره تلاش کنید.")
    else:
        # Fallback to normal answer handler
        return handle_answer(update, context)

# =============================================================================
# INDIVIDUAL TEST HANDLERS
# =============================================================================

def test_selection(update: Update, context: CallbackContext):
    """Handle test selection from the list"""
    query = update.callback_query
    query.answer()
    
    user = query.from_user
    save_user_info(user)
    cid = query.message.chat_id
    choice = query.data
    
    try:
        test_index = int(choice) - 1
        if not (0 <= test_index < len(pt.all_tests["tests"])):
            query.message.reply_text("❌ تست مورد نظر یافت نشد.")
            return
            
        test_data = pt.all_tests["tests"][test_index]
    except (ValueError, IndexError, KeyError) as e:
        logger.error(f"Error accessing test data: {e}")
        query.message.reply_text("❌ خطا در دریافت اطلاعات تست.")
        return
    
    # Store for later
    chat_states[cid] = {
        "stage": "test_info",
        "test_choice": choice,
        "test_name": test_data["test_name"]
    }
    
    # Build HTML formatted message
    test_name = test_data["test_name"]
    time_est = test_data["estimated_time"]
    outcome = test_data["outcome"]
    usage = test_data["usage"]
    price = test_data.get("price", 0)
    num_questions = len(test_data["questions"])
    
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
    
    try:
        if query.message.photo:
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
    
    try:
        choice = query.data.split("_")[-1]
        test_index = int(choice) - 1
        
        if not (0 <= test_index < len(pt.all_tests["tests"])):
            query.answer("❌ تست مورد نظر یافت نشد.", show_alert=True)
            return
            
        test_data = pt.all_tests["tests"][test_index]
        price = test_data.get("price", 0)
    except (ValueError, IndexError, KeyError) as e:
        logger.error(f"Error accessing test data: {e}")
        query.answer("❌ خطا در پردازش درخواست", show_alert=True)
        return
    
    # Check balance
    balance = db.get_balance(cid)
    if balance < price:
        return query.answer(
            text=ui.INSUFFICIENT_BALANCE.format(balance=balance, price=price),
            show_alert=True
        )
    
    # Record test purchase in database
    try:
        db.update_balance(cid, -price)
        query.answer("✅ تست با موفقیت خریداری شد!", show_alert=True)
        
        # Proceed to ask name
        chat_states[cid].update({"stage": "ask_name_age", "test_choice": choice})
        
        # Format and send name prompt
        send_formatted_text(update, ui.ASK_NAME_AGE)
        
    except Exception as e:
        logger.error(f"Error purchasing test: {e}")
        query.answer("❌ خطا در خرید تست. لطفاً دوباره تلاش کنید.", show_alert=True)
        # Refund the user
        db.update_balance(cid, price)

def view_result_callback(update: Update, context: CallbackContext):
    """Handle view result button click"""
    query = update.callback_query
    query.answer()
    
    try:
        record_id = int(query.data.split("_")[-1])
    except (ValueError, IndexError):
        query.message.reply_text("❌ خطا در پردازش درخواست.")
        return
        
    console.log(f"[cyan]User requested result ID: {record_id}[/cyan]")
    
    result = db.get_test_result(record_id)
    if result:
        stored_summary = result['result_text']
        test_name = result['test_name']
        
        # Send formatted result
        def _import_send_styled_test_result():
            from telegrambot import send_styled_test_result
            return send_styled_test_result
            
        send_styled_test_result = _import_send_styled_test_result()
        send_styled_test_result(update, context, test_name, stored_summary)
        
        # Send PDF if available
        pdf_path = result.get('pdf_path')
        if pdf_path and os.path.exists(pdf_path):
            try:
                with open(pdf_path, 'rb') as pdf_file:
                    query.message.reply_document(
                        pdf_file,
                        filename=f"{test_name}_result.pdf",
                        caption=ui.PDF_CAPTION
                    )
            except Exception as e:
                logger.error(f"Error sending PDF: {e}")
        
        # Add back button after showing results
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به نتایج", callback_data="previous_test_results")]]
        query.message.reply_text(
            "برای بازگشت به لیست نتایج دکمه زیر را لمس کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        console.log(f"[red]Result not found for ID: {record_id}[/red]")
        query.message.reply_text(ui.RESULT_NOT_FOUND)
# =============================================================================
# ANSWER HANDLING AND TEST FLOW
# =============================================================================

def handle_answer(update: Update, context: CallbackContext):
    """Handle user text messages based on current state"""
    cid = update.effective_chat.id
    info = chat_states.get(cid)
    text = update.message.text.strip()

    # Check for admin-specific stages first
    if info and info.get("stage") == "admin_charge_amount":
        return handle_admin_charge_input(update, context, text, info)
    if info and info.get("stage") == "admin_reduce_amount":
        return handle_admin_reduce_input(update, context, text, info)

    if not info or info["stage"] not in ["ask_name_age", "ask_user_info", "answering"]:
        return None

    if info["stage"] == "ask_name_age":
        info["name_age_response"] = text
        info["stage"] = "ask_user_info"
        console.log(f"[blue]User {cid} provided name/age: {sanitize_for_log(text)}[/blue]")
        send_formatted_text(update, ui.ASK_USER_INFO)
        return

    if info["stage"] == "ask_user_info":
        info["user_info_response"] = text
        console.log(f"[blue]User {cid} provided personal info: {sanitize_for_log(text)}[/blue]")

        # Send a loading message to the user
        wait_message = update.message.reply_text("درحال اماده سازی و شروع تست ...")

        # Extract name and age for logging/UI purposes
        name_age_response = info.get("name_age_response", "")
        user_name = name_age_response.split()[0] if name_age_response.split() else "User"
        age_str = "".join(filter(str.isdigit, name_age_response))
        user_age = int(age_str) if age_str.isdigit() else 0
        
        info["name"] = user_name
        info["age"] = user_age

        user_info_full = f"Name and age: {name_age_response}\nPersonal Information: {text}"

        # Initialize test state
        try:
            state = pt.tele_initialize(
                user_name, 
                user_age, 
                user_info_full,
                info["test_choice"], 
                chat_id=cid
            )
            console.log(f"[green]Initialized test for {info['name']}, age {info['age']}, test choice {info['test_choice']}, chat_id {cid}[/green]")

            # Ensure chat_id is set in the state
            if "chat_id" not in state or state["chat_id"] is None:
                state["chat_id"] = cid
                console.log(f"[yellow]Added missing chat_id {cid} to state[/yellow]")

            info["state"] = state
            info["stage"] = "answering"
            
            # Send first question
            first_q = pt.tele_get_question(state)
            
            # Delete the loading message
            try:
                wait_message.delete()
            except Exception as e:
                logger.error(f"Error deleting loading message: {e}")

            console.print(Panel(
                f"[cyan]To User {info['name']}:[/cyan]\n[purple]{first_q}[/purple]",
                title="Bot Sends (First Question)",
                border_style="magenta",
                expand=False
            ))
            
            format_md_for_telegram = import_formatter()
            message_chunks = format_md_for_telegram(first_q)
            
            for chunk in message_chunks:
                update.message.reply_text(chunk, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Error initializing test: {e}")
            try:
                wait_message.delete()
            except:
                pass
            update.message.reply_text("❌ خطا در راه‌اندازی تست. لطفاً دوباره تلاش کنید.")
            if cid in chat_states:
                del chat_states[cid]
        return

    # Stage is "answering"
    console.log(f"[green]User {cid} answered: {sanitize_for_log(text)}[/green]")
    
    console.print(Panel(
        f"[cyan]User response:[/cyan]\n[yellow]{text}[/yellow]",
        title="User Answer",
        border_style="green",
        expand=False
    ))
    
    wait = update.message.reply_text(ui.ANALYZING_ANSWER)
    
    console.log("[yellow]Analyzing user response...[/yellow]")
    
    try:
        res = pt.tele_process_answer(info["state"], text)
        
        # Ensure test_data is included in the state
        if not info["state"].get("test_data"):
            try:
                from psychology_test import test_data
                info["state"]["test_data"] = test_data
                console.log("Added test_data to state for analysis")
            except ImportError:
                console.log("Could not import test_data from psychology_test module")
        
        # Log history summary/trim events
        history_summary = info["state"].get("history_summary")
        if history_summary:
            console.log(f"[magenta]Conversation summary generated:[/magenta]\n{history_summary}")
            kept = len(info["state"]["conversation_history"])
            console.log(f"[magenta]History trimmed, kept last {kept} messages[/magenta]")
        
        # Show full conversation history in a table
        table = Table(title="Full Conversation History", show_header=True, header_style="bold magenta")
        table.add_column("Role", style="cyan", no_wrap=True)
        table.add_column("Message", style="white", overflow="fold")
        for msg in info["state"]["conversation_history"]:
            table.add_row(msg.get("role", ""), msg.get("content", ""))
        console.print(table)
        
        wait.delete()

        ack_message = res.get("ack")
        next_question_message = res.get("next")

        format_md_for_telegram = import_formatter()

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
        elif info["state"].get("finished"):
            # Test completed - generate results
            console.log(f"[green]Test completed for user {cid}. Generating summary...[/green]")
            
            # Ensure chat_id is set in state before summary generation
            if "chat_id" not in info["state"] or info["state"]["chat_id"] is None:
                info["state"]["chat_id"] = cid
                console.log(f"[yellow]Added missing chat_id {cid} to state before summary[/yellow]")
            
            generate_test_results(update, context, info, cid)
    except Exception as e:
        logger.error(f"Error processing answer: {e}")
        try:
            wait.delete()
        except:
            pass
        update.message.reply_text("❌ خطا در پردازش پاسخ. لطفاً دوباره تلاش کنید.")

def generate_test_results(update: Update, context: CallbackContext, info: dict, cid: int):
    """Generate and send test results in background thread"""
    result_data = {"summary": None, "error": None, "images": None, "pdf_path": None}
    
    def generate_results_background():
        """Generate all results in background thread"""
        try:
            # Generate summary
            console.log("[magenta]Generating final summary in background...[/magenta]")
            summary_content = pt.tele_summarize(info["state"])
            result_data["summary"] = summary_content
            
            # Get test name
            test_name = info.get("test_name")
            if not test_name:
                test_choice = info.get("test_choice")
                if test_choice and test_choice.isdigit():
                    test_index = int(test_choice) - 1
                    if 0 <= test_index < len(pt.all_tests["tests"]):
                        test_name = pt.all_tests["tests"][test_index]["test_name"]
                    else:
                        test_name = "تست روانشناسی"
                else:
                    test_name = "تست روانشناسی"
            
            # Generate image
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
                result_data["images"] = images
            except Exception as img_e:
                console.log(f"[red]Image generation error: {img_e}[/red]")
                result_data["images"] = None
            
            # Generate PDF
            try:
                safe_name = re.sub(r'[^\w\-_]', '_', test_name)
                pdf_filename = f"{safe_name}_result.pdf"
                pdf_path = get_safe_file_path("/tmp", pdf_filename)
                
                generate_pdf(summary_content, info["name"], info["age"], test_name, pdf_path)
                result_data["pdf_path"] = pdf_path
                
                # Save to database
                user = update.effective_user
                save_user_info(user)
                db.save_test_result(cid, test_name, summary_content, pdf_path)
                console.log(f"[blue]Saved test result for user {cid}[/blue]")
            except Exception as pdf_e:
                console.log(f"[red]PDF generation error: {pdf_e}[/red]")
                result_data["error"] = str(pdf_e)
                
        except Exception as e:
            console.log(f"[red]Error in background result generation: {e}[/red]")
            result_data["error"] = str(e)
    
    # Start background thread
    background_thread = threading.Thread(target=generate_results_background, daemon=True)
    background_thread.start()
    
    # Show processing messages while background thread works
    waiting_messages = ui.PROCESSING_MESSAGES
    current_message = None
    
    for i, msg_text in enumerate(waiting_messages):
        if current_message:
            try:
                current_message.delete()
            except Exception as e:
                logger.error(f"Error deleting previous waiting message: {e}")
        
        current_message = update.message.reply_text(msg_text)
        time.sleep(3)
    
    # Wait for background thread to complete
    background_thread.join(timeout=30)
    
    # Delete the final waiting message
    if current_message:
        try:
            current_message.delete()
        except Exception as e:
            logger.error(f"Error deleting final waiting message: {e}")
    
    # Send results
    send_test_results(update, context, result_data, info, cid)

def send_test_results(update: Update, context: CallbackContext, result_data: dict, info: dict, cid: int):
    """Send the generated test results to user"""
    if result_data.get("error"):
        update.message.reply_text(ui.ERROR_GENERATING_RESULT)
    elif result_data.get("summary"):
        summary_content = result_data["summary"]
        test_name = info.get("test_name", "تست روانشناسی")
        
        console.print(Panel(
            f"[cyan]Final analysis for {info['name']}:[/cyan]\n[purple]{summary_content[:500]}...[/purple]",
            title="Bot Sends (Test Summary)",
            border_style="magenta",
            expand=False
        ))
        
        # Send image with caption or fallback to styled text
        if result_data.get("images"):
            try:
                def _import_format_caption_for_telegram():
                    from telegrambot import format_caption_for_telegram
                    return format_caption_for_telegram
                    
                format_caption_for_telegram = _import_format_caption_for_telegram()
                caption_text = format_caption_for_telegram(test_name, summary_content)
                
                with open(result_data["images"][0], "rb") as img_f:
                    update.message.reply_photo(
                        photo=img_f,
                        caption=caption_text,
                        parse_mode=ParseMode.HTML
                    )
            except Exception as e:
                console.log(f"[red]Error sending image: {e}[/red]")
                # Fallback to styled text
                def _import_send_styled_test_result():
                    from telegrambot import send_styled_test_result
                    return send_styled_test_result
                    
                send_styled_test_result = _import_send_styled_test_result()
                send_styled_test_result(update, context, test_name, summary_content)
        else:
            # No image, send styled text
            def _import_send_styled_test_result():
                from telegrambot import send_styled_test_result
                return send_styled_test_result
                
            send_styled_test_result = _import_send_styled_test_result()
            send_styled_test_result(update, context, test_name, summary_content)
        
        # Send PDF if available
        if result_data.get("pdf_path") and os.path.exists(result_data["pdf_path"]):
            try:
                with open(result_data["pdf_path"], "rb") as pdf_f:
                    update.message.reply_document(
                        pdf_f,
                        filename=f"{test_name}_result.pdf",
                        caption=ui.PDF_CAPTION
                    )
            except Exception as e:
                logger.error(f"Error sending PDF: {e}")
    else:
        update.message.reply_text("❌ خطا در تولید نتایج. لطفاً دوباره تلاش کنید.")
        
    # Handle package completion and cleanup
    if cid in chat_states:
        info = chat_states.get(cid)
        if info and "user_package_id" in info:
            handle_package_test_completion(
                update,
                context,
                cid,
                info["user_package_id"],
                int(info["test_choice"]),
                info,
            )
        del chat_states[cid]
    else:
        console.log(f"Attempted to delete non-existent chat state for user {cid}")

def handle_package_test_completion(update: Update, context: CallbackContext,
                                   chat_id: int, user_package_id: int, test_id: int, info: dict):
    """Handle completion of a test within a package"""
    try:
        # Get tests in this specific package
        package_tests = db.get_package_tests(user_package_id)

        for pt_test in package_tests:
            if pt_test["test_id"] == test_id and pt_test["completed"] == 0:
                # Ensure pt_test has required id field
                if "id" not in pt_test:
                    logger.error(f"Package test missing id field: {pt_test}")
                    continue
                    
                # Mark this test as completed
                db.mark_package_test_completed(pt_test["id"])

                # Check if all tests in the package are completed
                all_tests = db.get_package_tests(user_package_id)
                all_completed = all(test["completed"] == 1 for test in all_tests)

                if all_completed:
                    # Get package info with proper error handling
                    pkg_info_from_db = db.get_user_package(user_package_id)
                    if not pkg_info_from_db:
                        console.log(f"[red]Could not find package info for user_package_id: {user_package_id}[/red]")
                        return
                    
                    pkg_info = packages.get_package_by_id(pkg_info_from_db["package_id"])
                    if not pkg_info:
                        console.log(f"[red]Could not find package details for package_id: {pkg_info_from_db['package_id']}[/red]")
                        return

                    # Show completion notification
                    try:
                        completion_message = f"🎉 تبریک! شما تمام تستهای پکیج «{pkg_info['name']}» را با موفقیت به پایان رساندید."
                        
                        context.bot.send_message(
                            chat_id=chat_id,
                            text="🔔 " + completion_message,
                            parse_mode=ParseMode.HTML
                        )
                        
                    except Exception as e:
                        console.log(f"[red]Error sending completion message: {e}[/red]")
                    
                    # Get user info
                    user = db.get_user(chat_id)
                    if not user:
                        console.log(f"[red]Could not find user info for chat_id: {chat_id}[/red]")
                        return
                    
                    # Get all test results
                    results = []
                    for test in all_tests:
                        result = db.get_test_result_by_test_id(chat_id, test["test_id"])
                        if result:
                            results.append(result)

                    # Generate and send the report
                    if results:
                        send_package_report(update, context, chat_id, user["first_name"], info.get("age"), pkg_info["name"], results)
                else:
                    # Show individual test completion notification
                    try:
                        context.bot.send_message(
                            chat_id=chat_id,
                            text="🔔 ✅ آفرین! تست شما با موفقیت ذخیره شد. برای ادامه، تست بعدی را انتخاب کنید.",
                            parse_mode=ParseMode.HTML
                        )
                    except Exception as e:
                        console.log(f"[red]Error sending test completion alert: {e}[/red]")
                    
                    # Partial completion → prompt next test
                    pkg_info_from_db = db.get_user_package(user_package_id)
                    if pkg_info_from_db:
                        pkg_info = packages.get_package_by_id(pkg_info_from_db["package_id"])
                        if pkg_info:
                            show_package_guide_by_id(context, chat_id, user_package_id, pkg_info)
                return
    except Exception as e:
        logger.error(f"Error in handle_package_test_completion: {e}")

def send_package_report(update: Update, context: CallbackContext, chat_id: int, user_name: str, user_age: int, package_name: str, results: list):
    """Generate and send the package report."""
    wait_message = context.bot.send_message(
        chat_id=chat_id,
        text="در حال آمادهسازی گزارش جامع شما... لطفاً چند لحظه صبر کنید.",
    )

    try:
        report = package_ai.summarize_package_results(
            user_name, user_age, package_name, results
        )
    except Exception as e:
        logger.error(f"Error generating package report: {e}")
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ متأسفانه در حال حاضر امکان ایجاد گزارش وجود ندارد. لطفاً بعداً دوباره تلاش کنید.",
        )
        return
    finally:
        try:
            wait_message.delete()
        except Exception as e:
            logger.error(f"Error deleting waiting message: {e}")

    send_formatted_text(update, report)

def show_package_guide_by_id(context: CallbackContext, chat_id: int, user_package_id: int, package: dict):
    """Show package guide and test list by IDs"""
    try:
        format_md_for_telegram = import_formatter()
        guide_chunks = format_md_for_telegram(package["guide"])
        
        # Send each chunk of the guide
        for chunk in guide_chunks:
            context.bot.send_message(
                chat_id=chat_id,
                text=chunk,
                parse_mode=ParseMode.HTML
            )
            time.sleep(0.5)
        
        # Get tests in this package
        package_tests = db.get_package_tests(user_package_id)
        
        # Create keyboard with test buttons
        keyboard = []
        for pt_test in package_tests:
            test_id = pt_test["test_id"]
            test_completed = pt_test["completed"] == 1
            
            if 1 <= test_id <= len(pt.all_tests["tests"]):
                test_data = pt.all_tests["tests"][test_id - 1]
                test_name = test_data["test_name"]
                
                status_icon = "✅ " if test_completed else ""
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"{status_icon}{test_name}", 
                        callback_data=f"package_test_{user_package_id}_{test_id}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="psychology_tests")])
        
        # Format and send the test selection message
        selection_chunks = format_md_for_telegram(ui.PACKAGE_TEST_SELECTION)
        selection_text = selection_chunks[0] if selection_chunks else ui.PACKAGE_TEST_SELECTION
        
        context.bot.send_message(
            chat_id=chat_id,
            text=selection_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in show_package_guide_by_id: {e}")
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
        except Exception as e:
            logger.error(f"Error getting chat info for user {uid}: {e}")
            uname = str(uid)
        keyboard.append([InlineKeyboardButton(uname, callback_data=f"admin_user_{uid}")])
    
    query.message.reply_text(ui.ADMIN_USERS_LIST_TITLE, reply_markup=InlineKeyboardMarkup(keyboard))

@admin_only
def admin_user_options(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    try:
        chat_id = query.data.split("_")[-1]
        # Validate chat_id is numeric
        int(chat_id)
    except (ValueError, IndexError):
        query.message.reply_text("❌ خطا در پردازش شناسه کاربر.")
        return
    
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
    
    try:
        parts = query.data.split("_")
        if len(parts) < 4:
            raise ValueError("Invalid callback data format")
        target = parts[2]
        target_id = int(target)  # Validate it's numeric
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing admin callback data: {e}")
        query.message.reply_text("❌ خطا در پردازش درخواست.")
        return
    
    chat_states[admin_id] = {"stage": "admin_charge_amount", "target": target_id}
    query.message.reply_text(ui.ADMIN_CHARGE_PROMPT.format(user_id=target))

@admin_only
def admin_reduce_prompt(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    admin_id = query.message.chat_id
    
    try:
        parts = query.data.split("_")
        if len(parts) < 4:
            raise ValueError("Invalid callback data format")
        target = parts[2]
        target_id = int(target)  # Validate it's numeric
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing admin callback data: {e}")
        query.message.reply_text("❌ خطا در پردازش درخواست.")
        return
    
    chat_states[admin_id] = {"stage": "admin_reduce_amount", "target": target_id}
    query.message.reply_text(ui.ADMIN_REDUCE_PROMPT.format(user_id=target))

@admin_only
def handle_admin_charge_input(update: Update, context: CallbackContext, amount_text: str, admin_info: dict):
    admin_id = update.effective_chat.id
    target_user_id = admin_info.get("target")

    if not target_user_id:
        update.message.reply_text("❌ خطای داخلی: شناسه کاربر هدف یافت نشد.")
        if admin_id in chat_states:
            del chat_states[admin_id]
        return

    try:
        amount = int(amount_text)
        if amount <= 0:
            update.message.reply_text(ui.ADMIN_AMOUNT_MUST_BE_POSITIVE)
            return  # Keep state to allow re-entry

        db.update_balance(target_user_id, amount)
        new_balance = db.get_balance(target_user_id)
        
        update.message.reply_text(
            ui.ADMIN_CHARGE_SUCCESS.format(
                user_id=target_user_id,
                amount=amount,
                balance=new_balance
            )
        )
        
        # Notify the user
        try:
            context.bot.send_message(
                chat_id=target_user_id,
                text=f"🎉 کیف پول شما به مبلغ {amount} هزار تومان شارژ شد.\nموجودی جدید: {new_balance} هزار تومان"
            )
        except Exception as e:
            logger.error(f"Failed to notify user {target_user_id} about charge: {e}")
            update.message.reply_text(f"⚠️ اخطار: موفق به اطلاعرسانی به کاربر {target_user_id} نشدیم.")

        if admin_id in chat_states:
            del chat_states[admin_id]

    except ValueError:
        update.message.reply_text(ui.ADMIN_INVALID_AMOUNT)
        return  # Keep state to allow re-entry
    except sqlite3.Error as e:
        logger.error(f"Database error during admin charge: {e}")
        update.message.reply_text("❌ خطای پایگاه داده هنگام شارژ کیف پول رخ داد.")
        if admin_id in chat_states:
            del chat_states[admin_id]
    except Exception as e:
        logger.error(f"Unexpected error during admin charge: {e}")
        update.message.reply_text("❌ یک خطای پیشبینی نشده رخ داد.")
        if admin_id in chat_states:
            del chat_states[admin_id]

@admin_only
def handle_admin_reduce_input(update: Update, context: CallbackContext, amount_text: str, admin_info: dict):
    admin_id = update.effective_chat.id
    target_user_id = admin_info.get("target")

    if not target_user_id:
        update.message.reply_text("❌ خطای داخلی: شناسه کاربر هدف یافت نشد.")
        if admin_id in chat_states:
            del chat_states[admin_id]
        return

    try:
        amount = int(amount_text)
        if amount <= 0:
            update.message.reply_text(ui.ADMIN_AMOUNT_MUST_BE_POSITIVE)
            return  # Keep state to allow re-entry

        current_balance = db.get_balance(target_user_id)
        if amount > current_balance:
            update.message.reply_text(
                ui.ADMIN_AMOUNT_EXCEEDS_BALANCE.format(
                    amount=amount,
                    balance=current_balance
                )
            )
            return  # Keep state to allow re-entry

        # Reduce balance but ensure it doesn't go below zero
        new_balance = max(0, current_balance - amount)
        db.update_balance(target_user_id, -min(amount, current_balance))
        
        update.message.reply_text(
            ui.ADMIN_REDUCE_SUCCESS.format(
                user_id=target_user_id,
                amount=min(amount, current_balance),
                balance=new_balance
            )
        )
        
        # Notify the user
        try:
            context.bot.send_message(
                chat_id=target_user_id,
                text=f"ℹ️ مبلغ {min(amount, current_balance)} هزار تومان از کیف پول شما کسر شد.\nموجودی جدید: {new_balance} هزار تومان"
            )
        except Exception as e:
            logger.error(f"Failed to notify user {target_user_id} about balance reduction: {e}")
            update.message.reply_text(f"⚠️ اخطار: موفق به اطلاعرسانی به کاربر {target_user_id} نشدیم.")
            
        if admin_id in chat_states:
            del chat_states[admin_id]

    except ValueError:
        update.message.reply_text(ui.ADMIN_INVALID_AMOUNT)
        return  # Keep state to allow re-entry
    except sqlite3.Error as e:
        logger.error(f"Database error during admin balance reduction: {e}")
        update.message.reply_text("❌ خطای پایگاه داده هنگام کاهش موجودی رخ داد.")
        if admin_id in chat_states:
            del chat_states[admin_id]
    except Exception as e:
        logger.error(f"Unexpected error during admin balance reduction: {e}")
        update.message.reply_text("❌ یک خطای پیشبینی نشده رخ داد.")
        if admin_id in chat_states:
            del chat_states[admin_id]