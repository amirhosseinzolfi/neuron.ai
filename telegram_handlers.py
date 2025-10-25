"""
Telegram bot handlers for Blue Psychology Test Bot.
This module contains all the handler functions for the Telegram bot.
"""
import re
import time
import os
import sqlite3
import logging
import threading
import random
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ParseMode, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import CallbackContext
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

import psychology_test as pt
import ai_utils
import db
import packages
import package_ai
from pdf_utils import generate_pdf
import telegram_ui as ui
from smart_chat import get_chat_agent, get_memory, chat as smart_chat_logic
from utils import chat_states, admin_only, escape_markdown_v2, ADMINS
from telegram_text_optimizer import optimize_for_telegram

# Console for rich logging
console = Console()
logger = logging.getLogger(__name__)

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

# Global smart chat agent
SMART_CHAT_AGENT = None

def get_smart_chat_agent():
    """Initializes and returns the smart chat agent with detailed logging."""
    global SMART_CHAT_AGENT
    
    console.log("[bold blue]🔧 Getting Smart Chat Agent...[/bold blue]")
    
    if SMART_CHAT_AGENT is None:
        console.log("[yellow]⚠️ Agent not initialized, creating new instance...[/yellow]")
        try:
            console.log("[blue]💾 Initializing memory...[/blue]")
            memory = get_memory()
            
            console.log("[blue]🤖 Creating chat agent...[/blue]")
            SMART_CHAT_AGENT = get_chat_agent(memory)
            
            console.log("[bold green]✅ Smart Chat Agent created and cached![/bold green]")
        except Exception as e:
            console.log(f"[bold red]❌ Failed to create Smart Chat Agent: {e}[/bold red]")
            logger.error(f"Smart chat agent creation failed: {e}", exc_info=True)
            raise
    else:
        console.log("[green]✅ Using cached Smart Chat Agent[/green]")
    
    return SMART_CHAT_AGENT

def send_formatted_text(update: Update, text: str, reply_markup=None):
    """Formats markdown/text to Telegram-friendly HTML using telegram_text_optimizer
    and sends it, handling message editing. Splits into safe-sized chunks."""
    # If the text already looks like optimized HTML, skip additional optimization.
    if text and ("<b>" in text or "<i>" in text or "<code>" in text):
        optimized = text
    else:
        optimized = optimize_for_telegram(text or "")

    # Simple chunking by paragraphs to keep messages under Telegram limits
    def _chunk_html(html_text: str, max_len: int = 4000):
        if not html_text:
            return [""]
        if len(html_text) <= max_len:
            return [html_text]
        paragraphs = [p.strip() for p in re.split(r'\n\s*\n', html_text) if p.strip()]
        chunks = []
        current = ""
        for para in paragraphs:
            add_len = len(para) + (2 if current else 0)
            if len(current) + add_len <= max_len:
                current += ("\n\n" if current else "") + para
            else:
                if current:
                    chunks.append(current)
                if len(para) > max_len:
                    # break very long paragraph by lines
                    for line in para.split('\n'):
                        if len(line) > max_len:
                            # fallback hard split
                            for i in range(0, len(line), max_len):
                                chunks.append(line[i : i + max_len])
                            current = ""
                        else:
                            if current and len(current) + 1 + len(line) <= max_len:
                                current += "\n" + line
                            else:
                                if current:
                                    chunks.append(current)
                                current = line
                    if current:
                        chunks.append(current)
                        current = ""
                else:
                    current = para
        if current:
            chunks.append(current)
        return chunks or [html_text[:max_len]]

    message_chunks = _chunk_html(optimized)

    is_callback = update.callback_query is not None

    if is_callback:
        reply_method = update.callback_query.message.reply_text
        edit_method = update.callback_query.edit_message_text
    else:
        reply_method = update.message.reply_text
        edit_method = None

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

def safe_edit_message(update: Update, context: CallbackContext, text: str, 
                     reply_markup=None, image_path=None, parse_mode=ParseMode.HTML):
    """Safely edit or send message with proper fallback handling."""
    if update.callback_query:
        query = update.callback_query
        
        # Handle image messages
        if image_path and (query.message.photo or query.message.animation):
            try:
                query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
            
            if image_path.endswith('.gif'):
                with open(image_path, "rb") as gif:
                    return context.bot.send_animation(
                        chat_id=update.effective_chat.id,
                        animation=gif,
                        caption=text,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup
                    )
            else:
                with open(image_path, "rb") as img:
                    return context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=img,
                        caption=text,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup
                    )
        
        # Handle text/media conversion
        if query.message.photo and not image_path:
            try:
                query.message.delete()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
            
            return context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        
        # Edit existing text message
        try:
            return query.edit_message_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Could not edit message: {e}")
            return query.message.reply_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
    else:
        # New message
        if image_path:
            if image_path.endswith('.gif'):
                with open(image_path, "rb") as gif:
                    return update.message.reply_animation(
                        animation=gif,
                        caption=text,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup
                    )
            else:
                with open(image_path, "rb") as img:
                    return update.message.reply_photo(
                        photo=img,
                        caption=text,
                        parse_mode=parse_mode,
                        reply_markup=reply_markup
                    )
        else:
            return update.message.reply_text(
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )

def get_formatted_text(text: str):
    """Get formatted text chunks (first chunk returned) optimized via telegram_text_optimizer."""
    optimized = optimize_for_telegram(text or "")

    # Return first reasonable-sized chunk
    if len(optimized) <= 4000:
        return optimized
    # else split by paragraphs
    parts = [p.strip() for p in re.split(r'\n\s*\n', optimized) if p.strip()]
    current = ""
    for part in parts:
        if len(current) + len(part) + 2 <= 4000:
            current += ("\n\n" if current else "") + part
        else:
            if current:
                return current
            # single large part — truncate safely
            return part[:3996] + "..."
    return current or optimized[:4000]

def save_user_data(update: Update):
    """Save user data to database."""
    user = update.effective_user
    db.save_user(user.id, user.username, user.first_name, user.last_name)

# =============================================================================
# MAIN MENU AND NAVIGATION HANDLERS
# =============================================================================

def start(update: Update, context: CallbackContext):
    """Show main menu with four persistent options."""
    save_user_data(update)
    console.log("[green]User started the bot[/green]")

    welcome_text = get_formatted_text(ui.WELCOME_INTRO)
    
    # Persistent reply keyboard
    reply_keyboard = [
        [KeyboardButton("📋 تست‌های روانشناسی"), KeyboardButton("🧠 پکیج‌های هوشمند")],
        [KeyboardButton("🧑‍💼 پروفایل من"), KeyboardButton("💬 جلسه هوشمند")]
    ]
    persistent_markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

    # Inline keyboard
    inline_kb = [
        [InlineKeyboardButton("📋 تست‌های روانشناسی", callback_data="psychology_tests"),
         InlineKeyboardButton("🧠 پکیج‌های هوشمند", callback_data="smart_packages")],
        [InlineKeyboardButton("🕵️ نتایج تست‌های قبلی", callback_data="my_profile"),
         InlineKeyboardButton("💬 جلسه هوشمند", callback_data="smart_therapy")]
    ]
    inline_markup = InlineKeyboardMarkup(inline_kb)

    gif_path = "/root/blue-psychology-test/images/neuron_intro.gif"
    
    if update.message:
        # From direct command
        safe_edit_message(update, context, welcome_text, inline_markup, gif_path)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=ui.WELCOME_KEYBOARD_HINT,
            reply_markup=persistent_markup
        )
    else:
        # From callback
        safe_edit_message(update, context, welcome_text, inline_markup, gif_path)

