"""
Final 12-Day Coaching Report Generator Skill
----------------------------------------------------------------------
Synthesizes the entire 12-day coaching cycle into a comprehensive
graduation and performance report.
"""

from typing import Dict, Any, Optional
import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from ai_utils import get_neuron_llm

logger = logging.getLogger("final_report_generator")

FINAL_REPORT_SYSTEM_PROMPT = """
شما مدیر آموزش و مربی ارشد تحصیلی هستید.
دانش‌آموز دوره فشرده ۱۲ روزه مربی‌گری تحصیلی و رشد فردی را با موفقیت پشت سر گذاشته است.
وظیفه شما بررسی گزارش ۱۲ روزه، تکالیف انجام شده و تدوین «کارنامه جامع تحول ۱۲ روزه» است.

### ساختار خروجی مورد انتظار (JSON معتبر):
{
  "student_name": "نام دانش‌آموز",
  "completion_date": "تاریخ اتمام دوره",
  "overall_score": 90,
  "executive_summary": "خلاصه جامع تحول و پیشرفت دانش‌آموز طی ۱۲ روز",
  "strengths_mastered": [
    "تسلط بر تکنیک پومودورو و مدیریت تمرکز",
    "کاهش اهمال‌کاری در درس‌های سخت"
  ],
  "habits_built": [
    "ثبت روزانه تکالیف و ساعات مطالعه",
    "مرور با جعبه لایتنر و تست‌زنی فعال"
  ],
  "remaining_challenges": [
    "نیاز به حفظ پیوستگی در روزهای تعطیل"
  ],
  "future_action_plan": [
    "گام اول برای ۳۰ روز آینده",
    "استراتژی آمادگی برای امتحانات ترم یا کنکور"
  ],
  "final_coach_message": "پیام پایانی الهام‌بخش مربی به دانش‌آموز"
}
فقط و فقط یک آبجکت معتبر JSON بدون متن اضافی برگردانید.
"""


def generate_final_coaching_report(
    user_profile: Optional[Dict[str, Any]],
    completed_plan: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Skill: Synthesizes completed 12-day school plan into a graduation report.
    """
    llm = get_neuron_llm()

    days_summary = []
    scores = []
    for d in completed_plan.get("days", []):
        eval_data = d.get("evaluation") or {}
        score = eval_data.get("score")
        if score is not None:
            try:
                scores.append(int(score))
            except (ValueError, TypeError):
                pass
        days_summary.append({
            "day": d.get("day"),
            "theme": d.get("theme"),
            "passed": d.get("status") == "completed",
            "score": score,
            "submission_excerpt": (d.get("submission") or "")[:150]
        })

    avg_score = round(sum(scores) / len(scores)) if scores else 85
    student_name = completed_plan.get("student_name") or (user_profile or {}).get("first_name") or "دانش‌آموز کوشا"

    payload = f"""
دانش‌آموز: {student_name}
میانگین نمرات تکالیف: {avg_score}/100
تعداد روزهای تکمیل‌شده: {len(days_summary)} روز

سوابق روزها:
{json.dumps(days_summary, ensure_ascii=False, indent=2)}
"""

    messages = [
        SystemMessage(content=FINAL_REPORT_SYSTEM_PROMPT),
        HumanMessage(content=payload)
    ]

    try:
        from app.agents.skills import safe_extract_text, extract_clean_json
        from app.agents.school_logger import log_graduation_report

        response = llm.invoke(messages)
        raw_text = safe_extract_text(response.content)
        report = extract_clean_json(raw_text)

        report["overall_score"] = avg_score
        log_graduation_report(report)
        return report
    except Exception as e:
        logger.error(f"Error generating final coaching report: {e}", exc_info=True)
        report = {
            "student_name": student_name,
            "overall_score": avg_score,
            "executive_summary": "تبریک! شما دوره ۱۲ روزه مربی‌گری تحصیلی را با موفقیت و تعهد کامل به پایان رساندید.",
            "strengths_mastered": ["تداوم در ارسال تکالیف", "بهبود انضباط شخصی در مطالعه"],
            "habits_built": ["برنامه‌ریزی روزانه", "پایش زمان تمرکز و مطالعه عمیق"],
            "remaining_challenges": ["تثبیت عادات در فواصل بلندمدت"],
            "future_action_plan": ["ادامه چرخه مطالعه پومودورو و مرورهای منظم هفتگی"],
            "final_coach_message": "موفقیت نتیجه اقدامات کوچک و مستمر است. همیشه به توانایی‌های خود باور داشته باش!"
        }
        try:
            from app.agents.school_logger import log_graduation_report
            log_graduation_report(report)
        except Exception:
            pass
        return report
