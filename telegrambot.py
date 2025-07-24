"""
Main Telegram bot module for Blue Psychology Test Bot.
This module initializes and runs the Telegram bot.
"""
import logging
import re
import time
import os
import threading
from functools import wraps
from telegram import Update, BotCommand, ParseMode
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler,
    MessageHandler, Filters, CallbackContext
)
from rich.logging import RichHandler
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

import db
import telegram_ui as ui
import telegram_handlers as handlers

# Setup rich console and logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)
logger = logging.getLogger(__name__)

# Import chat_states and ADMINS from utils.py
from utils import chat_states, ADMINS

# --------------------------
# G4F API Server Bootstrap
# --------------------------
try:
    from g4f.api import run_api
except ImportError:
    run_api = None

def start_g4f_server():
    """Start G4F API server on port 15207"""
    if run_api:
        def _start_g4f():
            logger.info("[bold green]Starting G4F API server on http://localhost:15207/v1 ...[/bold green]")
            try:
                run_api(bind="0.0.0.0:15207")
            except Exception as e:
                logger.error(f"[bold red]Failed to start G4F API server: {e}[/bold red]")
        
        threading.Thread(target=_start_g4f, daemon=True, name="G4F-API-Thread").start()
        logger.info("[bold blue]G4F API server thread started[/bold blue]")
    else:
        logger.warning("[bold yellow]g4f.api module not found. Install the 'g4f' package to run the local API server.[/bold yellow]")

def _parse_table_row(line: str) -> list[str]:
    """Helper to parse a Markdown table row into cells."""
    if not line.strip().startswith('|'):
        return []
    return [cell.strip() for cell in line.strip().strip('|').split('|')]