def handle_keyboard_buttons(update: Update, context: CallbackContext):
    """Handle persistent reply keyboard buttons and non-button messages.

    Behavior:
    - If user presses the Smart Chat keyboard button, start/continue smart chat.
    - If user presses any other keyboard button, stop smart chat.
    - If user sends plain text that is NOT a keyboard button and is not currently
      in a psychology test flow, automatically start smart chat and forward the
      message to the smart chat handler.
    - Prevent duplicate processing by setting a short-lived skip flag that
      `handle_answer` will honor.
    """
    button_map = {
        "📋 تست‌های روانشناسی": psychology_tests,
        "🧠 پکیج‌های هوشمند": smart_packages,
        "🧑‍💼 پروفایل من": my_profile,
        "💬 جلسه هوشمند": smart_therapy_session,
        "💰 کیف پول من": wallet,
    }

    text = update.message.text if update.message else ""
    handler = button_map.get(text)

    # Mark to skip the lower-priority text handler to avoid duplicate processing
    context.user_data["_skip_handle_answer"] = True

    if handler:
        # Stop smart chat for all buttons except the smart chat button
        if text != "💬 جلسه هوشمند":
            context.user_data["smart_chat_active"] = False
        else:
            context.user_data["smart_chat_active"] = True

        return handler(update, context)

    # Not a menu button. If user is in a psychology test flow or admin flow, do nothing here
    cid = update.message.chat_id
    info = chat_states.get(cid)
    if info and info.get("stage") in ["ask_name_age", "ask_user_info", "answering", "admin_charge_amount", "admin_reduce_amount", "await_payment_screenshot"]:
        # Allow normal test flow or admin handlers to operate
        # clear skip flag so handle_answer can run for test/admin flow
        context.user_data.pop("_skip_handle_answer", None)
        return None

    # Otherwise automatically start smart chat and forward message
    context.user_data["smart_chat_active"] = True
    return handle_smart_chat_message(update, context)

def psychology_tests(update: Update, context: CallbackContext):
    """Show available psychology tests"""
    console.log("[cyan]Showing psychology tests menu[/cyan]")
    save_user_data(update)
    
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
    
    caption_text = get_formatted_text(ui.TEST_SELECTION_CAPTION)
    image_path = "/root/blue-psychology-test/images/neuron_session.png"
    
    safe_edit_message(update, context, caption_text, InlineKeyboardMarkup(keyboard), image_path)

def smart_therapy_session(update: Update, context: CallbackContext):
    """Handles the smart therapy session with a friendly greeting and logging."""
    console.log("[bold blue]🎯 Smart Therapy Session Handler Called[/bold blue]")
    
    if not context.user_data.get("smart_chat_active"):
        console.log("[green]🚀 Activating smart chat for user...[/green]")
        context.user_data["smart_chat_active"] = True
        
        # Creative and friendly greeting message
        greeting_message = """🧠✨ سلام! به جلسه هوشمند خوش آمدید! ✨🧠

من نورون هستم، دستیار هوشمند شما! 🤖💙
آماده‌ام تا در یک گفتگوی دوستانه و آرامش‌بخش، شما را همراهی کنم.

🌟 در این جلسه می‌توانید:
• هر چیزی که در ذهنتان است را بگویید
• سوالاتتان را مطرح کنید  
• از تجربیاتتان بگویید
• راهنمایی و پشتیبانی دریافت کنید

💬 فقط کافیه شروع کنید... من اینجام تا گوش کنم و کمکتان کنم!

برای خروج از جلسه، دستور /end_chat را ارسال کنید."""
        
        console.log("[blue]📤 Sending greeting message...[/blue]")
        send_formatted_text(update, greeting_message)
        console.log("[bold green]✅ Smart therapy session started successfully![/bold green]")
    else:
        console.log("[yellow]ℹ️ Smart chat already active for this user[/yellow]")

def handle_smart_chat_message(update: Update, context: CallbackContext):
    """Handles messages during a smart chat session with detailed logging."""
    console.log("[bold cyan]💬 Smart Chat Message Handler Called[/bold cyan]")
    
    if not context.user_data.get("smart_chat_active"):
        console.log("[yellow]⚠️ Smart chat not active, returning[/yellow]")
        return  # Not in smart chat mode, do nothing.

    user_id = str(update.effective_chat.id)
    message_text = update.message.text
    
    # Create info panel
    console.print(Panel(
        f"[cyan]User ID:[/cyan] {user_id}\n"
        f"[cyan]Message:[/cyan] {message_text[:100]}{'...' if len(message_text) > 100 else ''}",
        title="📨 Smart Chat Message",
        border_style="cyan"
    ))

    # Show waiting message while processing
    console.log("[blue]📤 Sending waiting message to user...[/blue]")
    waiting_message = update.message.reply_text("🧠 نورون در حال فکر کردن ... 💭")
    
    try:
        console.log("[yellow]🤖 Getting smart chat agent...[/yellow]")
        agent = get_smart_chat_agent()
        
        console.log("[yellow]🚀 Calling smart chat logic...[/yellow]")
        response = smart_chat_logic(agent, user_id, message_text)
        
        console.log(f"[green]✅ Received response ({(len(response['raw']) if isinstance(response, dict) else len(response))} chars)[/green]" if isinstance(response, dict) else f"[green]✅ Received response ({len(response)} chars)[/green]")
        console.log(f"[dim]Response preview: {(response['raw'][:100] if isinstance(response, dict) else response[:100])}{'...' if (isinstance(response, dict) and len(response['raw'])>100) or (not isinstance(response, dict) and len(response)>100) else ''}[/dim]")

        # Delete waiting message
        console.log("[blue]🗑️ Deleting waiting message...[/blue]")
        try:
            waiting_message.delete()
        except Exception:
            pass

        # Prefer refined version if provided
        if isinstance(response, dict) and "refined" in response:
            display_text = response["refined"]
        else:
            display_text = response if isinstance(response, str) else str(response)

        console.log("[blue]📤 Sending refined response to user...[/blue]")
        send_formatted_text(update, display_text)
        
        console.log("[bold green]✅ Smart chat message handled successfully![/bold green]")
        
    except Exception as e:
        console.log(f"[bold red]❌ Error in smart chat message handler: {e}[/bold red]")
        logger.error(f"Smart chat message handler error: {e}", exc_info=True)
        
        # Delete waiting message even if there's an error
        try:
            waiting_message.delete()
        except Exception:
            pass
            
        console.log("[blue]📤 Sending error message to user...[/blue]")
        send_formatted_text(update, "متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید.")

