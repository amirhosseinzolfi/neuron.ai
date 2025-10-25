"""
Main Telegram bot module for Blue Psychology Test Bot.
This module initializes and runs the Telegram bot.
"""
import logging
import re
import time
import os
import threading
import subprocess, sys, shutil
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
from utils import chat_states, ADMINS

# Setup logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)
logger = logging.getLogger(__name__)

# G4F API Server Bootstrap
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
    """Convert markdown to Telegram-compatible HTML and split into chunks if needed."""
    # Stage 1: Table conversion
    lines = md_text.split('\n')
    processed_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        header_cells = _parse_table_row(line)
        is_header_row = bool(header_cells) and not all('---' in cell or cell.strip() == '' for cell in header_cells)

        if is_header_row and i + 1 < len(lines):
            next_line = lines[i+1]
            separator_cells = _parse_table_row(next_line)
            is_separator_row = bool(separator_cells) and all('---' in cell or cell.strip().replace(':','').replace('-','').isspace() for cell in separator_cells)

            if is_separator_row:
                table_html_lines = ["<b>" + "</b> | <b>".join(header_cells) + "</b>"]
                i += 2
                
                while i < len(lines):
                    data_line_candidate = lines[i]
                    data_cells = _parse_table_row(data_line_candidate)
                    if data_cells:
                        table_html_lines.append("<code>" + "</code> | <code>".join(data_cells) + "</code>")
                        i += 1
                    else:
                        break
                
                processed_lines.extend(table_html_lines)
                processed_lines.append("")
                continue
        
        processed_lines.append(line)
        i += 1
        
    html = "\n".join(processed_lines)

    # Stage 2: Markdown to HTML conversions
    conversions = [
        (r'^#\s*([^#\n]+?)\s*#*\s*$', r'<b>🔶 \1</b>'),  # H1يال
        (r'^##\s*([^#\n]+?)\s*#*\s*$', r'<b>🔷 \1</b>'), # H2
        (r'^###\s*([^#\n]+?)\s*#*\s*$', r'<b>🔹 \1</b>'), # H3
        (r'\*\*(.*?)\*\*', r'<b>\1</b>'),  # Bold
        (r'__(.*?)__', r'<b>\1</b>'),      # Bold alternative
        (r'(?<!\w)\*(.*?)\*(?!\w)', r'<i>\1</i>'),  # Italic *
        (r'(?<!\w)_(.*?)_(?!\w)', r'<i>\1</i>'),    # Italic _
        (r'```(?:\w*\n)?(.*?)\n?```', r'<pre>\1</pre>'),  # Code blocks
        (r'`(.*?)`', r'<code>\1</code>'),  # Inline code
        (r'^\s*-\s+(.*?)(?:\n|$)', r'• \1\n'),  # Unordered lists
        (r'^\s*\*\s+(.*?)(?:\n|$)', r'• \1\n'), # Unordered lists *
        (r'^\s{2,4}([-*])\s+(.*?)(?:\n|$)', r'  ◦ \2\n'),  # Nested lists
        (r'^\s*[-*_]{3,}\s*$', r'⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n'),  # HR
    ]
    
    for pattern, replacement in conversions:
        html = re.sub(pattern, replacement, html, flags=re.MULTILINE | re.DOTALL)
    
    # Persian numbered lists
    def format_numbered_item(match):
        number = match.group(1)
        content = match.group(2).strip()
        persian_nums = {'1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', 
                       '6': '۶', '7': '۷', '8': '۸', '9': '۹', '0': '۰'}
        persian_number = ''.join(persian_nums.get(char, char) for char in number.replace('.', ''))
        return f'{persian_number}. {content}\n'
    
    html = re.sub(r'^\s*(\d+\.)\s+(.*?)(?:\n|$)', format_numbered_item, html, flags=re.MULTILINE)
    html = re.sub(r'^\s{2,4}(\d+\.)\s+(.*?)(?:\n|$)', format_numbered_item, html, flags=re.MULTILINE)
    
    # Clean up spacing
    html = re.sub(r'(<b>.*?</b>)(?!\n\n|\n<pre>)', r'\1\n', html)
    html = re.sub(r'\n\n(<b>.*?</b>)', r'\n\1', html)
    html = re.sub(r'\n{3,}', '\n\n', html).strip()

    # Stage 3: Split into chunks
    MAX_LENGTH = 4000
    if len(html) <= MAX_LENGTH:
        return [html]
    
    # Split by paragraphs
    paragraphs = [p.strip() for p in re.split(r'\n\n', html) if p.strip()]
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= MAX_LENGTH:
            current_chunk += ('\n\n' if current_chunk else '') + para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            
            # Handle oversized paragraphs
            if len(para) > MAX_LENGTH:
                lines = para.split('\n')
                temp_chunk = ""
                for line in lines:
                    if len(temp_chunk) + len(line) + 1 <= MAX_LENGTH:
                        temp_chunk += ('\n' if temp_chunk else '') + line
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk)
                        temp_chunk = line
                if temp_chunk:
                    chunks.append(temp_chunk)
                current_chunk = ""
            else:
                current_chunk = para
    
    if current_chunk:
        chunks.append(current_chunk)
    # Add continuation markers and part numbers
    if len(chunks) > 1:
        for i in range(len(chunks) - 1):
            chunks[i] += ui.RESULT_CHUNK_CONTINUED
        for i in range(len(chunks)):
            chunks[i] = ui.RESULT_CHUNK_PART.format(part_num=i+1, total_parts=len(chunks)) + chunks[i]
    
    return chunks if chunks else ["(محتوایی برای نمایش وجود ندارد)"]

