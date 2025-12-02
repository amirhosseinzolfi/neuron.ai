"""
Async Telegram handlers for concurrent user processing
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from urllib.parse import urlparse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from ai_utils import generate_final_result_html_report
from telegram_handlers import *

# Global executor for CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=20)


def _is_inline_html_url_allowed(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return parsed.scheme in {"https", "tg"}


def _build_html_report_markup(html_link: str) -> InlineKeyboardMarkup | None:
    if not _is_inline_html_url_allowed(html_link):
        return None
    return InlineKeyboardMarkup([[InlineKeyboardButton("📄 گزارش HTML", url=html_link)]])


def _html_message_kwargs(html_link: str) -> dict[str, object]:
    kwargs: dict[str, object] = {"disable_web_page_preview": True}
    markup = _build_html_report_markup(html_link)
    if markup:
        kwargs["reply_markup"] = markup
    return kwargs

async def handle_answer_async(update: Update, context: CallbackContext):
    """Async version of handle_answer that doesn't block other users"""
    cid = update.effective_chat.id
    info = chat_states.get(cid)
    
    # Handle multimodal inputs
    if (update.message.photo or update.message.voice) and info and info.get("stage") in ["answering", "intro_zero", "ask_name_age", "ask_user_info"]:
        if info.get("stage") in ["intro_zero", "ask_name_age", "ask_user_info"]:
            pass
        else:
            return await handle_multimodal_input_async(update, context)
    
    text = update.message.text if update.message.text else (update.message.caption or "")

    if context.user_data.get("_skip_handle_answer"):
        context.user_data.pop("_skip_handle_answer", None)
        return None

    # Handle admin stages
    if info and info.get("stage") == "admin_charge_amount":
        return handle_admin_charge_input(update, context, text, info)
    if info and info.get("stage") == "admin_reduce_amount":
        return handle_admin_reduce_input(update, context, text, info)

    # Handle smart chat
    if context.user_data.get("smart_chat_active"):
        return await handle_smart_chat_async(update, context, text)

    # Auto-activate smart chat if no active flow
    if not info or info["stage"] not in ["intro_zero", "ask_name_age", "ask_user_info", "answering", "admin_charge_amount", "admin_reduce_amount", "await_payment_screenshot"]:
        context.user_data["smart_chat_active"] = True
        return await handle_smart_chat_async(update, context, text)

    # Handle test stages
    if info["stage"] == "intro_zero":
        return await handle_intro_zero_async(update, context, info, text)
    elif info["stage"] == "ask_name_age":
        return await handle_name_age_async(update, context, info, text)
    elif info["stage"] == "ask_user_info":
        return await handle_user_info_async(update, context, info, text)
    elif info["stage"] == "answering":
        return await handle_test_answering_async(update, context, info, text)

async def handle_smart_chat_async(update: Update, context: CallbackContext, text: str):
    """Async smart chat handler"""
    user_id = str(update.effective_chat.id)
    
    waiting_message = update.message.reply_text("🧠 نورون در حال فکر کردن ... 💭")
    
    try:
        # Run AI processing in thread pool
        loop = asyncio.get_event_loop()
        agent = await loop.run_in_executor(executor, get_smart_chat_agent)
        response = await loop.run_in_executor(executor, smart_chat_logic, agent, user_id, text)
        
        waiting_message.delete()
        
        if isinstance(response, dict) and "refined" in response:
            send_formatted_text(update, response["refined"])
        else:
            send_formatted_text(update, response if isinstance(response, str) else str(response))
            
    except Exception as e:
        logger.error(f"Smart chat error: {e}")
        try:
            waiting_message.delete()
        except:
            pass
        send_formatted_text(update, "متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید.")

async def handle_test_answering_async(update: Update, context: CallbackContext, info: dict, text: str):
    """Async test answering that doesn't block other users"""
    cid = update.effective_chat.id
    
    # Show waiting message for questions after first
    wait = None
    current_q_index = info["state"].get("current_question", 0)
    if current_q_index > 0:
        random_tip = random.choice(ui.NEURON_TIPS)
        wait_message_with_tip = ui.ANALYZING_ANSWER_WITH_TIP.format(tip=random_tip)
        wait = update.message.reply_text(wait_message_with_tip, parse_mode=ParseMode.HTML)
    
    # Process answer in thread pool
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(executor, pt.tele_process_answer, info["state"], text)
    
    if wait:
        try:
            wait.delete()
        except:
            pass

    # Send acknowledgment and next question
    ack_message = res.get("ack")
    next_question_message = res.get("next")

    if ack_message:
        send_formatted_text(update, ack_message)

    if next_question_message:
        send_formatted_text(update, next_question_message)
    elif info["state"].get("finished"):
        # Test completed - start async result generation
        await handle_test_completion_async(update, context, cid, info)

async def handle_test_completion_async(update: Update, context: CallbackContext, cid: int, info: dict):
    """Async test completion that doesn't block other users"""
    
    # Send immediate acknowledgment
    update.message.reply_text(
        "✅ تست شما تکمیل شد!\n\n"
        "🔄 در حال آمادهسازی نتایج...\n"
        "نتایج طی چند لحظه برای شما ارسال خواهد شد."
    )
    
    # Start async result generation
    asyncio.create_task(generate_and_send_results_async(context.bot, cid, dict(info)))
    
    # Handle package completion
    if "user_package_id" in info:
        handle_package_test_completion(update, context, cid, info["user_package_id"], int(info["test_choice"]), info)
    
    # Clean up immediately - user can start new test
    if cid in chat_states:
        del chat_states[cid]

