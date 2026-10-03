"""
12-Day School and Academic Coaching Plan Generator Skill
----------------------------------------------------------------------
Synthesizes user profile, psychological testing traits, and diagnostic
inputs into a structured, personalized 12-day curriculum.
"""

from typing import Dict, Any, List, Optional
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from ai_utils import get_neuron_llm

logger = logging.getLogger("school_plan_generator")

PLAN_GENERATOR_SYSTEM_PROMPT = """
شما یک کوچ ارشد برنامه‌ریزی تحصیلی، کنکور و رشد شناختی دانش‌آموزان و دانشجویان هستید.
وظیفه شما طراحی یک «برنامه مربی‌گری و تحصیلی ۱۲ روزه» جامع، گام‌به‌گام و کاملاً شخصی‌سازی‌شده است.

### اصول طراحی برنامه ۱۲ روزه:
۱. بر اساس استعدادها، ویژگی‌های شخصیتی، سبک یادگیری و سوابق تست‌های روانشناسی کاربر طراحی شود.
۲. نقاط ضعف (مثل اهمال‌کاری، حواس‌پرتی گوشی، اضطراب امتحان یا ضعف در دروس خاص) مستقیماً هدف‌گذاری و درمان شوند.
۳. هر روز شامل یک موضوع مشخص، هدف یادگیری، نکات انگیزشی/ذهنی، تمرین‌های روزانه، و تکلیف شبانه شفاف باشد.
۴. معیار قبولی (Passing Criteria) برای هر تکلیف باید کاملاً واضح و سنجش‌پذیر باشد.

### ساختار دقیق خروجی (JSON):
شما باید فقط و فقط یک آبجکت معتبر JSON طبق ساختار زیر برگردانید:
{
  "student_name": "نام دانش‌آموز",
  "curriculum_goal": "هدف کلی برنامه ۱۲ روزه",
  "strengths_leveraged": ["نقطه قوت ۱", "نقطه قوت ۲"],
  "weaknesses_addressed": ["نقطه ضعف ۱", "نقطه ضعف ۲"],
  "total_days": 12,
  "current_day": 1,
  "status": "active",
  "days": [
    {
      "day": 1,
      "theme": "عنوان روز اول (مثلاً: مهندسی محیط مطالعه و ماتریس اولویت‌ها)",
      "learning_objective": "هدف یادگیری دقیق این روز",
      "mindset_and_theory": "نکته علمی و ذهنی جهت افزایش تمرکز و انگیزه",
      "daily_exercises": ["تمرین ۱", "تمرین ۲"],
      "homework_assignment": "تکلیف دقیق که دانش‌آموز در پایان روز باید ارسال کند",
      "passing_criteria": "معیار دقیق قبولی در تکلیف (حداقل موارد لازم برای ارتقا به روز بعد)",
      "status": "active",
      "submission": null,
      "evaluation": null
    }
  ]
}

توجه بسیار مهم:
- آرایه `days` باید حتماً شامل ۱۲ روز کامل (روزهای ۱ تا ۱۲) با توالی منطقی و رو به رشد باشد.
- روز ۱۲ باید جمع‌بندی، آزمون خودارزیابی نهایی و تدوین برنامه تداوم عادات باشد.
- خروجی فقط JSON خالص باشد بدون متن یا توضیحات جانبی.
"""