def end_smart_chat(update: Update, context: CallbackContext):
    """Ends the smart chat session via command."""
    if context.user_data.get("smart_chat_active"):
        context.user_data["smart_chat_active"] = False
        update.message.reply_text("جلسه گفتگوی هوشمند به پایان رسید. برای شروع مجدد، دکمه مربوطه را بزنید.")
    else:
        update.message.reply_text("در حال حاضر جلسه گفتگوی هوشمندی فعال نیست.")

def end_smart_chat(update: Update, context: CallbackContext):
    """Ends the smart chat session."""
    if context.user_data.get("smart_chat_active"):
        context.user_data["smart_chat_active"] = False
        update.message.reply_text("جلسه گفتگوی هوشمند به پایان رسید. برای شروع مجدد، دکمه مربوطه را بزنید.")
    else:
        update.message.reply_text("در حال حاضر جلسه گفتگوی هوشمندی فعال نیست.")

# Simple callbacks
def show_tests_cb(update: Update, context: CallbackContext):
    update.callback_query.answer()
    save_user_data(update)
    return psychology_tests(update, context)

def show_profile_cb(update: Update, context: CallbackContext):
    update.callback_query.answer()
    save_user_data(update)
    return my_profile(update, context)
        
def back_to_home_cb(update: Update, context: CallbackContext):
    """Handle back to home button click"""
    query = update.callback_query
    query.answer()
    save_user_data(update)
    
    welcome_text = get_formatted_text(ui.WELCOME_INTRO)
    inline_kb = [
        [InlineKeyboardButton("📋 تست‌های روانشناسی", callback_data="psychology_tests"),
         InlineKeyboardButton("🧠 پکیج‌های هوشمند", callback_data="smart_packages")],
        [InlineKeyboardButton("🕵️ نتایج تست‌های قبلی", callback_data="my_profile"),
         InlineKeyboardButton("💬 جلسه هوشمند درمانی با هوش مصنوعی", callback_data="smart_therapy")]
    ]
    
    gif_path = "/root/blue-psychology-test/images/neuron_intro.gif"
    safe_edit_message(update, context, welcome_text, InlineKeyboardMarkup(inline_kb), gif_path)

# =============================================================================
# SMART PACKAGES HANDLERS
# =============================================================================

def smart_packages(update: Update, context: CallbackContext):
    """Show smart AI packages explanation and package options."""
    intro_text = get_formatted_text(ui.SMART_PACKAGES_INTRO)
    
    keyboard = [
        [InlineKeyboardButton("🍃 پکیج خودآگاهی", callback_data="smart_pack_selfaware")],
        [InlineKeyboardButton("💼پکیج کسب‌وکار و شغلی", callback_data="smart_pack_business")],
        [InlineKeyboardButton("💫پکیج استعدادها و آینده", callback_data="smart_pack_talents")],
        [InlineKeyboardButton("🧪 پکیج تست", callback_data="smart_pack_test")],
        [InlineKeyboardButton("🏠 بازگشت خانه", callback_data="back_to_home")]
    ]
    
    safe_edit_message(update, context, intro_text, InlineKeyboardMarkup(keyboard))

def smart_package_selected(update: Update, context: CallbackContext):
    """Handle smart package selection - show package card"""
    console.log(f"[DEBUG] smart_package_selected called with callback_data: {update.callback_query.data}")
    return show_package_card(update, context)

def show_package_card(update: Update, context: CallbackContext):
    """Show package card with details and purchase option"""
    query = update.callback_query
    query.answer()
    
    package_id = query.data.split("_")[-1]
    logger.info(f"[DEBUG] Extracted package_id: '{package_id}'")
    
    package = packages.get_package_by_id(package_id)
    if not package:
        logger.error(f"[ERROR] Package not found for ID: '{package_id}'")
        query.message.reply_text("پکیج مورد نظر یافت نشد.")
        return
    
    # Get test names for this package
    test_list = ""
    for i, test_id in enumerate(package["tests"], 1):
        if 1 <= test_id <= len(pt.all_tests["tests"]):
            test_data = pt.all_tests["tests"][test_id - 1]
            test_list += f"{i}. {test_data['test_name']}\n"
        else:
            test_list += f"{i}. تست شماره {test_id}\n"
    
    info_msg = f"""<b>🧠 {package["name"]}</b>

<b>💲 قیمت:</b> {package.get("price", 0)} هزار تومان
<b>🧮 تعداد تست‌ها:</b> {len(package["tests"])} عدد
<b>⏰ زمان تخمینی:</b> {package["estimated_time"]}

<b>📝 توضیحات:</b>
{package["description"]}

<b>💡 هدف و مزایا:</b>
{package["outcome"]}

<b>🎯 کاربرد:</b>
{package["usage"]}

<b>📋 تست‌های شامل در این پکیج:</b>
{test_list}"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 خرید و شروع پکیج", callback_data=f"start_package_{package_id}")],
        [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="charge_wallet")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="smart_packages")]
    ]
    
    safe_edit_message(update, context, info_msg, InlineKeyboardMarkup(keyboard))

def start_package_callback(update: Update, context: CallbackContext):
    """Handle starting a package"""
    query = update.callback_query
    cid = query.message.chat_id
    
    package_id = query.data.split("_")[-1]
    package = packages.get_package_by_id(package_id)
    
    if not package:
        query.answer("❌ پکیج مورد نظر یافت نشد.", show_alert=True)
        return
    
    price = package.get("price", 0)
    balance = db.get_balance(cid)
    
    if balance < price:
        return query.answer(
            text=f"⚠️ موجودی کیف پول شما کافی نیست!\n\n"
                 f"موجودی فعلی: {balance} هزار تومان\n"
                 f"هزینه پکیج: {price} هزار تومان\n\n"
                 "لطفاً ابتدا کیف پول خود را شارژ کنید.",
            show_alert=True
        )
    
    try:
        db.update_balance(cid, -price)
        new_balance = db.get_balance(cid)
        user_package_id = db.purchase_package(cid, package_id)
        db.add_package_tests(user_package_id, package["tests"])
        
        query.answer(
            f"✅ پکیج با موفقیت خریداری شد!\n\nمبلغ پرداختی: {price:,} تومان\nموجودی باقیمانده: {new_balance:,} تومان",
            show_alert=True
        )
        
        send_formatted_text(update, package["guide"])
        
        # Show test selection
        package_tests = db.get_package_tests(user_package_id)
        keyboard = []
        
        for pt_test in package_tests:
            test_id = pt_test["test_id"]
            if 1 <= test_id <= len(pt.all_tests["tests"]):
                test_data = pt.all_tests["tests"][test_id - 1]
                status_icon = "✅ " if pt_test["completed"] == 1 else ""
                keyboard.append([
                    InlineKeyboardButton(
                        f"{status_icon}{test_data['test_name']}", 
                        callback_data=f"package_test_{user_package_id}_{test_id}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton("🏠 بازگشت به خانه", callback_data="back_to_home")])
        
        query.message.reply_text(
            ui.PACKAGE_TEST_SELECTION,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error purchasing package: {e}")
        query.answer("❌ خطا در خرید پکیج. لطفاً دوباره تلاش کنید.", show_alert=True)
        db.update_balance(cid, price)

def package_test_selected(update: Update, context: CallbackContext):
    """Handle selection of a test within a package"""
    query = update.callback_query
    
    parts = query.data.split("_")
    user_package_id = int(parts[2])
    test_id = int(parts[3])
    
    if not (1 <= test_id <= len(pt.all_tests["tests"])):
        query.answer("❌ تست مورد نظر یافت نشد.", show_alert=True)
        return
    
    test_data = pt.all_tests["tests"][test_id - 1]
    
    # Check if test is already completed
    package_test = db.get_package_test_by_test_id(user_package_id, test_id)
    if package_test["completed"] == 1:
        query.answer(
            f"✅ شما قبلاً تست «{test_data['test_name']}» را انجام داده‌اید.\nمی‌توانید تست دیگری را انتخاب کنید.",
            show_alert=True
        )
        return
    
    query.answer()
    
    info_msg = f"""<b>🎯 {test_data["test_name"]}</b>

