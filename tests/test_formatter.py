"""
Example and Test Script for Enhanced Telegram Formatter
Demonstrates the new formatting capabilities for psychology bot
"""

from telegram_formatter import telegram_formatter, format_psychology_content
import json

def test_basic_formatting():
    """Test basic formatting capabilities"""
    print("=" * 50)
    print("Testing Basic Formatting")
    print("=" * 50)
    
    # Test header formatting
    header1 = telegram_formatter.format_header("نتایج آزمون شخصیت", level=1)
    print("Header Level 1:")
    print(header1)
    
    header2 = telegram_formatter.format_header("تحلیل شخصیت", level=2)
    print("Header Level 2:")
    print(header2)
    
    # Test list formatting
    items = ["درون‌گرا و متفکر", "تحلیل‌گر و منطقی", "خلاق و نوآور"]
    numbered_list = telegram_formatter.format_numbered_list(items)
    print("Numbered List:")
    print(numbered_list)
    
    # Test bullet points
    for item in items:
        bullet = telegram_formatter.format_list_item(item, 'point')
        print(bullet, end='')
    
    print("\n")

def test_psychology_specific_formatting():
    """Test psychology-specific formatting"""
    print("=" * 50)
    print("Testing Psychology-Specific Formatting")
    print("=" * 50)
    
    # Test personality score formatting
    trait_score = telegram_formatter.format_personality_score(
        "درون‌گرایی", 75, "تمایل قوی به تأمل و آرامش"
    )
    print("Personality Score:")
    print(trait_score)
    
    # Test progress bar
    progress = telegram_formatter.format_progress_bar(85, "نمره کلی")
    print("Progress Bar:")
    print(progress)
    
    # Test highlight box
    highlight = telegram_formatter.format_highlight_box(
        "شما فردی تحلیل‌گر و منطقی هستید که ترجیح می‌دهید تصمیمات را بر اساس داده‌ها و شواهد بگیرید.",
        "نکته کلیدی"
    )
    print("Highlight Box:")
    print(highlight)
    
    print("\n")

def test_complete_result_formatting():
    """Test complete psychology result formatting"""
    print("=" * 50)
    print("Testing Complete Result Formatting")
    print("=" * 50)
    
    # Sample result data
    sample_result = {
        'test_name': 'تست شخصیت‌شناسی MBTI',
        'user_name': 'علی',
        'analysis': """## نتایج آزمون MBTI شما

**تیپ شخصیتی:** INTJ - معمار

### ویژگی‌های کلیدی:
- **درون‌گرا (I):** شما انرژی خود را از تنهایی و تأمل می‌گیرید
- **شهودی (N):** بر ایده‌ها و احتمالات تمرکز دارید
- **منطقی (T):** تصمیمات را بر اساس منطق می‌گیرید  
- **قضاوت‌گر (J):** ساختار و برنامه‌ریزی را ترجیح می‌دهید

### نقاط قوت شما:
1. تفکر استراتژیک
2. خلاقیت در حل مسائل
3. استقلال و خودکفایی
4. پیگیری اهداف بلندمدت

### زمینه‌های قابل بهبود:
- روابط اجتماعی
- انعطاف‌پذیری
- ابراز احساسات

**نتیجه‌گیری:** شما یک معمار ذهن هستید که می‌تواند سیستم‌های پیچیده را طراحی و بهبود دهد.""",
        'answers': [
            {
                'question': 'در جمع‌های بزرگ چگونه رفتار می‌کنید؟',
                'selected_option': 'ترجیح می‌دهم گوش کنم و کمتر صحبت کنم',
                'user_response': 'معمولاً ساکت می‌مانم'
            }
        ]
    }
    
    # Format the complete result
    formatted_chunks = format_psychology_content(sample_result, 'analysis')
    
    print("Formatted Result Chunks:")
    for i, chunk in enumerate(formatted_chunks, 1):
        print(f"\n--- Chunk {i} ---")
        print(chunk)
        print("--- End Chunk ---\n")