def format_caption_for_telegram(test_name: str, summary_content: str) -> str:
    """Format test result as a caption for an image with Telegram's caption length limits."""
    # Use shared UI constant for caption limits
    MAX_CAPTION_LENGTH = getattr(ui, "MAX_CAPTION_LENGTH", 1000)
    header = f"<b>🎯 نتایج تست {test_name}</b>\n\n"

    # Reuse the first chunk as the main caption content (already HTML-safe)
    message_chunks = format_md_for_telegram(summary_content)
    main_content = message_chunks[0] if message_chunks else summary_content

    footer = ""
    # If we have more content than fits, hint to user that full report is in the PDF
    if len(message_chunks) > 1 or len(summary_content) > (MAX_CAPTION_LENGTH - len(header) - 50):
        footer = "\n\n📄 نتایج کامل در فایل PDF ارسال شده موجود است."

    # Reserve some space for header/footer and safety margin
    available_space = MAX_CAPTION_LENGTH - len(header) - len(footer) - 8
    if len(main_content) > available_space:
        main_content = main_content[:available_space - 3] + "..."

    full_caption = header + main_content + footer
    # Final safety clamp
    if len(full_caption) > MAX_CAPTION_LENGTH:
        full_caption = full_caption[:MAX_CAPTION_LENGTH - 3] + "..."

    return full_caption

def send_styled_test_result(update: Update, context: CallbackContext, test_name: str, summary_content: str):
    """Send formatted test result with separate image, analysis and PDF."""
    try:
        # Determine chat id
        chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
        
        # Get paths and required data from context
        image_path = context.user_data.get("result_image")
        pdf_path = context.user_data.get("result_pdf")
        # Fallback: use summary_content if result_caption is empty
        analysis_text = context.user_data.get("result_caption") or summary_content

        # 1. First send the AI-generated personality image with simple caption
        if image_path and os.path.exists(image_path):
            send_media_with_caption(
                context, 
                chat_id,
                image_path,
                ui.IMAGE_GENERATED_CAPTION,
                media_type="photo"
            )
            time.sleep(0.7)
        
        # 2. Send the ANALYSIS text (not raw summary) in chunks
        header = ui.ANALYSIS_HEADER.format(test_name=test_name)
        message_chunks = format_md_for_telegram(analysis_text)  # Use analysis instead of summary
        for i, chunk in enumerate(message_chunks):
            full_message = (header + chunk) if i == 0 else chunk
            context.bot.send_message(
                chat_id=chat_id,
                text=full_message,
                parse_mode=ParseMode.HTML
            )
            time.sleep(0.7)
        
        # 3. Finally send PDF (which contains the full raw summary)
        if pdf_path and os.path.exists(pdf_path):
            send_media_with_caption(
                context,
                chat_id,
                pdf_path,
                ui.PDF_REPORT_CAPTION.format(test_name=test_name),
                media_type="document"
            )
        
        return True

    except Exception as e:
        logger.error(f"[bold red]Error sending formatted results: {e}[/bold red]")
        try:
            # Even in error case, prefer showing analysis if available
            fallback_text = context.user_data.get("result_caption") or summary_content
            context.bot.send_message(
                chat_id=chat_id,
                text=ui.RESULT_FALLBACK_TEXT.format(
                    test_name=test_name,
                    summary=fallback_text[:4000000] + ("..." if len(fallback_text) > 4000000 else "")
                )
            )
        except Exception as fallback_e:
            logger.error(f"[bold red]Fallback send also failed: {fallback_e}[/bold red]")
        return False

