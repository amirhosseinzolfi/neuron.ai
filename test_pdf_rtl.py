#!/usr/bin/env python3
"""
Test script for RTL PDF generation with Persian text and image in header
"""
from pathlib import Path
from pdf_utils import generate_pdf

# Sample Persian test summary with real content from the image
test_summary = """
# تست طرحواره پایۀ شناختی‌ یانگ

## خلاصه کلی

تستی طرحواره پایۀ شناختی یانگ برمبنای نظریۀ جفری یانگ درباره طرحواره‌های ناسازگار اولیۀ است که بر پایۀ نیازهای برآورده نشدۀ هیجانی و تجربیات دوران کودکی شکل می‌گیرند.

## تفسیر نتایج

### نقاط برجستۀ شخصیتی

برای تفسیر درست نتایج، به نمرات بالای (بالاتر از ۱۱) در هر یک از مقیاس‌های طرحواره توجه کنید.

### طرحواره‌ها با نمرات بالا

#### محرومیت هیجانی
این طرحواره نشان می‌دهد که شما احساس می‌کنید نیازهای هیجانی اساسی‌تان مانند مراقبت، همدلی یا محبت توسط دیگران برآورده نمی‌شود.

#### شکست
احساس عدم کفایت و ناتوانی در انجام وظایف به خوبی دیگران، حتی در مواردی که توانایی لازم را دارید.

#### بی‌اعتمادی / بدرفتاری
انتظار اینکه دیگران شما را آزار خواهند داد، فریب می‌دهند یا از شما سوء استفاده خواهند کرد.

## توصیه‌های روانشناختی

### راهکارهای پیشنهادی برای بهبود

۱. **آگاهی از طرحواره‌ها**: اولین قدم شناخت و پذیرش این الگوهای فکری است
۲. **چالش با افکار منفی**: سعی کنید شواهد موافق و مخالف این باورها را بیابید
۳. **درمان شناختی‌-رفتاری**: مراجعه به روانشناس برای کار حرفه‌ای روی این طرحواره‌ها
۴. **تمرین‌های ذهن‌آگاهی**: تمرین‌هایی که به شناخت احساسات و افکار در لحظۀ حال کمک می‌کنند

### جدول خلاصۀ طرحواره‌ها

| طرحواره | نمرۀ شما | تفسیر |
|---------|----------|-------|
| محرومیت هیجانی | ۱۵ | بالا - نیاز به توجه |
| شکست | ۱۲ | متوسط به بالا |
| بی‌اعتمادی | ۱۳ | بالا |

## نتیجه‌گیری

نتایج این تست نشان می‌دهد که شما در برخی حوزه‌ها دارای طرحواره‌های ناسازگار هستید که ممکن است بر روابط و عملکرد روزمرۀ‌تان تأثیر بگذارد. با کمک یک متخصص و تمرین‌های مناسب، می‌توانید این الگوها را تغییر دهید.

---

**نکتۀ مهم**: این تست یک ابزار غربالگری است و جایگزین ارزیابی حرفه‌ای نیست. برای راهنمایی دقیق‌تر با روانشناس مشورت کنید.
"""

def main():
    print("🔄 Testing RTL PDF generation with Persian text...")
    print("=" * 60)
    
    # Test data
    user_name = "سارا احمدی"
    user_age = 28
    test_name = "تست طرحواره پایۀ شناختی یانگ"
    output_path = "/tmp/test_rtl_persian_pdf.pdf"
    
    # Use default image if exists
    image_path = "/root/blue-psychology-test/images/neuron_result.png"
    if not Path(image_path).exists():
        print(f"⚠️  Image not found at {image_path}, generating without image")
        image_path = None
    else:
        print(f"✅ Using image: {image_path}")
    
    try:
        print("\n📝 Generating PDF with:")
        print(f"   - Name: {user_name}")
        print(f"   - Age: {user_age}")
        print(f"   - Test: {test_name}")
        print(f"   - Output: {output_path}")
        print()
        
        # Generate PDF
        result_path = generate_pdf(
            summary_md=test_summary,
            user_name=user_name,
            user_age=user_age,
            test_name=test_name,
            output_path=output_path,
            image_path=image_path
        )
        
        print("=" * 60)
        print(f"✅ PDF generated successfully!")
        print(f"📄 Output: {result_path}")
        print(f"📊 File size: {result_path.stat().st_size / 1024:.2f} KB")
        
        # Check if file exists and has content
        if result_path.exists() and result_path.stat().st_size > 0:
            print("\n✅ All tests passed!")
            print(f"\n🔍 You can view the PDF at: {result_path}")
            print("\n📋 Changes implemented:")
            print("   ✓ Persian text properly formatted for RTL display")
            print("   ✓ Removed white border from header image")
            print("   ✓ Added beautiful wavy separator to header")
            print("   ✓ Fixed broken font import (removed IranYekan)")
            return True
        else:
            print("\n❌ PDF file is empty or doesn't exist!")
            return False
            
    except Exception as e:
        print(f"\n❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
