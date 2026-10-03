"""
Homework and Daily Task Evaluator Skill
----------------------------------------------------------------------
Evaluates student homework submissions against the day's passing criteria,
assigns a score, provides constructive feedback, and decides progression.
"""

from typing import Dict, Any, Optional
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from ai_utils import get_neuron_llm

logger = logging.getLogger("homework_evaluator")

HOMEWORK_EVALUATOR_SYSTEM_PROMPT = """
شما یک ارزیاب و کوچ آموزشی ساختاریافته، دقیق و منصف در برنامه ۱۲ روزه تحصیلی هستید.
وظیفه شما تحلیل دقیق و موشکافانه پاسخی است که دانش‌آموز به عنوان تکلیف روز ارسال کرده است.

### اصول و معیارهای اعتبارسنجی تکلیف:
۱. **تطبیق با معیار قبولی (Passing Criteria):** متن ارسالی دانش‌آموز را به دقت با صورت تکلیف و معیار قبولی همان روز مقایسه کنید.
۲. **ممنوعیت تأیید ادعاهای توخالی:**
   - اگر کاربر فقط ادعا کرده که کار را انجام داده اما محتوا، جدول، یا گزارش واقعی تمرین را نفرستاده است (مثل: «نوشتم»، «انجام دادم»، «حل شد»، «خوندم»، «حله»، «تموم شد» یا جملات کوتاه کلیشه‌ای):
     * قطعاً `passed: false` و `next_step_unlocked: false` تعیین کنید.
     * نمره پایین بدهید (بین ۱۰ تا ۲۵ از ۱۰۰).
     * در فیدبک با لحنی صمیمی و قاطع بنویسید که مربی نیاز دارد خود کار، جدول یا گزارش پارت‌های مطالعاتی را ببیند تا بتواند ارزیابی کند.
     * در `areas_for_improvement` دقیقاً مشخص کنید چه اطلاعاتی باید ارسال شود.
۳. **تکالیف معتبر و کامل:**
   - اگر تکلیف صادقانه، شامل جزییات خواسته شده، و منطبق بر معیار قبولی باشد:
     * نمره بالای ۶۰ (بین ۶۵ تا ۱۰۰) بدهید و `passed: true` تعیین کنید.
     * نقاط قوت را تحسین کرده و انگیزه برای روز بعد بدهید.
۴. **تکالیف ناقص یا سطحی:**
   - اگر متنی فرستاده ولی ناقص است یا به بخش‌های اصلی تکلیف پاسخ نداده:
     * نمره زیر ۶۰ بدهید و `passed: false` بگذارید و نکات لازم برای تکمیل را ذکر کنید.

### فرمت خروجی (JSON معتبر):
{
  "passed": false,
  "score": 25,
  "feedback": "بازخورد راهنما و مربی‌گری به دانش‌آموز و درخواست ارسال جزییات تمرین",
  "strengths_identified": ["نکات مثبت مشاهده‌شده"],
  "areas_for_improvement": ["موارد ناقص یا بخش‌های تکلیفی که باید ارسال شوند"],
  "next_step_unlocked": false
}
فقط و فقط یک شیء معتبر JSON بدون هیچ متن اضافی تولید کنید.
"""