def send_alert_message(context, chat_id: int, message: str):
    """Send a message formatted to look like an alert notification"""
    try:
        context.bot.send_message(chat_id=chat_id, text=f"🔔 {message}", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error sending alert message: {e}")

def send_media_with_caption(context: CallbackContext, chat_id: int, media_path: str, caption: str, media_type: str = "auto"):
    """Send media file with caption, with proper error handling."""
    try:
        if not os.path.exists(media_path):
            logger.warning(f"Media file not found: {media_path}")
            context.bot.send_message(chat_id=chat_id, text=caption, parse_mode=ParseMode.HTML)
            return False
            
        # Auto-detect media type
        if media_type == "auto":
            ext = os.path.splitext(media_path)[1].lower()
            type_map = {
                '.gif': 'animation',
                '.mp4': 'video', '.mov': 'video', '.avi': 'video',
                '.jpg': 'photo', '.jpeg': 'photo', '.png': 'photo', '.webp': 'photo'
            }
            media_type = type_map.get(ext, 'document')
        
        with open(media_path, 'rb') as media_file:
            send_methods = {
                'animation': context.bot.send_animation,
                'video': context.bot.send_video,
                'photo': context.bot.send_photo,
                'document': context.bot.send_document
            }
            
            method = send_methods.get(media_type, context.bot.send_document)
            kwargs = {'chat_id': chat_id, 'caption': caption, 'parse_mode': ParseMode.HTML}
            
            if media_type == 'animation':
                kwargs['animation'] = media_file
            elif media_type == 'video':
                kwargs['video'] = media_file
            elif media_type == 'photo':
                kwargs['photo'] = media_file
            else:
                kwargs['document'] = media_file
                
            method(**kwargs)
        return True
    except Exception as e:
        logger.error(f"Error sending media {media_path}: {e}")
        context.bot.send_message(chat_id=chat_id, text=caption, parse_mode=ParseMode.HTML)
        return False

def start_streamlit_ui_if_needed():
    """Start the streamlit UI as a background process if streamlit is installed and not already running."""
    try:
        # reuse logic similar to psychology_test (non-blocking)
        import socket
        def _is_running(port=8501):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    return s.connect_ex(("127.0.0.1", port)) == 0
            except Exception:
                return False
        if _is_running():
            logger.info("[blue]Streamlit UI already running on port 8501[/blue]")
            return
        streamlit_exe = shutil.which("streamlit")
        if not streamlit_exe:
            logger.warning("[yellow]Streamlit not found in PATH. Install it to enable web UI.[/yellow]")
            return
        ui_path = os.path.join(os.path.dirname(__file__), "streamlit_ui.py")
        cmd = [streamlit_exe, "run", ui_path, "--server.port", "8501", "--server.headless", "true"]
        logger.info("[blue]Starting Streamlit UI in background (port 8501)...[/blue]")
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=os.path.dirname(__file__), start_new_session=True)
    except Exception as e:
        logger.error(f"[red]Failed to start Streamlit UI: {e}[/red]")