<b>🧮 تعداد سوالات:</b> {len(test_data["questions"])} عدد
<b>⏰ زمان تخمینی:</b> {test_data["estimated_time"]}

<b>💡 هدف و مزایای تست:</b>
{test_data["outcome"]}

<b>🎯 کاربرد:</b>
{test_data["usage"]}"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 شروع تست", callback_data=f"start_package_test_{user_package_id}_{test_id}")],
        [InlineKeyboardButton("🔙 بازگشت به لیست تست‌ها", callback_data=f"view_package_{user_package_id}")],
    ]
    
    safe_edit_message(update, context, info_msg, InlineKeyboardMarkup(keyboard))

def start_package_test_callback(update: Update, context: CallbackContext):
    """Start a test from within a package"""
    query = update.callback_query
    cid = query.message.chat_id
    
    parts = query.data.split("_")
    if len(parts) >= 5:
        user_package_id = int(parts[3])
        test_id = int(parts[4])
    else:
        query.answer("❌ خطا در پردازش درخواست", show_alert=True)
        return
    
    query.answer()
    
    chat_states[cid] = {
        "stage": "ask_name_age", 
        "test_choice": str(test_id), 
        "user_package_id": user_package_id
    }
    
    send_formatted_text(update, ui.ASK_NAME_AGE)

def view_package_callback(update: Update, context: CallbackContext):
    """Show package guide and test list for an existing package"""
    query = update.callback_query
    query.answer()
    
    user_package_id = int(query.data.split("_")[-1])
    package_info = db.get_user_package(user_package_id)
    
    if not package_info:
        query.message.reply_text("❌ پکیج مورد نظر یافت نشد.")
        return
    
    package = packages.get_package_by_id(package_info["package_id"])
    if not package:
        query.message.reply_text("❌ اطلاعات پکیج یافت نشد.")
        return
    
    smart_package_guide(update, context, user_package_id, package)

def smart_package_guide(update: Update, context: CallbackContext, user_package_id: int, package: dict):
    """Show package guide and test list"""
    send_formatted_text(update, package["guide"])
    
    package_tests = db.get_package_tests(user_package_id)
    keyboard = []
    
    for pt_test in package_tests:
        test_id = pt_test["test_id"]
        if 1 <= test_id <= len(pt.all_tests["tests"]):
            test_data = pt.all_tests["tests"][test_id - 1]
            status_icon = "✅ " if pt_test["completed"] == 1 else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_icon}{test_data['test_name']}", 
                    callback_data=f"package_test_{user_package_id}_{test_id}"
                )
            ])
    
    keyboard.extend([
        [InlineKeyboardButton("🔙 بازگشت به پکیج‌ها", callback_data="purchased_packages")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_home")]
    ])
    
    send_formatted_text(update, ui.PACKAGE_TEST_SELECTION, reply_markup=InlineKeyboardMarkup(keyboard))

def purchased_packages_callback(update: Update, context: CallbackContext):
    """Show user's purchased packages"""
    query = update.callback_query
    query.answer()
    
    user_packages = db.get_user_packages(query.message.chat_id)
    
    if not user_packages:
        safe_edit_message(update, context, ui.NO_PACKAGES_PURCHASED)
        return
    
    keyboard = []
    for pkg in user_packages:
        package_info = packages.get_package_by_id(pkg["package_id"])
        if package_info:
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
    safe_edit_message(update, context, ui.PURCHASED_PACKAGES_TITLE, InlineKeyboardMarkup(keyboard))

def handle_package_test_completion(update: Update, context: CallbackContext,
                                   chat_id: int, user_package_id: int, test_id: int, info: dict):
    """Handle completion of a test within a package"""
    package_tests = db.get_package_tests(user_package_id)

    for pt_test in package_tests:
        if pt_test["test_id"] == test_id and pt_test["completed"] == 0:
            db.mark_package_test_completed(pt_test["id"])

            all_tests = db.get_package_tests(user_package_id)
            all_completed = all(test["completed"] == 1 for test in all_tests)

            if all_completed:
                pkg_info_from_db = db.get_user_package(user_package_id)
                if not pkg_info_from_db:
                    return
                
                pkg_info = packages.get_package_by_id(pkg_info_from_db["package_id"])
                if not pkg_info:
                    return

                completion_message = f"🎉 تبریک! شما تمام تست‌های پکیج «{pkg_info['name']}» را با موفقیت به پایان رساندید."
                context.bot.send_message(chat_id=chat_id, text="🔔 " + completion_message, parse_mode=ParseMode.HTML)
                
                user = db.get_user(chat_id)
                if not user:
                    return
                
                results = []
                for test in all_tests:
                    result = db.get_test_result_by_test_id(chat_id, test["test_id"])
                    if result:
                        results.append(result)

                if results:
                    send_package_report(update, context, chat_id, user["first_name"], info.get("age"), pkg_info["name"], results)
            else:
                context.bot.send_message(
                    chat_id=chat_id,
                    text="🔔 ✅ آفرین! تست شما با موفقیت ذخیره شد. برای ادامه، تست بعدی را انتخاب کنید.",
                    parse_mode=ParseMode.HTML
                )
                
                pkg_info_from_db = db.get_user_package(user_package_id)
                if pkg_info_from_db:
                    pkg_info = packages.get_package_by_id(pkg_info_from_db["package_id"])
                    if pkg_info:
                        show_package_guide_by_id(context, chat_id, user_package_id, pkg_info)
            return

def send_package_report(update: Update, context: CallbackContext, chat_id: int, user_name: str, user_age: int, package_name: str, results: list):
    """Generate and send the package report."""
    wait_message = context.bot.send_message(
        chat_id=chat_id,
        text="در حال آماده‌سازی گزارش جامع شما... لطفاً چند لحظه صبر کنید.",
    )

    try:
        report = package_ai.summarize_package_results(user_name, user_age, package_name, results)
        send_formatted_text(update, report)
    except Exception as e:
        logger.error(f"Error generating package report: {e}")
        context.bot.send_message(
            chat_id=chat_id,
            text="❌ متأسفانه در حال حاضر امکان ایجاد گزارش وجود ندارد. لطفاً بعداً دوباره تلاش کنید.",
        )
    finally:
        try:
            wait_message.delete()
        except Exception as e:
            logger.error(f"Error deleting waiting message: {e}")

def show_package_guide_by_id(context: CallbackContext, chat_id: int, user_package_id: int, package: dict):
    """Show package guide and test list by IDs"""
    from telegrambot import format_md_for_telegram
    
    guide_chunks = format_md_for_telegram(package["guide"])
    for chunk in guide_chunks:
        context.bot.send_message(chat_id=chat_id, text=chunk, parse_mode=ParseMode.HTML)
        time.sleep(0.5)
    
    package_tests = db.get_package_tests(user_package_id)
    keyboard = []
    
    for pt_test in package_tests:
        test_id = pt_test["test_id"]
        if 1 <= test_id <= len(pt.all_tests["tests"]):
            test_data = pt.all_tests["tests"][test_id - 1]
            status_icon = "✅ " if pt_test["completed"] == 1 else ""
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_icon}{test_data['test_name']}", 
                    callback_data=f"package_test_{user_package_id}_{test_id}"
                )
            ])
    
    keyboard.append([InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="psychology_tests")])
    
    selection_text = get_formatted_text(ui.PACKAGE_TEST_SELECTION)
    context.bot.send_message(
        chat_id=chat_id,
        text=selection_text,
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# =============================================================================
# USER PROFILE AND WALLET HANDLERS
# =============================================================================

def my_profile(update: Update, context: CallbackContext):
    """Show profile intro and buttons for previous results and wallet."""
    save_user_data(update)
    console.log(f"[blue]User {update.effective_chat.id} requested profile (intro)[/blue]")

    intro_text = get_formatted_text(ui.PROFILE_INTRO)
    
    keyboard = [
        [InlineKeyboardButton("👤 پروفایل روانشناسی کاربر", callback_data="show_psychological_profile")],
        [InlineKeyboardButton("📚 نتایج تست‌های قبلی", callback_data="previous_test_results"),
         InlineKeyboardButton("🧠 پکیج‌های خریداری شده", callback_data="purchased_packages")],
        [InlineKeyboardButton("💰 کیف پول من", callback_data="wallet_info"),
         InlineKeyboardButton("➕ شارژ کیف پول", callback_data="charge_wallet")],
        [InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="back_to_home")]
    ]
    
    safe_edit_message(update, context, intro_text, InlineKeyboardMarkup(keyboard))

