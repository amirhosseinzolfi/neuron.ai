#!/usr/bin/env python3
"""Test PDF generation with RTL Persian text and improved styling."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pdf_utils import generate_pdf

# Test data with Persian content
test_summary = """
## سرزمینا پاینازا متسر چچیائز

**زریاک** (11) زبراک طسورر مدش هارراذ دخاو چشار سایاسا رر ربایطغ نیا

### مدش پاینازا روایذ

این یک متن آزمایشی به زبان فارسی است که باید به صورت راست به چپ نمایش داده شود.

### نتایج کلیدی

1. **باز بودن به تجربیات جدید**: سطح بالا (85%)
2. **وظیفه‌شناسی**: بسیار بالا (90%)  
3. **برون‌گرایی**: متوسط به بالا (60%)
4. **توافق‌پذیری**: بالا (70%)
5. **روان‌رنجوری**: پایین (30%)

### توصیه‌ها

- توسعه مهارت‌های ارتباطی
- تمرکز بر اهداف بلندمدت
- ایجاد تعادل بین کار و زندگی شخصی

### جدول نتایج

| ویژگی | نمره |
|------|------|
| باز بودن | 85% |
| وظیفه‌شناسی | 90% |
| برون‌گرایی | 60% |
| توافق‌پذیری | 70% |

### نکات مهم

> این نتایج براساس پاسخ‌های شما به پرسشنامه محاسبه شده است.

### لیست توصیه‌ها

- مطالعه منابع روانشناسی مثبت
- شرکت در کارگاه‌های توسعه فردی
- مشاوره با متخصص در صورت نیاز

**پایان گزارش**
"""

def main():
    """Generate test PDF."""
    print("🔧 Generating test PDF with RTL Persian text...")
    
    output_dir = Path(__file__).parent / "generated_media"
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / "test_rtl_fixed.pdf"
    
    # Check if test image exists
    image_path = output_dir / "test_chart.png"
    if not image_path.exists():
        # Try to find any image
        images = list(output_dir.glob("*.png")) + list(output_dir.glob("*.jpg"))
        image_path = images[0] if images else None
        if image_path:
            print(f"📷 Using image: {image_path.name}")
        else:
            print("⚠️  No test image found, generating PDF without image")
            image_path = None
    
    try:
        pdf_path = generate_pdf(
            summary_md=test_summary,
            user_name="علی احمدی",
            user_age=28,
            test_name="تست شخصیت پنج عاملی",
            output_path=output_path,
            image_path=image_path
        )
        
        print(f"✅ PDF generated successfully!")
        print(f"📄 Location: {pdf_path.resolve()}")
        print(f"📊 File size: {pdf_path.stat().st_size / 1024:.1f} KB")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
