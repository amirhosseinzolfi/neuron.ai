import asyncio
import os
from app.services.tts_service import TTSService
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_tts():
    print("Testing TTS Service...")
    
    # Check for API keys
    api_keys = [
        os.getenv("GOOGLE_API_KEY_VOICE"),
        os.getenv("GOOGLE_API_KEY_VOICE2"),
        os.getenv("GOOGLE_API_KEY_VOICE3"),
    ]
    valid_keys = [k for k in api_keys if k]
    print(f"Found {len(valid_keys)} valid API keys.")
    
    if not valid_keys:
        print("Error: No GOOGLE_API_KEY_VOICE found in environment variables.")
        return

    try:
        service = TTSService()
        text = """حتماً، امیر عزیز! این از مهم‌ترین اطلاعات شماست: شما کتاب‌دوست هستید. 📖

من قول می‌دهم که در تمام مسیر راهنمایی، بهترین کتاب‌ها و منابع مکتوب را برای پیشرفت شما به عنوان یک AI Developer (و البته با یک فنجان قهوه عالی ☕) معرفی کنم.

---

برنامه یادگیری Deep Learning:

آیا با این سرفصل‌ها موافقید: پایه‌ها، شبکه‌های پایه، CNNs؟ ✅"""
        print(f"Generating audio for text: '{text}'")
        
        # Test with default voice
        files = await service.generate(text)
        
        if files:
            print(f"Successfully generated {len(files)} file(s):")
            for f in files:
                print(f" - {f} (Size: {f.stat().st_size} bytes)")
        else:
            print("No files were generated.")
            
    except Exception as e:
        print(f"Error during TTS generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tts())