def generate_12day_school_plan(
    user_profile: Optional[Dict[str, Any]] = None,
    diagnostic_info: Optional[Dict[str, Any]] = None,
    psych_tests: Optional[List[Dict[str, Any]]] = None,
    memories: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Skill: Generates a complete 12-day personalized academic coaching schedule.
    """
    llm = get_neuron_llm()

    context_parts = []
    if user_profile:
        context_parts.append(f"### مشخصات و پروفایل کاربر:\n{json.dumps(user_profile, ensure_ascii=False)}")
    if diagnostic_info:
        context_parts.append(f"### اطلاعات تحصیلی و چالش‌های دریافتی:\n{json.dumps(diagnostic_info, ensure_ascii=False)}")
    if psych_tests:
        context_parts.append(f"### سوابق تست‌های روانشناختی:\n{json.dumps(psych_tests[:3], ensure_ascii=False)}")
    if memories:
        mem_texts = [m.get("content") or str(m) for m in memories[:4]]
        context_parts.append(f"### فکت‌های ذخیره‌شده از کاربر:\n" + "\n".join(f"- {t}" for t in mem_texts))

    user_context_str = "\n\n".join(context_parts) if context_parts else "دانش‌آموز خواهان برنامه رشد تحصیلی ۱۲ روزه."

    messages = [
        SystemMessage(content=PLAN_GENERATOR_SYSTEM_PROMPT),
        HumanMessage(content=f"لطفاً بر اساس مشخصات زیر، برنامه ۱۲ روزه تحصیلی را تولید کن:\n\n{user_context_str}")
    ]

    try:
        from app.agents.skills import safe_extract_text, extract_clean_json
        from app.agents.school_logger import log_plan_generated

        response = llm.invoke(messages)
        raw_text = safe_extract_text(response.content)
        plan = extract_clean_json(raw_text)

        plan["total_days"] = 12
        plan["current_day"] = 1
        plan["status"] = "active"

        # Rich logging in terminal
        log_plan_generated(plan)
        return plan
    except Exception as e:
        logger.error(f"Error generating 12-day school plan: {e}", exc_info=True)
        # Fallback template if LLM JSON fails
        student_name = (user_profile or {}).get("first_name") or "دانش‌آموز"
        plan = _build_fallback_12day_plan(student_name)
        try:
            from app.agents.school_logger import log_plan_generated
            log_plan_generated(plan)
        except Exception:
            pass
        return plan


def _build_fallback_12day_plan(student_name: str) -> Dict[str, Any]:
    """Fallback default 12-day curriculum structure."""
    days = []
    themes = [
        ("ارزیابی و سازمان‌دهی محیط مطالعه", "حذف محرک‌های مزاحم و ایجاد میز کار استاندارد", "ثبت عکس یا گزارش از سازمان‌دهی میز مطالعه"),
        ("تکنیک پومودورو و مدیریت انرژی مغز", "اجرای ۴ بازه ۲۵ دقیقه‌ای مطالعه عمیق با ۵ دقیقه استراحت", "گزارش زمان‌های پومودورو و میزان افت توجه"),
        ("مبارزه با اهمال‌کاری و قانون ۵ ثانیه", "شناسایی عامل تعلل در دروس سخت و شروع فوری", "نوشتن چرایی تعلل در درس چالش‌برانگیز و ۳ اقدام آغازین"),
        ("جعبه یادگیری لایتنر و تکرار فاصله‌دار", "ساخت فلاش‌کارت برای مفاهیم دشوار و فرمول‌ها", "ساخت حداقل ۱۵ فلاش‌کارت و مرور مرحله اول"),
        ("تکنیک فاینمن برای درک عمیق دروس", "توضیح دادن یک مبحث سخت به زبان ساده به یک فرد خیالی", "ارسال متن یا ویس خلاصه مبحث دشوار به زبان ساده"),
        ("مدیریت خواب و بازیابی عصبی-شناختی", "تنظیم ساعت خواب و عدم استفاده از گوشی ۱ ساعت قبل خواب", "ثبت زمان خاموشی و سنجش هوشیاری صبحگاهی"),
        ("آزمون نیمه‌راه و تحلیل اشتباهات", "حل یک آزمون شبیه‌ساز و استخراج جدول تحلیل آزمون", "ارسال جدول تحلیل اشتباهات و دسته‌بندی آن‌ها"),
        ("نقشه‌کشی ذهنی (Mind Mapping) برای مرور سریع", "رسم نقشه ذهنی یک فصل از درس‌های حفظی/تحلیلی", "ارسال تصویر یا ساختار مایند مپ رسم‌شده"),
        ("مدیریت استرس امتحان و بازسازی خطاهای شناختی", "تمرین تنفس دیافراگمی و ثبت افکار خودآیند منفی", "ثبت ۳ فکر منفی تحصیلی و جایگزینی با افکار واقع‌بینانه"),
        ("تکنیک بازخوانی فعال (Active Recall)", "مطالعه بدون روخوانی منفعل؛ حل تست‌های زمان‌دار", "کارنامه درصد تست‌زنی و زمان صرف‌شده به ازای هر تست"),
        ("مدیریت زمان در جلسات آزمون و استراتژی ضربدر-منها", "تمرین تکنیک زمان‌های نقصانی و عدم اتلاف وقت روی سوال سخت", "شبیه‌سازی یک آزمون جامع با تکنیک ضربدر-منها"),
        ("جمع‌بندی نهایی، تثبیت عادات و نقشه راه استمرار", "مرور ۱۲ روز گذشته و تدوین منشور انضباط تحصیلی شخصی", "ارسال منشور فردی موفقیت تحصیلی برای ماه‌های آینده")
    ]

    for i, (theme, obj, hw) in enumerate(themes, 1):
        days.append({
            "day": i,
            "theme": theme,
            "learning_objective": obj,
            "mindset_and_theory": f"پیوستگی در روز {i} تفاوت دانش‌آموزان عادی و پیشرو را رقم می‌زند.",
            "daily_exercises": [f"تمرین اختصاصی {theme}"],
            "homework_assignment": hw,
            "passing_criteria": f"ارسال گزارش شفاف و کامل از {hw}",
            "status": "active" if i == 1 else "pending",
            "submission": None,
            "evaluation": None
        })

    return {
        "student_name": student_name,
        "curriculum_goal": "دستیابی به حداکثر بازدهی، تمرکز و انضباط تحصیلی پایدار",
        "strengths_leveraged": ["انگیزه برای پیشرفت", "پشتکار در اجرای گام‌های روزانه"],
        "weaknesses_addressed": ["اهمال‌کاری", "حواس‌پرتی", "روش مطالعه غیراصولی"],
        "total_days": 12,
        "current_day": 1,
        "status": "active",
        "days": days
    }
