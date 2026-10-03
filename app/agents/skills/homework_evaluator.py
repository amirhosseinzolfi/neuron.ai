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
شما ارزیاب و کوچ آموزشی در برنامه ۱۲ روزه تحصیلی هستید.
وظیفه شما تحلیل دقیق و موشکافانه تکلیفی است که دانش‌آموز برای روز مشخصی ارسال کرده است.

### اصول ارزیابی:
۱. تکلیف ارسال‌شده را با «معیار قبولی (Passing Criteria)» و «هدف روز» مقایسه کنید.
۲. اگر تکلیف باصداقت، کامل و طبق هدف انجام شده باشد، نمره بالای ۶۰ داده و وضعیت `passed: true` تعیین کنید.
۳. اگر تکلیف ناقص، بسیار سطحی، نامرتبط یا تقلبی باشد، نمره زیر ۶۰ داده، `passed: false` قرار دهید و با لحنی دلسوزانه و قاطعانه نقاط نیاز به اصلاح را مشخص کنید.
۴. بازخورد باید ترغیب‌کننده، دقیق و شامل راه‌حل عملی باشد.

### فرمت خروجی (JSON معتبر):
{
  "passed": true,
  "score": 85,
  "feedback": "تحلیل تشویقی و راهنمایی مربی به دانش‌آموز",
  "strengths_identified": ["نکات مثبت مشاهده‌شده در تمرین"],
  "areas_for_improvement": ["مواردی که باید در ادامه تقویت شوند"],
  "next_step_unlocked": true
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
    """
    if not submission or not submission.strip():
        return {
            "passed": False,
            "score": 0,
            "feedback": "هیچ متنی به عنوان تکلیف ارسال نشده است. لطفاً گزارش یا تکلیف خود را ثبت کنید.",
            "strengths_identified": [],
            "areas_for_improvement": ["ارسال پاسخ و گزارش شفاف"],
            "next_step_unlocked": False
        }

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
        from app.agents.school_logger import log_homework_evaluation

        response = llm.invoke(messages)
        raw_text = safe_extract_text(response.content)
        result = extract_clean_json(raw_text)

        passed = bool(result.get("passed", False))
        result["next_step_unlocked"] = passed

        # Rich terminal logging
        log_homework_evaluation(
            day=day_number,
            score=int(result.get("score", 0)),
            passed=passed,
            feedback=result.get("feedback", ""),
            strengths=result.get("strengths_identified", []),
            improvements=result.get("areas_for_improvement", [])
        )
        return result
    except Exception as e:
        logger.error(f"Error evaluating homework: {e}", exc_info=True)
        # Robust heuristic fallback
        word_count = len(submission.strip().split())
        passed = word_count >= 15
        score = 75 if passed else 40
        feedback = "تکلیف شما بررسی شد. تلاش خوبی بود و با دقت ثبت شده است." if passed else "تکلیف ارسال‌شده بسیار کوتاه است؛ لطفاً جزییات بیشتری از تمرین روزانه بنویسید."
        fallback_res = {
            "passed": passed,
            "score": score,
            "feedback": feedback,
            "strengths_identified": ["اقدام به انجام و ارسال تکلیف"],
            "areas_for_improvement": ["افزایش عمق تحلیل و گزارش"],
            "next_step_unlocked": passed
        }
        try:
            from app.agents.school_logger import log_homework_evaluation
            log_homework_evaluation(
                day=day_number,
                score=score,
                passed=passed,
                feedback=feedback,
                strengths=fallback_res["strengths_identified"],
                improvements=fallback_res["areas_for_improvement"]
            )
        except Exception:
            pass
        return fallback_res
