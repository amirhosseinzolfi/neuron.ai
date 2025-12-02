# CONCURRENCY FIX: Key changes to make bot handle multiple users simultaneously

# Add at top of file:
from telegram.ext import run_async
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Create thread pool for concurrent operations
executor = ThreadPoolExecutor(max_workers=10)  # Handle up to 10 users concurrently

# Add per-user locks to prevent race conditions within same user
user_locks = {}

def get_user_lock(user_id):
    """Get or create a lock for specific user"""
    if user_id not in user_locks:
        user_locks[user_id] = threading.Lock()
    return user_locks[user_id]

# CRITICAL FIX 1: Make handle_answer non-blocking
@run_async
def handle_answer(update: Update, context: CallbackContext):
    """Handle user text messages - NOW CONCURRENT"""
    cid = update.effective_chat.id
    
    # Use per-user lock (only blocks THIS user, not others)
    with get_user_lock(cid):
        info = chat_states.get(cid)
        
        # ... existing code for handling different stages ...
        
        # When test is finished:
        if info["state"].get("finished"):
            console.log(f"[green]Test completed for user {cid}. Generating summary...[/green]")
            
            # CRITICAL: Don't wait for results - generate in background
            executor.submit(generate_and_send_results, update, context, cid, info)
            
            # Send immediate acknowledgment
            update.message.reply_text(
                "✅ تست شما تکمیل شد!\\n\\n"
                "🔄 در حال آمادهسازی نتایج...\\n"
                "نتایج به زودی برای شما ارسال خواهد شد."
            )
            
            # Clean up state immediately so user can start new test
            if cid in chat_states:
                del chat_states[cid]
            
            # Bot is now free to process other users!
            return