def show_psychological_profile(update: Update, context: CallbackContext):
    """Show user's psychological profile information."""
    query = update.callback_query
    try:
        query.answer()
    except Exception:
        # If answer fails, continue — don't crash
        pass

    # Determine user id safely (callback may lack message in some edge cases)
    try:
        user_id = query.message.chat_id if (query and getattr(query, "message", None)) else update.effective_chat.id
    except Exception:
        user_id = update.effective_chat.id

    try:
        user_data = db.get_user(user_id)
    except Exception as e:
        logger.error(f"Error fetching user data for {user_id}: {e}", exc_info=True)
        # Safe fallback to friendly message
        safe_edit_message(update, context, "⚠️ خطا در بازیابی اطلاعات پروفایل. لطفاً چند لحظه بعد دوباره تلاش کنید.")
        return

    if not user_data or not user_data.get('information'):
        profile_text_raw = ui.NO_PSYCH_PROFILE
    else:
        # Format using available fields but guard against missing keys/format errors
        try:
            profile_text_raw = ui.PSYCH_PROFILE_TEMPLATE.format(
                name=user_data.get('first_name', 'کاربر'),
                progress=user_data.get('progress', 0),
                stars=user_data.get('stars', 0),
                information=user_data.get('information', '')
            )
        except Exception as e:
            logger.error(f"Error formatting profile template for {user_id}: {e}", exc_info=True)
            profile_text_raw = ui.NO_PSYCH_PROFILE

    # Optimize / convert to Telegram-safe HTML
    try:
        profile_text = optimize_for_telegram(profile_text_raw)
    except Exception as e:
        logger.error(f"Optimizer failure for profile text (user {user_id}): {e}", exc_info=True)
        profile_text = profile_text_raw

    # Enforce maximum length requirement (<= 1200 chars)
    MAX_PROFILE_LEN = 1200
    if len(profile_text) > MAX_PROFILE_LEN:
        logger.info("Truncating psychological profile for user %s to %d chars", user_id, MAX_PROFILE_LEN)
        profile_text = profile_text[: MAX_PROFILE_LEN - 3] + "..."

    keyboard = [[InlineKeyboardButton("🔙 بازگشت به پروفایل", callback_data="my_profile")]]
    safe_edit_message(update, context, profile_text, InlineKeyboardMarkup(keyboard))

def previous_test_results(update: Update, context: CallbackContext):
    """Show all previous test results."""
    cid = update.effective_chat.id
    save_user_data(update)
    console.log(f"[blue]User {cid} requested previous test results[/blue]")
    
    tests = db.get_user_tests(cid)
    if not tests:
        send_formatted_text(update, ui.NO_PREVIOUS_TESTS)
        return

    keyboard = [
        [InlineKeyboardButton(f"📝 {row['test_name']}", callback_data=f"view_result_{row['id']}")]
        for row in tests
    ]
    # added explicit back rows: back to profile and back to home
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به پروفایل", callback_data="my_profile")])
    keyboard.append([InlineKeyboardButton("🏠 بازگشت به منوی اصلی", callback_data="back_to_home")])
    
    safe_edit_message(update, context, ui.PREVIOUS_TESTS_TITLE, InlineKeyboardMarkup(keyboard))

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
        [InlineKeyboardButton("🎁 دریافت هدیه", callback_data='get_gift')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="my_profile")]
    ]
    
    safe_edit_message(update, context, message_text, InlineKeyboardMarkup(keyboard))

def wallet_info_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    return wallet(update, context)

def get_gift_callback(update: Update, context: CallbackContext):
    """Handle get gift button click"""
    query = update.callback_query
    cid = query.message.chat_id
    
    # Check if user has already received the gift
    if db.has_received_gift(cid):
        query.answer(
            text="🎁 شما قبلاً هدیه خود را دریافت کرده‌اید!",
            show_alert=True
        )
        return
    
    # Give the gift
    gift_amount = 600  # 200,000 as specified
    db.update_balance(cid, gift_amount)
    db.mark_gift_received(cid)
    
    new_balance = db.get_balance(cid)
    
    query.answer(
        text=f"🎉 تبریک! شما {gift_amount:,} تومان هدیه دریافت کردید!\nموجودی جدید: {new_balance:,} تومان",
        show_alert=True
    )
    
    # Update the wallet display
    return wallet(update, context)

def charge_wallet_callback(update: Update, context: CallbackContext):
    """Handle charge wallet button click"""
    query = update.callback_query
    query.answer()
    cid = query.message.chat_id
    
    safe_edit_message(update, context, ui.CHARGE_WALLET_INSTRUCTIONS)
    chat_states[cid] = {"stage": "await_payment_screenshot"}