def format_md_for_telegram(md_text: str) -> list:
    """
    Convert markdown to Telegram-compatible HTML and split into chunks if needed.
    Returns a list of message chunks ready to be sent.
    """
    # --- Stage 1: Pre-processing and Table Conversion ---
    lines = md_text.split('\n')
    processed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Try to detect a Markdown table
        # A table has: | Header | ... |
        #              | ---    | ... |
        #              | Data   | ... |
        
        header_cells = _parse_table_row(line)
        is_header_row = bool(header_cells) and not all('---' in cell or cell.strip() == '' for cell in header_cells)

        if is_header_row and i + 1 < len(lines):
            next_line = lines[i+1]
            separator_cells = _parse_table_row(next_line)
            is_separator_row = bool(separator_cells) and all('---' in cell or cell.strip().replace(':','').replace('-','').isspace() for cell in separator_cells)

            if is_separator_row:
                # Found a table header and separator
                table_html_lines = []
                
                # Process header
                table_html_lines.append("<b>" + "</b> | <b>".join(header_cells) + "</b>")
                
                # Optional: Add a visual separator line (can be simple or more complex)
                # table_html_lines.append("⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯")

                i += 2 # Move past header and separator
                
                # Process data rows
                while i < len(lines):
                    data_line_candidate = lines[i]
                    data_cells = _parse_table_row(data_line_candidate)
                    if data_cells: # It's a table data row
                        # Using <code> for cells for potential monospacing.
                        # If alignment is poor, replace <code>...</code> with just the cell content.
                        table_html_lines.append("<code>" + "</code> | <code>".join(data_cells) + "</code>")
                        i += 1
                    else: # Not a table row, table ends
                        break
                
                processed_lines.extend(table_html_lines)
                processed_lines.append("") # Add a blank line after the table for spacing
                continue # Continue to the next line in the original lines
        
        processed_lines.append(line)
        i += 1
        
    html = "\n".join(processed_lines)

    # --- Stage 2: Standard Markdown to HTML Conversions ---
    
    # Replace markdown headers with HTML headers - improved regex
    html = re.sub(r'^#\s*([^#\n]+?)\s*#*\s*$', r'<b>🔶 \1</b>', html, flags=re.MULTILINE)  # H1
    html = re.sub(r'^##\s*([^#\n]+?)\s*#*\s*$', r'<b>🔷 \1</b>', html, flags=re.MULTILINE) # H2
    html = re.sub(r'^###\s*([^#\n]+?)\s*#*\s*$', r'<b>🔹 \1</b>', html, flags=re.MULTILINE) # H3
    
    # Replace markdown bold/italic with HTML tags
    html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html) # Bold
    html = re.sub(r'__(.*?)__', r'<b>\1</b>', html)   # Bold (alternative)
    # Italic: ensure it doesn't conflict with internal underscores in words or links
    html = re.sub(r'(?<!\w)\*(.*?)\*(?!\w)', r'<i>\1</i>', html)   # Italic *
    html = re.sub(r'(?<!\w)_(.*?)_(?!\w)', r'<i>\1</i>', html)     # Italic _

    # Replace markdown code blocks and inline code
    html = re.sub(r'```(?:\w*\n)?(.*?)\n?```', r'<pre>\1</pre>', html, flags=re.DOTALL) # Code blocks
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html) # Inline code
    
    # Improve list rendering
    # Unordered lists
    html = re.sub(r'^\s*-\s+(.*?)(?:\n|$)', r'• \1\n', html, flags=re.MULTILINE)
    html = re.sub(r'^\s*\*\s+(.*?)(?:\n|$)', r'• \1\n', html, flags=re.MULTILINE) # Support * for lists
    
    # Numbered lists - Persian RTL formatting with numbers at the end
    def format_numbered_item(match):
        number = match.group(1)  # e.g., "1."
        content = match.group(2).strip()  # the text content
        # Convert to Persian numbers and format for RTL
        persian_nums = {'1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', 
                       '6': '۶', '7': '۷', '8': '۸', '9': '۹', '0': '۰'}
        persian_number = ''.join(persian_nums.get(char, char) for char in number.replace('.', ''))
        return f'{persian_number}. {content}\n'
    
    html = re.sub(r'^\s*(\d+\.)\s+(.*?)(?:\n|$)', format_numbered_item, html, flags=re.MULTILINE)
    
    # Handle indented/nested lists with extra spacing
    html = re.sub(r'^\s{2,4}([-*])\s+(.*?)(?:\n|$)', r'  ◦ \2\n', html, flags=re.MULTILINE)
    
    def format_nested_numbered_item(match):
        number = match.group(1)  # e.g., "1."
        content = match.group(2).strip()  # the text content
        # Convert to Persian numbers for nested items too
        persian_nums = {'1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', 
                       '6': '۶', '7': '۷', '8': '۸', '9': '۹', '0': '۰'}
        persian_number = ''.join(persian_nums.get(char, char) for char in number.replace('.', ''))
        return f'{persian_number}. {content}\n'
    
    html = re.sub(r'^\s{2,4}(\d+\.)\s+(.*?)(?:\n|$)', format_nested_numbered_item, html, flags=re.MULTILINE)
    
    # Replace markdown horizontal rules with a more visible separator
    html = re.sub(r'^\s*[-*_]{3,}\s*$', r'⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n', html, flags=re.MULTILINE)
    
    # Ensure headers have proper spacing before and after
    html = re.sub(r'(<b>.*?</b>)(?!\n\n|\n<pre>)', r'\1\n', html) # Add newline after header if not followed by double or pre
    html = re.sub(r'\n\n(<b>.*?</b>)', r'\n\1', html) # Reduce excessive newlines before header
    
    # Replace multiple newlines with double newlines to maintain paragraph spacing
    html = re.sub(r'\n{3,}', '\n\n', html)
    
    # Trim leading/trailing whitespace from the whole HTML
    html = html.strip()

    # --- Stage 3: Splitting into Chunks ---
    MAX_LENGTH = 4000  # slightly less than 4096 to be safe
    chunks = []
    
    if len(html) <= MAX_LENGTH:
        chunks.append(html)
    else:
        # Try to split at paragraph breaks first (double newlines)
        # Also consider <pre> blocks as unsplittable units if possible
        # For simplicity, we'll stick to paragraph splitting primarily.
        
        # Split by a custom delimiter that respects <pre> blocks
        split_points = []
        last_split = 0
        in_pre = False
        for m in re.finditer(r'(<pre>.*?</pre>|\n\n)', html, re.DOTALL | re.IGNORECASE):
            if m.group(0) == '\n\n' and not in_pre:
                split_points.append(html[last_split:m.start()])
                last_split = m.end()
            elif m.group(0).lower().startswith('<pre>'):
                in_pre = True
            elif m.group(0).lower().endswith('</pre>'):
                in_pre = False
        split_points.append(html[last_split:])
        
        paragraphs = [p for p in split_points if p.strip()]

        current_chunk = ""
        for para_idx, para in enumerate(paragraphs):
            # Check if adding the current paragraph (plus separator) exceeds max length
            if len(current_chunk) + len(para) + (2 if current_chunk else 0) <= MAX_LENGTH:
                if current_chunk:
                    current_chunk += '\n\n'
                current_chunk += para
            else:
                # If current_chunk is not empty, store it
                if current_chunk:
                    chunks.append(current_chunk)
                
                # If the paragraph itself is too long, split it by lines or sentences
                if len(para) > MAX_LENGTH:
                    # Simple split by lines for very long paragraphs
                    lines_in_para = para.split('\n')
                    temp_para_chunk = ""
                    for line_idx, line_in_para in enumerate(lines_in_para):
                        if len(temp_para_chunk) + len(line_in_para) + (1 if temp_para_chunk else 0) <= MAX_LENGTH:
                            if temp_para_chunk:
                                temp_para_chunk += '\n'
                            temp_para_chunk += line_in_para
                        else:
                            if temp_para_chunk: 
                                chunks.append(temp_para_chunk)
                            temp_para_chunk = line_in_para 
                    if temp_para_chunk: 
                        chunks.append(temp_para_chunk)
                    current_chunk = "" 
                else:
                    current_chunk = para 
        
        if current_chunk:
            chunks.append(current_chunk)

    # Clean up empty chunks that might result from splitting
    chunks = [chunk for chunk in chunks if chunk.strip()]

    # Add "Continued..." at the end of each chunk except the last one
    if len(chunks) > 1:
        for i in range(len(chunks) - 1):
            chunks[i] += ui.RESULT_CHUNK_CONTINUED
    
    # Add part numbers if multiple chunks
    if len(chunks) > 1:
        for i in range(len(chunks)):
            chunks[i] = ui.RESULT_CHUNK_PART.format(part_num=i+1, total_parts=len(chunks)) + chunks[i]
    
    return chunks if chunks else ["(محتوایی برای نمایش وجود ندارد)"]