# CRITICAL FIX 2: Generate results without blocking
def generate_and_send_results(update: Update, context: CallbackContext, cid: int, info: dict):
    """Generate and send results in background - doesn't block other users"""
    try:
        console.log(f"[cyan]🚀 Starting background result generation for user {cid}[/cyan]")
        
        # Step 1: Generate summary
        console.log(f"[blue]📊 Generating summary for user {cid}...[/blue]")
        summary_content = pt.tele_summarize(info["state"])
        
        # Step 2: Generate caption
        console.log(f"[blue]📝 Generating caption for user {cid}...[/blue]")
        try:
            caption = pt.analyze_final_result(info["state"], summary_content)
        except Exception:
            caption = "تحلیل نهایی شخصیت شما"
        
        # Step 3: Get test name
        test_name = info.get("test_name", "تست روانشناسی")
        
        # Step 4: Generate image (with fallback)
        console.log(f"[blue]🎨 Generating image for user {cid}...[/blue]")
        image_path = None
        try:
            img_prompt = pt.generate_image_prompt(summary_content)
            images = pt.generate_images_for_prompt(
                img_prompt, cid, "/tmp", model="midjourney",
                num_images=1, width=512, height=512
            )
            if images:
                image_path = images[0]
        except Exception as e:
            console.log(f"[yellow]Image generation failed, using default: {e}[/yellow]")
            image_path = "/root/blue-psychology-test/images/neuron_result.png"
        
        # Step 5: Generate PDF
        console.log(f"[blue]📄 Generating PDF for user {cid}...[/blue]")
        pdf_path = None
        try:
            safe_name = test_name.replace(" ", "_")
            pdf_path = f"/tmp/{safe_name}_result_{int(time.time())}.pdf"
            
            # Get user info
            pdf_user_name = info.get("name", "کاربر گرامی")
            pdf_user_age = info.get("age", 0)
            
            generate_pdf(summary_content, pdf_user_name, pdf_user_age, test_name, pdf_path, image_path=image_path)
        except Exception as e:
            console.log(f"[yellow]PDF generation failed: {e}[/yellow]")
        
        # Step 6: Generate voice
        console.log(f"[blue]🎙️ Generating voice for user {cid}...[/blue]")
        voice_path = None
        try:
            voice_path = generate_final_result_analyze_voice(caption)
        except Exception as e:
            console.log(f"[yellow]Voice generation failed: {e}[/yellow]")
        
        # Step 7: Save to database
        console.log(f"[blue]💾 Saving to database for user {cid}...[/blue]")
        try:
            db.save_test_result(cid, test_name, summary_content, pdf_path or "", caption, voice_path, image_path)
        except Exception as e:
            console.log(f"[red]Database save failed: {e}[/red]")
        
        # Step 8: Send results to user
        console.log(f"[blue]📤 Sending results to user {cid}...[/blue]")
        
        # Send image
        if image_path and os.path.exists(image_path):
            try:
                with open(image_path, 'rb') as img:
                    context.bot.send_photo(
                        chat_id=cid,
                        photo=img,
                        caption=ui.IMAGE_GENERATED_CAPTION
                    )
                time.sleep(0.7)
            except Exception as e:
                console.log(f"[red]Failed to send image: {e}[/red]")
        
        # Send voice
        if voice_path and os.path.exists(voice_path):
            try:
                with open(voice_path, 'rb') as voice_file:
                    context.bot.send_voice(
                        chat_id=cid,
                        voice=voice_file,
                        caption="🎙️ آنالیز و تحلیل تست شما"
                    )
                time.sleep(0.7)
            except Exception as e:
                console.log(f"[red]Failed to send voice: {e}[/red]")
        
        # Send PDF
        if pdf_path and os.path.exists(pdf_path):
            try:
                with open(pdf_path, 'rb') as pdf_file:
                    context.bot.send_document(
                        chat_id=cid,
                        document=pdf_file,
                        caption=ui.PDF_REPORT_CAPTION.format(test_name=test_name)
                    )
            except Exception as e:
                console.log(f"[red]Failed to send PDF: {e}[/red]")
        
        console.log(f"[bold green]✅ Results sent successfully to user {cid}[/bold green]")
        
        # Step 9: Update profile in background (non-blocking)
        try:
            executor.submit(
                ai_utils.update_user_profile_with_ai,
                cid,
                summary_content,
                conversation_history=info["state"].get("conversation_history", []),
                state=info["state"]
            )
        except Exception as e:
            console.log(f"[yellow]Profile update scheduling failed: {e}[/yellow]")
        
    except Exception as e:
        console.log(f"[bold red]❌ Critical error in background generation for user {cid}: {e}[/bold red]")
        logger.error(f"Background generation failed for user {cid}: {e}", exc_info=True)
        
        # Send error message to user
        try:
            context.bot.send_message(
                chat_id=cid,
                text="❌ متأسفانه در تولید نتایج خطایی رخ داد. لطفاً دوباره تلاش کنید."
            )
        except Exception:
            pass

# CRITICAL FIX 3: Make other handlers non-blocking too
@run_async
def handle_multimodal_input(update: Update, context: CallbackContext):
    """Handle image/voice input - NOW CONCURRENT"""
    cid = update.effective_chat.id
    
    with get_user_lock(cid):
        # ... existing multimodal processing code ...
        pass

@run_async  
def handle_smart_chat_message(update: Update, context: CallbackContext):
    """Handle smart chat - NOW CONCURRENT"""
    cid = update.effective_chat.id
    
    with get_user_lock(cid):
        # ... existing smart chat code ...
        pass

# CRITICAL FIX 4: Update telegrambot.py to use concurrent dispatcher
# In telegrambot.py main():

def main():
    # ... existing setup ...
    
    updater = Updater(TOKEN, use_context=True, workers=10)  # ADD workers parameter
    
    # Enable concurrent processing
    updater.dispatcher.workers = 10  # Process up to 10 messages concurrently
    
    register_handlers(updater.dispatcher)
    
    # ... rest of code ...