def test_question_formatting():
    """Test question formatting"""
    print("=" * 50)
    print("Testing Question Formatting") 
    print("=" * 50)
    
    question_data = {
        'question': 'وقتی با یک مسئله جدید روبرو می‌شوید، معمولاً چگونه عمل می‌کنید؟',
        'number': 3,
        'total': 10,
        'options': [
            'فوراً شروع به عمل می‌کنم',
            'ابتدا در مورد آن فکر می‌کنم', 
            'از دیگران مشورت می‌گیرم',
            'منتظر می‌مانم تا راه حل خودش پیدا شود'
        ]
    }
    
    formatted_chunks = format_psychology_content(question_data, 'question')
    
    for chunk in formatted_chunks:
        print(chunk)
        print("\n")

def test_acknowledgment_formatting():
    """Test acknowledgment formatting"""
    print("=" * 50)
    print("Testing Acknowledgment Formatting")
    print("=" * 50)
    
    ack_data = {
        'user_response': 'من معمولاً ابتدا فکر می‌کنم',
        'acknowledgment': 'جالب است! این نشان‌دهنده تفکر تأملی و احتیاط در تصمیم‌گیری شماست. این ویژگی معمولاً در افراد درون‌گرا دیده می‌شود.'
    }
    
    formatted_chunks = format_psychology_content(ack_data, 'acknowledgment')
    
    for chunk in formatted_chunks:
        print(chunk)
        print("\n")

def test_error_formatting():
    """Test error message formatting"""
    print("=" * 50)
    print("Testing Error Message Formatting")
    print("=" * 50)
    
    error_data = {
        'error': 'پاسخ شما کاملاً واضح نیست. لطفاً یکی از گزینه‌های ارائه شده را انتخاب کنید.',
        'suggestion': 'می‌توانید عدد گزینه مورد نظرتان را تایپ کنید یا متن کاملش را بنویسید.'
    }
    
    formatted_chunks = format_psychology_content(error_data, 'error')
    
    for chunk in formatted_chunks:
        print(chunk)
        print("\n")

def test_persian_numbers():
    """Test Persian number conversion"""
    print("=" * 50)
    print("Testing Persian Number Conversion")
    print("=" * 50)
    
    english_text = "سوال 1 از 10: شما 85% درون‌گرا هستید"
    persian_text = telegram_formatter.to_persian_numbers(english_text)
    
    print(f"English: {english_text}")
    print(f"Persian: {persian_text}")
    print("\n")

def test_table_formatting():
    """Test table formatting"""
    print("=" * 50)
    print("Testing Table Formatting")
    print("=" * 50)
    
    headers = ["ویژگی", "امتیاز", "سطح"]
    rows = [
        ["درون‌گرایی", "۷۵%", "بالا"],
        ["خلاقیت", "۹۰%", "خیلی بالا"],
        ["منطق", "۸۰%", "بالا"]
    ]
    
    table = telegram_formatter.format_table(headers, rows, "نتایج آزمون")
    print(table)

def run_all_tests():
    """Run all formatting tests"""
    print("🧠 Starting Enhanced Telegram Formatter Tests 🧠\n")
    
    test_basic_formatting()
    test_psychology_specific_formatting()
    test_question_formatting()
    test_acknowledgment_formatting()
    test_error_formatting()
    test_persian_numbers()
    test_table_formatting()
    test_complete_result_formatting()
    
    print("✅ All tests completed!")
    print("\nThe new formatter provides:")
    print("🔹 Enhanced visual hierarchy")
    print("🔹 Better RTL support for Persian")
    print("🔹 Psychology-specific formatting")
    print("🔹 Intelligent message chunking")
    print("🔹 Improved readability")
    print("🔹 Professional appearance")

if __name__ == "__main__":
    run_all_tests()