def format_caption_for_telegram(test_name: str, summary_content: str) -> str:
    """
    Format test result as a caption for an image with Telegram's caption length limits.
    Captions are limited to 1024 characters.
    """
    MAX_CAPTION_LENGTH = 1000  # Leave some buffer for safety
    
    # Create a nice header
    header = f"<b>🎯 نتایج تست {test_name}</b>\n\n"
    
    # Format the summary content using our standard function but take only first chunk
    message_chunks = format_md_for_telegram(summary_content)
    main_content = message_chunks[0] if message_chunks else summary_content
    
    # Calculate available space for content
    available_space = MAX_CAPTION_LENGTH - len(header) - 50  # Buffer for footer
    
    # Truncate content if too long
    if len(main_content) > available_space:
        main_content = main_content[:available_space - 3] + "..."
    
    # Add footer if content was truncated
    footer = ""
    if len(message_chunks) > 1 or len(summary_content) > available_space:
        footer = "\n\n📄 نتایج کامل در فایل PDF ارسال شده موجود است."
    
    full_caption = header + main_content + footer
    
    # Final safety check
    if len(full_caption) > MAX_CAPTION_LENGTH:
        # More aggressive truncation
        content_limit = MAX_CAPTION_LENGTH - len(header) - len(footer) - 10
        truncated_content = main_content[:content_limit] + "..."
        full_caption = header + truncated_content + footer
    
    return full_caption

def send_styled_test_result(update: Update, context: CallbackContext, test_name: str, summary_content: str):
    """Send formatted test result to user with proper styling using HTML."""
    try:
        # Create a nice header with emoji decoration
        header = ui.RESULT_HTML_HEADER.format(test_name=test_name)
        
        # Format the summary content using the improved function
        message_chunks = format_md_for_telegram(summary_content)
        
        # Determine the reply method (message or query callback)
        reply_method = update.message.reply_text if update.message else update.callback_query.message.reply_text

        # Send each chunk with the header for the first chunk
        for i, chunk in enumerate(message_chunks):
            full_message = chunk
            if i == 0:
                full_message = header + chunk
            
            reply_method(
                full_message,
                parse_mode=ParseMode.HTML
            )
            
            # Add a small delay between messages to maintain order and avoid rate limits
            time.sleep(0.7) # Increased delay slightly
            
        return True
    except Exception as e:
        logger.error(f"[bold red]Error sending formatted HTML results: {e}[/bold red]")
        # Fallback to plain text if HTML parsing fails, try to send to query or message
        fallback_reply_method = update.message.reply_text if update.message else update.callback_query.message.reply_text
        try:
            fallback_reply_method(
                ui.RESULT_FALLBACK_TEXT.format(
                    test_name=test_name,
                    summary=summary_content[:4000] + ("..." if len(summary_content) > 4000 else "")
                )
            )
        except Exception as fallback_e:
            logger.error(f"[bold red]Fallback send also failed: {fallback_e}[/bold red]")
        return False