def handle_payment_screenshot(update: Update, context: CallbackContext):
    """Handle incoming payment screenshot and save file."""
    cid = update.effective_chat.id
    info = chat_states.get(cid)
    
    if info and info.get("stage") == "await_payment_screenshot":
        try:
            photo = update.message.photo[-1]
            file = context.bot.getFile(photo.file_id)
            os.makedirs("payments", exist_ok=True)
            
            filepath = os.path.join("payments", f"{cid}_{int(time.time())}.jpg")
            file.download(filepath)
            db.save_payment_screenshot(cid, filepath)
            
            user = update.message.from_user
            uname = f"@{user.username}" if user.username else str(cid)
            
            for admin_id in ADMINS:
                with open(filepath, "rb") as img_f:
                    context.bot.send_photo(
                        chat_id=admin_id,
                        photo=img_f,
                        caption=f"📸 Payment screenshot from {uname}"
                    )
            
            send_formatted_text(update, ui.PAYMENT_RECEIVED)
            del chat_states[cid]
            
        except Exception as e:
            logger.error(f"Error processing payment screenshot: {e}")
            update.message.reply_text("❌ خطا در پردازش عکس پرداخت. لطفاً دوباره تلاش کنید.")
    else:
        return handle_answer(update, context)

# =============================================================================
# INDIVIDUAL TEST HANDLERS
# =============================================================================