async def generate_and_send_results_async(bot, cid: int, info: dict):
    """Generate and send results completely asynchronously"""
    try:
        console.log(f"[cyan]🚀 Async generation started for user {cid}[/cyan]")
        
        loop = asyncio.get_event_loop()
        
        # Generate summary
        summary_content = await loop.run_in_executor(executor, pt.tele_summarize, info["state"])
        
        # Generate caption
        try:
            caption = await loop.run_in_executor(executor, pt.analyze_final_result, info["state"], summary_content)
        except:
            caption = "تحلیل نهایی شخصیت شما"
        
        test_name = info.get("test_name", "تست روانشناسی")
        
        # Generate image
        image_path = None
        try:
            img_prompt = await loop.run_in_executor(executor, pt.generate_image_prompt, summary_content)
            images = await loop.run_in_executor(executor, pt.generate_images_for_prompt, img_prompt, cid, "/tmp", "midjourney", 1, 512, 512)
            image_path = images[0] if images else None
        except:
            pass
        if not image_path or not os.path.exists(image_path):
            image_path = "/root/blue-psychology-test/images/neuron_result.png"
        
        # Generate PDF
        pdf_path = None
        try:
            safe_name = test_name.replace(" ", "_")
            pdf_path = f"/tmp/{safe_name}_result_{int(time.time())}.pdf"
            pdf_user_name = info.get("name", "کاربر گرامی")
            pdf_user_age = info.get("age", 0)
            await loop.run_in_executor(executor, generate_pdf, summary_content, pdf_user_name, pdf_user_age, test_name, pdf_path, image_path)
        except Exception as e:
            console.log(f"[yellow]PDF generation failed: {e}[/yellow]")
        
        # Generate voice
        voice_path = None
        try:
            voice_path = await loop.run_in_executor(executor, generate_final_result_analyze_voice, caption)
        except Exception as e:
            console.log(f"[yellow]Voice generation failed: {e}[/yellow]")

        # Generate HTML report
        html_path = None
        html_url = None
        try:
            html_result = await loop.run_in_executor(
                executor,
                generate_final_result_html_report,
                info["state"],
                caption,
                summary_content,
                info["state"].get("conversation_history", []),
            )
            if html_result:
                html_path, html_url = html_result
        except Exception as e:
            console.log(f"[yellow]HTML report generation failed: {e}[/yellow]")
        
        # Save to database
        try:
            await loop.run_in_executor(
                executor,
                db.save_test_result,
                cid,
                test_name,
                summary_content,
                pdf_path or "",
                caption,
                voice_path,
                image_path,
                html_path,
            )
        except Exception as e:
            console.log(f"[red]Database save failed: {e}[/red]")
        
        # Send results
        await send_results_async(bot, cid, image_path, voice_path, pdf_path, test_name, html_url)
        
        console.log(f"[bold green]✅ Results sent to user {cid}[/bold green]")
        
        # Update profile in background
        try:
            asyncio.create_task(update_user_profile_async(cid, summary_content, info["state"]))
        except:
            pass
            
    except Exception as e:
        console.log(f"[bold red]❌ Error for user {cid}: {e}[/bold red]")
        try:
            await asyncio.get_event_loop().run_in_executor(executor, bot.send_message, cid, "❌ متأسفانه در تولید نتایج خطایی رخ داد.")
        except:
            pass

async def send_results_async(bot, cid: int, image_path: str, voice_path: str, pdf_path: str, test_name: str, html_url: str = None):
    """Send results asynchronously"""
    loop = asyncio.get_event_loop()
    
    # Send image
    if image_path and os.path.exists(image_path):
        try:
            with open(image_path, 'rb') as img:
                await loop.run_in_executor(executor, bot.send_photo, cid, img, ui.IMAGE_GENERATED_CAPTION)
            await asyncio.sleep(0.7)
        except:
            pass
    
    # Send voice
    if voice_path and os.path.exists(voice_path):
        try:
            with open(voice_path, 'rb') as voice:
                await loop.run_in_executor(executor, bot.send_voice, cid, voice, "🎙️ آنالیز و تحلیل تست شما")
            await asyncio.sleep(0.7)
        except:
            pass
    
    # Send PDF
    if pdf_path and os.path.exists(pdf_path):
        try:
            with open(pdf_path, 'rb') as pdf:
                await loop.run_in_executor(executor, bot.send_document, cid, pdf, ui.PDF_REPORT_CAPTION.format(test_name=test_name))
        except:
            pass

    if html_url:
        try:
            kwargs = _html_message_kwargs(html_url)
            send_fn = partial(
                bot.send_message,
                cid,
                ui.HTML_RESULT_MESSAGE.format(link=html_url),
                **kwargs
            )
            await loop.run_in_executor(executor, send_fn)
        except Exception:
            pass

async def update_user_profile_async(cid: int, summary_content: str, state: dict):
    """Update user profile asynchronously"""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, ai_utils.update_user_profile_with_ai, cid, summary_content, state.get("conversation_history", []), state)
    except Exception as e:
        console.log(f"[red]Profile update failed for user {cid}: {e}[/red]")

async def handle_multimodal_input_async(update: Update, context: CallbackContext):
    """Async multimodal input handler"""
    # Implementation similar to sync version but with async/await
    # This would be a longer implementation - keeping it brief for now
    pass

async def handle_intro_zero_async(update: Update, context: CallbackContext, info: dict, text: str):
    """Async intro zero handler"""
    # Implementation with async processing
    pass

async def handle_name_age_async(update: Update, context: CallbackContext, info: dict, text: str):
    """Async name/age handler"""
    # Implementation with async processing
    pass

async def handle_user_info_async(update: Update, context: CallbackContext, info: dict, text: str):
    """Async user info handler"""
    # Implementation with async processing
    pass