def main():
    # Clear module cache to avoid duplicate handlers
    import sys
    for module in list(sys.modules.keys()):
        if module.startswith('handlers') and module != 'telegram_handlers':
            del sys.modules[module]
    
    logger.info("[bold green]Starting Blue PTsychology Test Bot[/bold green]")
    
    # Start G4F server before initializing the bot
    start_g4f_server()
    
    TOKEN = "7810952815:AAETk8FaU6rtq8_ICAJuwLGLJA8ZcMILrMM"
    db.init_db()  # <-- initialize database tables
    logger.info("[bold blue]Database initialized[/bold blue]")
    
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # --- Command handlers ---
    dp.add_handler(CommandHandler("start", handlers.start))
    dp.add_handler(CommandHandler("psychology_tests", handlers.psychology_tests))
    dp.add_handler(CommandHandler("my_profile", handlers.my_profile))
    dp.add_handler(CommandHandler("wallet", handlers.wallet))
    dp.add_handler(CommandHandler("admin", handlers.admin_panel))

    # --- Persistent keyboard (text) handlers ---
    # Create a single message handler for all persistent keyboard buttons
    def handle_keyboard_buttons(update: Update, context: CallbackContext):
        text = update.message.text
        if text == "📋 تست‌های روانشناسی":
            return handlers.psychology_tests(update, context)
        elif text == "🧠 پکیج‌های هوشمند":
            return handlers.smart_packages(update, context)
        elif text == "🧑‍💼 پروفایل من":
            return handlers.my_profile(update, context)
        elif text == "💰 کیف پول من":
            return handlers.wallet(update, context)
        elif text == "💬 جلسه هوشمند درمانی با هوش مصنوعی":
            return handlers.smart_therapy_session(update, context)
    
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_keyboard_buttons), group=0)

    # Debug callback handler to log all callback queries
    def debug_callback_handler(update: Update, context: CallbackContext):
        query = update.callback_query
        logger.info(f"[DEBUG] Callback received: {query.data} from user {query.from_user.id}")
        return  # Let other handlers process it
    
    # Add debug handler first (will be called for all callbacks)
    dp.add_handler(CallbackQueryHandler(debug_callback_handler), group=0)
    
    # --- Inline keyboard (callback) handlers for main menu ---
    dp.add_handler(CallbackQueryHandler(handlers.show_tests_cb, pattern="^psychology_tests$"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.show_profile_cb, pattern="^my_profile$"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.previous_test_results_cb, pattern="^previous_test_results$"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.purchased_packages_callback, pattern="^purchased_packages$"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.wallet_info_callback, pattern="^wallet_info$"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.charge_wallet_callback, pattern="^charge_wallet$"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.smart_packages, pattern="^smart_packages$"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.smart_therapy_session, pattern="^smart_therapy$"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.smart_package_selected, pattern="^smart_pack_"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.back_to_home_cb, pattern="^back_to_home$"), group=1)
    
    # Package-related callback handlers - order matters!
    dp.add_handler(CallbackQueryHandler(handlers.start_package_test_callback, pattern="^start_package_test_"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.start_package_callback, pattern="^start_package_[^_]*$"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.package_test_selected, pattern="^package_test_"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.view_package_callback, pattern="^view_package_"), group=1)
    
    # Admin handlers
    dp.add_handler(CallbackQueryHandler(handlers.admin_users_list, pattern="^admin_users$"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.admin_user_options, pattern=r"^admin_user_\d+$"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.admin_charge_prompt, pattern=r"^admin_user_\d+_charge$"), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.admin_reduce_prompt, pattern=r"^admin_user_\d+_reduce$"), group=1)
    
    # Test handlers
    dp.add_handler(CallbackQueryHandler(handlers.view_result_callback, pattern='^view_result_'), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.test_selection, pattern=r'^[0-9]+$'), group=1)
    dp.add_handler(CallbackQueryHandler(handlers.start_test_callback, pattern=r"^start_test_\d+$"), group=1)

    # Add text message handler for the conversation flow (name/age/answers)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handlers.handle_answer), group=1)
    
    # Handle photo uploads (for payment screenshots)
    dp.add_handler(MessageHandler(Filters.photo, handlers.handle_payment_screenshot), group=1)
    
    # register bot commands - updated list
    updater.bot.set_my_commands([
        BotCommand("start", "🚀 شروع ربات و انتخاب تست"),
        BotCommand("psychology_tests", "📋 نمایش تست‌های روانشناسی"),
        BotCommand("my_profile", "🕵️ مشاهده نتایج تست‌های قبلی"),
        BotCommand("wallet", "💰 کیف پول من"),
        BotCommand("admin", "🛠️ پنل مدیریت")
    ])

    logger.info("[bold green]Bot is now running. Press Ctrl+C to stop.[bold green]")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    console.print(Panel(
        "[bold green]Blue Psychology Test Bot[/bold green]\n"
        "[cyan]A sophisticated AI-powered psychology test platform[/cyan]",
        border_style="bright_blue"
    ))
    main()