def test_selection(update: Update, context: CallbackContext):
    """Handle test selection from the list"""
    query = update.callback_query
    query.answer()
    save_user_data(update)
    
    cid = query.message.chat_id
    choice = query.data
    test_data = pt.all_tests["tests"][int(choice)-1]
    
    chat_states[cid] = {
        "stage": "test_info",
        "test_choice": choice,
        "test_name": test_data["test_name"]
    }
    
    info_msg = f"""<b>🎯 {test_data["test_name"]}</b>

💲 <b>قیمت:</b> {test_data.get("price", 0)} هزار تومان
🧮 <b>تعداد سوالات:</b> {len(test_data["questions"])} عدد
⏰ <b>زمان تخمینی:</b> {test_data["estimated_time"]}

📝 <b>توضیحات:</b>
{test_data["outcome"]}

💡 <b>کاربرد:</b>
{test_data["usage"]}"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 شروع تست", callback_data=f"start_test_{choice}")],
        [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="charge_wallet")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="psychology_tests")],
    ]
    
    safe_edit_message(update, context, info_msg, InlineKeyboardMarkup(keyboard))

def start_test_callback(update: Update, context: CallbackContext):
    """Handle start test button click"""
    query = update.callback_query
    cid = query.message.chat_id
    
    choice = query.data.split("_")[-1]
    test_data = pt.all_tests["tests"][int(choice)-1]
    price = test_data.get("price", 0)
    balance = db.get_balance(cid)
    
    if balance < price:
        return query.answer(
            text=ui.INSUFFICIENT_BALANCE.format(balance=balance, price=price),
            show_alert=True
        )
    
    try:
        db.update_balance(cid, -price)
        new_balance = db.get_balance(cid)
        query.answer(
            f"✅ تست با موفقیت خریداری شد!\n\nمبلغ پرداختی: {price:,} تومان\nموجودی باقیمانده: {new_balance:,} تومان",
            show_alert=True
        )
        
        chat_states[cid].update({"stage": "ask_name_age", "test_choice": choice})
        send_formatted_text(update, ui.ASK_NAME_AGE)
        
    except Exception as e:
        logger.error(f"Error purchasing test: {e}")
        query.answer("❌ خطا در خرید تست. لطفاً دوباره تلاش کنید.", show_alert=True)

def view_result_callback(update: Update, context: CallbackContext):
    """Handle view result button click"""
    query = update.callback_query
    query.answer()

    record_id = int(query.data.split("_")[-1])
    result = db.get_test_result(record_id)

    if result:
        # Show stored final-analyze (concise personalized analysis) first (preferred)
        final_analyze = result.get('final_analyze') or result.get('result_text') or ""
        try:
            # send_formatted_text will format markdown -> HTML and handle callbacks
            send_formatted_text(update, final_analyze)
        except Exception:
            # fallback: plain text
            try:
                if update.callback_query:
                    update.callback_query.message.reply_text(final_analyze)
                else:
                    update.message.reply_text(final_analyze)
            except Exception:
                pass

        pdf_path = result.get('pdf_path')
        if pdf_path and os.path.exists(pdf_path):
            try:
                query.message.reply_document(
                    open(pdf_path, 'rb'),
                    filename=f"{result['test_name']}_result.pdf",
                    caption=ui.PDF_CAPTION
                )
            except Exception as e:
                logger.error(f"Failed to send PDF: {e}")

        keyboard = [[InlineKeyboardButton("🔙 بازگشت به نتایج", callback_data="previous_test_results")]]
        query.message.reply_text(
            "برای بازگشت به لیست نتایج دکمه زیر را لمس کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        query.message.reply_text(ui.RESULT_NOT_FOUND)

def handle_answer(update: Update, context: CallbackContext):
    """Handle user text messages based on current state"""
    cid = update.effective_chat.id
    text = update.message.text

    # If a higher-priority handler already processed this message (keyboard handler), skip here
    if context.user_data.get("_skip_handle_answer"):
        # clear the skip flag and do nothing
        context.user_data.pop("_skip_handle_answer", None)
        return None

    # Check for admin-specific stages first
    info = chat_states.get(cid)
    if info and info.get("stage") == "admin_charge_amount":
        return handle_admin_charge_input(update, context, text, info)
    if info and info.get("stage") == "admin_reduce_amount":
        return handle_admin_reduce_input(update, context, text, info)

    # Handle smart chat first if active
    if context.user_data.get("smart_chat_active"):
        console.log("[bold cyan]💬 Smart chat is active, processing message...[/bold cyan]")
        user_id = str(cid)
        
        # Show waiting message while processing
        console.log("[blue]📤 Sending waiting message...[/blue]")
        waiting_message = update.message.reply_text("🧠 نورون در حال فکر کردن ... 💭")
        
        try:
            console.log("[yellow]🤖 Getting smart chat agent...[/yellow]")
            agent = get_smart_chat_agent()
            
            console.log(f"[yellow]🚀 Processing message for user {user_id}...[/yellow]")
            response = smart_chat_logic(agent, user_id, text)
            
            console.log(f"[green]✅ Got response ({(len(response['raw']) if isinstance(response, dict) else len(response))} chars)[/green]" if isinstance(response, dict) else f"[green]✅ Got response ({len(response)} chars)[/green]")
            
            # Delete waiting message and send response
            console.log("[blue]🗑️ Deleting waiting message...[/blue]")
            waiting_message.delete()
            
            console.log("[blue]📤 Sending response...[/blue]")
            if isinstance(response, dict) and "refined" in response:
                send_formatted_text(update, response["refined"])
            else:
                send_formatted_text(update, response if isinstance(response, str) else str(response))
            
            console.log("[bold green]✅ Smart chat response sent successfully![/bold green]")
            
        except Exception as e:
            console.log(f"[bold red]❌ Smart chat error: {e}[/bold red]")
            logger.error(f"Smart chat error in handle_answer: {e}", exc_info=True)
            
            # Delete waiting message even if there's an error
            try:
                waiting_message.delete()
            except Exception as delete_error:
                console.log(f"[red]❌ Failed to delete waiting message: {delete_error}[/red]")
                
            console.log("[blue]📤 Sending error message...[/blue]")
            send_formatted_text(update, "متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید.")
        
        return  # End processing here

    text = text.strip()

    if not info or info["stage"] not in ["ask_name_age", "ask_user_info", "answering", "admin_charge_amount", "admin_reduce_amount", "await_payment_screenshot"]:
        return None

    if info["stage"] == "ask_name_age":
        info["name_age_response"] = text
        info["stage"] = "ask_user_info"
        console.log(f"[blue]User {cid} provided name/age: {text}[/blue]")
        send_formatted_text(update, ui.ASK_USER_INFO)
        return

    if info["stage"] == "ask_user_info":
        info["user_info_response"] = text
        console.log(f"[blue]User {cid} provided personal info: {text}[/blue]")

        wait_message = update.message.reply_text("درحال اماده سازی و شروع تست ...")

        name_age_response = info.get("name_age_response", "")
        user_name = name_age_response.split()[0] if name_age_response.split() else "User"
        age_str = "".join(filter(str.isdigit, name_age_response))
        user_age = int(age_str) if age_str.isdigit() else 0
        
        info["name"] = user_name
        info["age"] = user_age

        user_info_full = f"Name and age: {name_age_response}\nPersonal Information: {text}"

        state = pt.tele_initialize(user_name, user_age, user_info_full, info["test_choice"], chat_id=cid)
        console.log(f"[green]Initialized test for {info['name']}, age {info['age']}, test choice {info['test_choice']}, chat_id {cid}[/green]")

        if "chat_id" not in state or state["chat_id"] is None:
            state["chat_id"] = cid

        info["state"] = state
        info["stage"] = "answering"
        
        first_q = pt.tele_get_question(state)
        
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
        
        send_formatted_text(update, first_q)
        return

    # Stage is "answering"
    console.log(f"[green]User {cid} answered: {text}[/green]")
    
    console.print(Panel(
        f"[cyan]User response:[/cyan]\n[yellow]{text}[/yellow]",
        title="User Answer",
        border_style="green",
        expand=False
    ))
    
    # Select a random tip for this waiting message
    random_tip = random.choice(ui.NEURON_TIPS)
    wait_message_with_tip = ui.ANALYZING_ANSWER_WITH_TIP.format(tip=random_tip)
    wait = update.message.reply_text(wait_message_with_tip, parse_mode=ParseMode.HTML)
    console.log("[yellow]Analyzing user response...[/yellow]")
    
    res = pt.tele_process_answer(info["state"], text)
    
    if not info["state"].get("test_data") and "test_data" in globals():
        try:
            from psychology_test import test_data
            info["state"]["test_data"] = test_data
        except ImportError:
            pass
    
    table = Table(title="Full Conversation History", show_header=True, header_style="bold magenta")
    table.add_column("Role", style="cyan", no_wrap=True)
    table.add_column("Message", style="white", overflow="fold")
    for msg in info["state"]["conversation_history"]:
        table.add_row(msg.get("role", ""), msg.get("content", ""))
    console.print(table)
    
    wait.delete()

    ack_message = res.get("ack")
    next_question_message = res.get("next")

    if ack_message:
        console.print(Panel(
            f"[cyan]To User {cid}:[/cyan]\n[purple]{ack_message}[/purple]",
            title="Bot Sends (Acknowledgment/Retry)",
            border_style="magenta",
            expand=False
        ))
        send_formatted_text(update, ack_message)

    if next_question_message:
        console.print(Panel(
            f"[cyan]To User {cid}:[/cyan]\n[purple]{next_question_message}[/purple]",
            title="Bot Sends (Next Question)",
            border_style="magenta",
            expand=False
        ))
        send_formatted_text(update, next_question_message)
    elif info["state"].get("finished"):
        console.log(f"[green]Test completed for user {cid}. Generating summary...[/green]")
        
        if "chat_id" not in info["state"] or info["state"]["chat_id"] is None:
            info["state"]["chat_id"] = cid

        result_data = {"summary": None, "error": None, "images": [], "pdf_path": None}
        
        def generate_results_background():
            try:
                # Generate full summary first
                summary_content = pt.tele_summarize(info["state"])
                result_data["summary"] = summary_content

                # Always generate concise analysis
                try:
                    caption = pt.analyze_final_result(info["state"], summary_content)
                    result_data["caption"] = caption
                except Exception as cap_e:
                    console.log(f"[red]Caption generation error: {cap_e}[/red]")
                    # Provide fallback caption
                    result_data["caption"] = "تحلیل نهایی شخصیت شما در حال آماده‌سازی است..."

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

                # Always attempt image generation
                try:
                    img_prompt = pt.generate_image_prompt(summary_content)
                    images = pt.generate_images_for_prompt(
                        img_prompt, cid, "/tmp", model="midjourney",
                        num_images=1, width=512, height=512
                    )
                    if images and len(images) > 0:
                        result_data["images"] = images
                    else:
                        # Use default image if generation fails
                        default_image = "/root/blue-psychology-test/images/neuron_result.png"
                        if os.path.exists(default_image):
                            result_data["images"] = [default_image]
                except Exception as img_e:
                    console.log(f"[red]Image generation error: {img_e}[/red]")
                    # Use default image on error
                    default_image = "/root/blue-psychology-test/images/neuron_result.png"
                    if os.path.exists(default_image):
                        result_data["images"] = [default_image]

                # Always generate PDF
                try:
                    safe_name = test_name.replace(" ", "_")
                    pdf_path = f"/tmp/{safe_name}_result_{int(time.time())}.pdf"
                    generate_pdf(summary_content, info["name"], info["age"], test_name, pdf_path)
                    result_data["pdf_path"] = pdf_path
                except Exception as pdf_e:
                    console.log(f"[red]PDF generation error: {pdf_e}[/red]")
                    # Create simple text PDF as fallback
                    try:
                        from fpdf import FPDF
                        pdf = FPDF()
                        pdf.add_page()
                        pdf.add_font('Arial', '', '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf', uni=True)
                        pdf.set_font('Arial', '', 12)
                        pdf.multi_cell(0, 10, summary_content)
                        fallback_pdf = f"/tmp/result_{int(time.time())}.pdf"
                        pdf.output(fallback_pdf)
                        result_data["pdf_path"] = fallback_pdf
                    except Exception as fallback_e:
                        console.log(f"[red]Fallback PDF creation failed: {fallback_e}[/red]")

                # Save results to database
                try:
                    save_user_data(update)
                    db.save_test_result(
                        cid, 
                        test_name, 
                        summary_content, 
                        result_data.get("pdf_path", ""),
                        result_data.get("caption", "")
                    )
                    console.log(f"[blue]Saved test result for user {cid}[/blue]")
                except Exception as db_e:
                    console.log(f"[red]Database save error: {db_e}[/red]")

            except Exception as e:
                console.log(f"[red]Error in background result generation: {e}[/red]")
                result_data["error"] = str(e)

        background_thread = threading.Thread(target=generate_results_background, daemon=True)
        background_thread.start()
        
        current_message = None
        for i, msg_text in enumerate(ui.PROCESSING_MESSAGES):
            # Delete previous message if it exists
            if current_message:
                try:
                    current_message.delete()
                except Exception as e:
                    logger.error(f"Error deleting previous waiting message: {e}")
            
            # Send new message
            current_message = update.message.reply_text(msg_text)
            
            # Wait between messages
            time.sleep(3)
        
        # Wait for background thread to complete (with timeout)
        background_thread.join()  # wait until the background processing completes
        
        # Delete the final waiting message
        if current_message:
            try:
                current_message.delete()
            except Exception as e:
                logger.error(f"Error deleting final waiting message: {e}")
                
        # Send results in correct order (image -> analysis -> PDF)
        try:
            context.user_data["result_image"] = result_data["images"][0] if result_data.get("images") else None
            context.user_data["result_pdf"] = result_data.get("pdf_path")
            context.user_data["result_caption"] = result_data.get("caption")
            
            # Use unified sender which will handle all components
            from telegrambot import send_styled_test_result
            test_name = info.get("test_name", "تست روانشناسی")
            success = send_styled_test_result(update, context, test_name, result_data.get("summary", ""))
            
            if not success:
                # On failure, try sending components individually
                if context.user_data.get("result_image"):
                    try:
                        update.message.reply_photo(
                            photo=open(context.user_data["result_image"], 'rb'),
                            caption=ui.IMAGE_GENERATED_CAPTION
                        )
                    except Exception:
                        pass
                
                if context.user_data.get("result_caption"):
                    try:
                        update.message.reply_text(context.user_data["result_caption"])
                    except Exception:
                        pass
                
                if context.user_data.get("result_pdf"):
                    try:
                        update.message.reply_document(
                            document=open(context.user_data["result_pdf"], 'rb'),
                            caption=ui.PDF_REPORT_CAPTION.format(test_name=test_name)
                        )
                    except Exception:
                        pass

        finally:
            # Clean up context data
            context.user_data.pop("result_image", None)
            context.user_data.pop("result_pdf", None)
            context.user_data.pop("result_caption", None)

        # Handle package completion and cleanup
        if cid in chat_states:
            info = chat_states.get(cid)
            if info and "user_package_id" in info:
                handle_package_test_completion(update, context, cid, info["user_package_id"], int(info["test_choice"]), info)
            
            # AI Profile Updater - run in background and only notify user on success with a plain message
            try:
                console.log(f"[bold blue]🚀 Scheduling AI profile update for user {cid}...[/bold blue]")
                summary_for_profile = result_data.get("summary", "")

                def _profile_update_task(bot, chat_id, summary_text):
                    try:
                        ai_utils.update_user_profile_with_ai(chat_id, summary_text)
                        # send single success message (no callback_query popup, no interim loading text)
                        try:
                            bot.send_message(
                                chat_id=chat_id,
                                text="✅ پروفایل هوش مصنوعی شما با موفقیت به‌روزرسانی شد."
                            )
                        except Exception as send_err:
                            logger.error(f"Failed to send profile update success message to {chat_id}: {send_err}")
                    except Exception as profile_err:
                        # Log the error; do not show callback popups or interim loading messages per request.
                        logger.error(f"AI profile update failed for {chat_id}: {profile_err}", exc_info=True)

                threading.Thread(
                    target=_profile_update_task,
                    args=(context.bot, cid, summary_for_profile),
                    daemon=True
                ).start()

                console.log(f"[bold green]✅ AI profile update scheduled for user {cid}.[/bold green]")
            except Exception as e:
                console.log(f"[bold red]❌ Failed to schedule AI profile update for user {cid}: {e}[/bold red]")
                logger.error(f"Failed to schedule AI profile update for user {cid}: {e}", exc_info=True)

            del chat_states[cid]

# Add new callback handler for profile update status
def show_profile_update_status(update: Update, context: CallbackContext):
    """Show profile update status via callback query alert"""
    query = update.callback_query
    query.answer(
        text="پروفایل هوش مصنوعی شما با موفقیت به‌روزرسانی شد! 🎉",
        show_alert=True
    )
    # Remove the inline keyboard after showing status
    query.message.edit_text(
        "پروفایل شما با موفقیت به‌روزرسانی شد.",
        reply_markup=None
    )

# =============================================================================
# ADMIN HANDLERS
# =============================================================================

@admin_only
def admin_panel(update: Update, context: CallbackContext):
    """Admin main menu"""
    keyboard = [[InlineKeyboardButton("📋 Users", callback_data="admin_users")]]
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
        [InlineKeyboardButton("💬 Messages", callback_data=f"admin_user_{chat_id}_messages"),
         InlineKeyboardButton("➕ Charge Wallet", callback_data=f"admin_user_{chat_id}_charge"),
         InlineKeyboardButton("➖ Reduce Wallet", callback_data=f"admin_user_{chat_id}_reduce")]
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
    target = query.data.split("_")[2]
    chat_states[admin_id] = {"stage":"admin_charge_amount","target":int(target)}
    query.message.reply_text(ui.ADMIN_CHARGE_PROMPT.format(user_id=target))

@admin_only
def admin_reduce_prompt(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    admin_id = query.message.chat_id
    target = query.data.split("_")[2]
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
            return

        db.update_balance(target_user_id, amount)
        new_balance = db.get_balance(target_user_id)
        
        update.message.reply_text(
            ui.ADMIN_CHARGE_SUCCESS.format(
                user_id=target_user_id, amount=amount, balance=new_balance
            )
        )
        
        try:
            context.bot.send_message(
                chat_id=target_user_id,
                text=f"🎉 کیف پول شما به مبلغ {amount} هزار تومان شارژ شد.\nموجودی جدید: {new_balance} هزار تومان"
            )
        except Exception as e:
            console.log(f"Failed to notify user {target_user_id} about charge: {e}")
            update.message.reply_text(f"⚠️ اخطار: موفق به اطلاع‌رسانی به کاربر {target_user_id} نشدیم.")

        del chat_states[admin_id]

    except ValueError:
        update.message.reply_text(ui.ADMIN_INVALID_AMOUNT)
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
            return

        current_balance = db.get_balance(target_user_id)
        if amount > current_balance:
            update.message.reply_text(
                ui.ADMIN_AMOUNT_EXCEEDS_BALANCE.format(amount=amount, balance=current_balance)
            )
            return

        db.update_balance(target_user_id, -amount)
        new_balance = db.get_balance(target_user_id)
        
        update.message.reply_text(
            ui.ADMIN_REDUCE_SUCCESS.format(
                user_id=target_user_id, amount=amount, balance=new_balance
            )
        )
        
        try:
            context.bot.send_message(
                chat_id=target_user_id,
                text=f"ℹ️ مبلغ {amount} هزار تومان از کیف پول شما کسر شد.\nموجودی جدید: {new_balance} هزار تومان"
            )
        except Exception as e:
            console.log(f"Failed to notify user {target_user_id} about balance reduction: {e}")
            update.message.reply_text(f"⚠️ اخطار: موفق به اطلاع‌رسانی به کاربر {target_user_id} نشدیم.")
            
        del chat_states[admin_id]

    except ValueError:
        update.message.reply_text(ui.ADMIN_INVALID_AMOUNT)
        update.message.reply_text(ui.ADMIN_INVALID_AMOUNT)
