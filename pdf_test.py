#!/usr/bin/env python3
"""
Test utility for the PDF generation functionality.
Generates a sample PDF with various formatting elements to check styling.
"""

import os
from pathlib import Path

from pdf_utils import generate_pdf

def test_pdf_generation(output_dir: str = "./output") -> Path:
    """
    Generate a sample PDF with various formatting elements to test styling.
    
    Args:
        output_dir: Directory to save the test PDF
        
    Returns:
        Path to the generated PDF file
    """
    # Create test data with various elements
    test_name = "آزمون نمونه روانشناسی"
    user_name = "محمد احمدی"
    user_age = 28
    
    # Create a sample markdown with various elements to test styling
    sample_markdown = """
# گزارش نتایج آزمون

## اطلاعات کلی

این یک **نمونه** گزارش برای نمایش نحوه قالب‌بندی المان‌های مختلف در PDF است.

## بخش‌های اصلی نتایج

### ویژگی‌های شخصیتی

شما دارای ویژگی‌های زیر هستید:

* برون‌گرایی: بالا
* درون‌گرایی: متوسط
* خلاقیت: بسیار بالا
* نظم‌پذیری: متوسط

### نتایج تفصیلی

در این بخش، نتایج با جزئیات بیشتری توضیح داده می‌شود.

1. **برون‌گرایی**: شما فردی اجتماعی هستید که از تعامل با دیگران لذت می‌برید.
2. **درون‌گرایی**: در برخی موارد به تنهایی و فکر کردن نیاز دارید.
3. **خلاقیت**: توانایی فوق‌العاده‌ای در ایجاد راه‌حل‌های خلاقانه دارید.

> نکته مهم: این نتایج براساس پاسخ‌های شما به سوالات آزمون است و صرفاً جنبه راهنمایی دارد.

## مقایسه امتیازات

| ویژگی | امتیاز شما | میانگین | وضعیت |
|-------|:----------:|:-------:|:------:|
| برون‌گرایی | 85 | 65 | بالاتر از میانگین |
| درون‌گرایی | 60 | 55 | نزدیک به میانگین |
| خلاقیت | 90 | 60 | بسیار بالاتر |
| نظم‌پذیری | 55 | 70 | پایین‌تر از میانگین |

### نکات تکمیلی

به صورت کلی، شما فردی با توانایی‌های خاص در زمینه‌های خلاقیت و ارتباطات اجتماعی هستید. 
توصیه می‌شود از این نقاط قوت در مسیر شغلی و زندگی خود بهره ببرید.

## توصیه‌های کاربردی

```
1. زمان بیشتری را به فعالیت‌های خلاقانه اختصاص دهید
2. برنامه‌ریزی روزانه را تقویت کنید
3. از توانایی شبکه‌سازی اجتماعی خود استفاده کنید
```

### یادداشت پایانی

از شرکت شما در این آزمون سپاسگزاریم. امیدواریم نتایج برای شما مفید باشد.
    """
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    output_path = Path(output_dir) / "test_sample_pdf.pdf"
    
    # Generate the PDF
    pdf_path = generate_pdf(
        summary_md=sample_markdown,
        user_name=user_name,
        user_age=user_age,
        test_name=test_name,
        output_path=output_path
    )
    
    print(f"Test PDF generated at: {pdf_path.absolute()}")
    return pdf_path

if __name__ == "__main__":
    # Run the test when script is executed directly
    test_pdf_generation()