def register_handlers(dp):
    """Register all bot handlers in organized groups"""
    
    # Command handlers
    commands = [
        ("start", handlers.start),
        ("psychology_tests", handlers.psychology_tests),
        ("my_profile", handlers.my_profile),
        ("wallet", handlers.wallet),
    ("admin", handlers.admin_panel),
    ("end_chat", handlers.end_smart_chat)
    ]
    
    for command, handler in commands:
        dp.add_handler(CommandHandler(command, handler))

    # Persistent keyboard handler (uses handler from handlers module)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handlers.handle_keyboard_buttons), group=0)

    # When any inline callback button is pressed we should disable smart chat for that user
    def _callback_preprocessor(update: Update, context: CallbackContext):
        try:
            user_id = update.callback_query.message.chat_id
            # mark smart chat inactive to avoid accidental forwarding
            context.user_data["smart_chat_active"] = False
        except Exception:
            pass

    # Register the preprocessor for callbacks (highest priority)
    dp.add_handler(CallbackQueryHandler(_callback_preprocessor), group=0)
    
    # Callback query handlers
    callback_handlers = [
        # Main menu
        ("^psychology_tests$", handlers.show_tests_cb),
        ("^my_profile$", handlers.show_profile_cb),
        ("^previous_test_results$", handlers.previous_test_results_cb),
        ("^purchased_packages$", handlers.purchased_packages_callback),
        ("^wallet_info$", handlers.wallet_info_callback),
        ("^charge_wallet$", handlers.charge_wallet_callback),
        ("^get_gift$", handlers.get_gift_callback),
        ("^smart_packages$", handlers.smart_packages),
        ("^smart_therapy$", handlers.smart_therapy_session),
        ("^smart_pack_", handlers.smart_package_selected),
        ("^back_to_home$", handlers.back_to_home_cb),
        
        # Package handlers (order matters)
        ("^start_package_test_", handlers.start_package_test_callback),
        ("^start_package_[^_]*$", handlers.start_package_callback),
        ("^package_test_", handlers.package_test_selected),
        ("^view_package_", handlers.view_package_callback),
        
        # Admin handlers
        ("^admin_users$", handlers.admin_users_list),
        (r"^admin_user_\d+$", handlers.admin_user_options),
        (r"^admin_user_\d+_charge$", handlers.admin_charge_prompt),
        (r"^admin_user_\d+_reduce$", handlers.admin_reduce_prompt),
        
        # Test handlers
        ("^view_result_", handlers.view_result_callback),
        (r"^[0-9]+$", handlers.test_selection),
        (r"^start_test_\d+$", handlers.start_test_callback),
        ("^show_profile_update_status$", handlers.show_profile_update_status),
        ("^show_psychological_profile$", handlers.show_psychological_profile),
    ]
    
    for pattern, handler in callback_handlers:
        dp.add_handler(CallbackQueryHandler(handler, pattern=pattern), group=1)
    
    # Message handlers
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handlers.handle_answer), group=1)
    dp.add_handler(MessageHandler(Filters.photo, handlers.handle_payment_screenshot), group=1)

def main():
    # Clear module cache
    import sys
    for module in list(sys.modules.keys()):
        if module.startswith('handlers') and module != 'telegram_handlers':
            del sys.modules[module]
    
    logger.info("[bold green]Starting Blue Psychology Test Bot[/bold green]")
    
    # Test smart chat initialization at startup
    try:
        console.print(Panel("[bold blue]🧪 Testing Smart Chat Components...[/bold blue]", border_style="blue"))
        
        # Test imports
        from smart_chat import get_memory, get_chat_agent
        console.log("[green]✅ Smart chat imports successful[/green]")
        
        # Test memory initialization
        console.log("[blue]💾 Testing memory initialization...[/blue]")
        test_memory = get_memory()
        console.log("[green]✅ Memory initialization successful[/green]")
        
        # Test agent creation
        console.log("[blue]🤖 Testing agent creation...[/blue]")
        test_agent = get_chat_agent(test_memory)
        console.log("[green]✅ Agent creation successful[/green]")
        
        console.print(Panel("[bold green]✅ Smart Chat Components Test Passed![/bold green]", border_style="green"))
        
    except Exception as e:
        console.print(Panel(f"[bold red]❌ Smart Chat Test Failed: {e}[/bold red]", border_style="red"))
        logger.error(f"Smart chat startup test failed: {e}", exc_info=True)
    
    start_g4f_server()

    # NEW: start streamlit UI so operator can watch logs in browser
    start_streamlit_ui_if_needed()
    
    TOKEN = "8330412252:AAErsNiTYTs9bXlaMZEGIElNh0ytDO3U-Ds"
    db.init_db()
    logger.info("[bold blue]Database initialized[/bold blue]")
    
    updater = Updater(TOKEN, use_context=True)
    register_handlers(updater.dispatcher)

    # Set bot commands
    updater.bot.set_my_commands([
        BotCommand("start", "🚀 شروع ربات و انتخاب تست"),
        BotCommand("psychology_tests", "📋 نمایش تست‌های روانشناسی"),
        BotCommand("my_profile", "🕵️ مشاهده نتایج تست‌های قبلی"),
        BotCommand("wallet", "💰 کیف پول من"),
        BotCommand("admin", "🛠️ پنل مدیریت"),
        BotCommand("end_chat", "🔚 پایان جلسه هوشمند")
    ])

    logger.info("[bold green]Bot is now running. Press Ctrl+C to stop.[/bold green]")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    console.print(Panel(
        "[bold green]Blue Psychology Test Bot[/bold green]\n"
        "[cyan]A sophisticated AI-powered psychology test platform[/cyan]",
        border_style="bright_blue"
    ))
    main()