def evaluate_school_homework(
    day_number: int,
    day_objective: str,
    homework_prompt: str,
    passing_criteria: str,
    submission: str,
    user_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Skill: Evaluates student's submitted homework for a specific day.
    Grades against passing criteria and logs full process info to terminal.
    """
    from app.agents.school_logger import log_tool_execution, log_homework_evaluation

    log_tool_execution("homework_evaluator (ارزیابی تکلیف روز)", {
        "day_number": day_number,
        "day_objective": day_objective,
        "homework_prompt": homework_prompt,
        "passing_criteria": passing_criteria,
        "submission": submission
    })

    if not submission or not submission.strip():
        res = {
            "passed": False,
            "score": 0,
            "feedback": "هیچ متنی به عنوان تکلیف ارسال نشده است. لطفاً گزارش، جدول یا پاسخ تمرین خود را بنویسید و ارسال کنید.",
            "strengths_identified": [],
            "areas_for_improvement": ["ارسال پاسخ و گزارش تمرین"],
            "next_step_unlocked": False
        }
        log_homework_evaluation(
            day=day_number,
            score=0,
            passed=False,
            feedback=res["feedback"],
            strengths=res["strengths_identified"],
            improvements=res["areas_for_improvement"],
            submission="(بدون متن)",
            criteria=passing_criteria,
            objective=day_objective,
            evaluation_mode="عدم ارسال متن تکلیف"
        )
        return res

    clean_sub = submission.strip()
    words = clean_sub.split()
    trivial_phrases = {
        "نوشتم", "انجام دادم", "کردم", "خوندم", "تموم شد", "انجام شد", "حل شد",
        "حله", "اوکیه", "همه رو انجام دادم", "همشو انجام دادم", "تانجام دادم",
        "تانجام دادم چک کن ببین درسته تکلیفم", "چک کن", "درسته", "انجام شد چک کن"
    }

    # Early rejection for trivial or empty claims without calling LLM
    if len(words) < 5 or clean_sub in trivial_phrases:
        res = {
            "passed": False,
            "score": 15,
            "feedback": (
                "❌ تکلیف شما تأیید نشد: صرف اعلام اینکه «کار را انجام دادم» یا «نوشتم» بدون ارائه محتوای تمرین، برای مربی کافی نیست! "
                "لطفاً متن کامل پاسخ‌ها، جدول زمانی خواسته‌شده یا گزارش ساعات مطالعه و چالش‌های امروز را تایپ و ارسال کنید تا بتوانم آن را بررسی و نمره‌گذاری کنم."
            ),
            "strengths_identified": ["اعلام آمادگی برای گزارش"],
            "areas_for_improvement": ["ارسال متن و جزییات مستند تکلیف"],
            "next_step_unlocked": False
        }
        log_homework_evaluation(
            day=day_number,
            score=15,
            passed=False,
            feedback=res["feedback"],
            strengths=res["strengths_identified"],
            improvements=res["areas_for_improvement"],
            submission=submission,
            criteria=passing_criteria,
            objective=day_objective,
            evaluation_mode="رد زودهنگام (ادعای توخالی / کمتر از ۵ کلمه)"
        )
        return res

    llm = get_neuron_llm()

    user_info = f"مشخصات دانش‌آموز: {user_profile.get('first_name', 'دانش‌آموز')}" if user_profile else ""

    input_payload = f"""
{user_info}
- شماره روز: {day_number}
- هدف روز: {day_objective}
- صورت تکلیف: {homework_prompt}
- معیار قبولی: {passing_criteria}

=== متن ارسالی دانش‌آموز برای تکلیف ===
{submission}
"""

    messages = [
        SystemMessage(content=HOMEWORK_EVALUATOR_SYSTEM_PROMPT),
        HumanMessage(content=input_payload)
    ]

    try:
        from app.agents.skills import safe_extract_text, extract_clean_json

        response = llm.invoke(messages)
        raw_text = safe_extract_text(response.content)
        result = extract_clean_json(raw_text)
        passed = bool(result.get("passed", False))
        result["next_step_unlocked"] = passed

        log_homework_evaluation(
            day=day_number,
            score=int(result.get("score", 0)),
            passed=passed,
            feedback=result.get("feedback", ""),
            strengths=result.get("strengths_identified", []),
            improvements=result.get("areas_for_improvement", []),
            submission=submission,
            criteria=passing_criteria,
            objective=day_objective,
            evaluation_mode="تحلیل و نمره‌گذاری هوشمند هوش مصنوعی"
        )
        return result
    except Exception as e:
        logger.error(f"Error evaluating homework: {e}", exc_info=True)
        # Safe fallback: never auto-pass on error or ambiguous text
        res = {
            "passed": False,
            "score": 35,
            "feedback": "در ارزیابی خودکار تکلیف مشکلی رخ داد یا متن ارسالی دارای ساختار کافی نبود. لطفاً گزارش دقیق تمرین را با جزییات بیشتر ارسال نمایید.",
            "strengths_identified": [],
            "areas_for_improvement": ["ارسال پاسخ‌های شفاف و ساختاریافته"],
            "next_step_unlocked": False
        }
        log_homework_evaluation(
            day=day_number,
            score=35,
            passed=False,
            feedback=res["feedback"],
            strengths=res["strengths_identified"],
            improvements=res["areas_for_improvement"],
            submission=submission,
            criteria=passing_criteria,
            objective=day_objective,
            evaluation_mode="فال‌بک ایمن به دلیل خطای پردازش"
        )
        return res


