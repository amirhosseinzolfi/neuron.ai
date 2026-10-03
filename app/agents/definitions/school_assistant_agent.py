"""
School & Academic Assistant Agent Definition
----------------------------------------------------------------------
12-Day Intensive Academic Coaching Agent for students.
Provides personalized daily coaching, exercise assignments, homework
grading, and progression tracking based on cognitive traits and psych tests.
"""

from typing import List, Dict, Any, Optional
import json
import logging
import contextvars

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool, BaseTool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.pregel import Pregel
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agents.base import BaseAgent, AgentState
from app.agents.session_handler import SessionMessageHandler
from app.agents.registry import register_agent
from app.agents.skills.school_plan_generator import generate_12day_school_plan
from app.agents.skills.homework_evaluator import evaluate_school_homework
from app.agents.skills.final_report_generator import generate_final_coaching_report
from app.agents.school_logger import (
    log_student_session_start,
    log_tool_execution,
    log_day_progression,
    log_graduation_report,
    log_brain_and_memory_context,
    log_turn_telemetry
)
from ai_utils import get_neuron_llm
import db

logger = logging.getLogger("school_assistant_agent")

active_student_id = contextvars.ContextVar("active_student_id", default="default")


# ── Agent Specific Tools ──────────────────────────────────────────────

@tool
def check_or_create_school_plan(
    academic_grade: Optional[str] = None,
    study_field: Optional[str] = None,
    main_bottleneck: Optional[str] = None,
    daily_study_hours: Optional[str] = None,
    user_id: Optional[str] = None
) -> str:
    """
    بررسی وضعیت برنامه تحصیلی ۱۲ روزه دانش‌آموز یا ایجاد برنامه جدید در صورت عدم وجود.
    اگر کاربر برنامه دارد، خلاصه روز فعلی برمی‌گردد.
    اگر برنامه ندارد، با دریافت مقطع تحصیلی، رشته، چالش اصلی و ساعت مطالعه روزانه برنامه ۱۲ روزه ایجاد و ذخیره می‌شود.
    """
    uid = user_id or active_student_id.get()
    existing_plan = db.get_student_school_plan(uid)

    if existing_plan and existing_plan.get("days"):
        cur_day = existing_plan.get("current_day", 1)
        status = existing_plan.get("status", "active")
        if status == "completed":
            return "دانش‌آموز گرامی، شما قبلاً دوره ۱۲ روزه را با موفقیت به پایان رسانده‌اید! می‌توانید کارنامه نهایی را دریافت کنید."
        day_info = next((d for d in existing_plan.get("days", []) if d.get("day") == cur_day), None)
        theme = day_info.get("theme", "نامشخص") if day_info else ""
        return f"برنامه تحصیلی فعال یافت شد: هم‌اکنون در روز {cur_day} از ۱۲ روز هستید. موضوع امروز: '{theme}'."

    # If parameters missing, prompt coach to ask them
    if not (academic_grade or study_field or main_bottleneck):
        return (
            "برنامه فعالی برای کاربر ثبت نشده است. لطفاً از کاربر اطلاعات پایه‌ای تحصیلی "
            "(مقطع تحصیلی، رشته یا هدف کنکور/امتحانات، بزرگترین مانع مثل اهمال‌کاری یا حواس‌پرتی، "
            "و میانگین ساعت مطالعه روزانه) را جویا شوید تا برنامه ۱۲ روزه اختصاصی تولید شود."
        )

    # Diagnostic data
    diag_data = {
        "academic_grade": academic_grade or "متوسطه/کنکور",
        "study_field": study_field or "عمومی",
        "main_bottleneck": main_bottleneck or "مدیریت زمان و تمرکز",
        "daily_study_hours": daily_study_hours or "۳ تا ۵ ساعت"
    }

    # Fetch user data from DB for personalization
    user_row = db.get_user(uid) or {}
    psych_profile = db.get_psychology_profile(uid) or {}
    tests = db.get_user_tests(uid) or []

    new_plan = generate_12day_school_plan(
        user_profile={**user_row, "psychology_profile": psych_profile},
        diagnostic_info=diag_data,
        psych_tests=tests
    )

    db.save_student_school_plan(uid, new_plan, diagnostic_data=diag_data, status="active")
    day_1 = new_plan.get("days", [{}])[0]
    return (
        f"✅ برنامه جامع ۱۲ روزه با موفقیت برای شما طراحی و ذخیره شد!\n"
        f"🎯 هدف دوره: {new_plan.get('curriculum_goal')}\n"
        f"📅 امروز روز ۱ است: '{day_1.get('theme')}'\n"
        f"📝 تکلیف امروز: {day_1.get('homework_assignment')}"
    )


@tool
def get_current_day_mission(user_id: Optional[str] = None) -> str:
    """
    دریافت درس، تمرین‌ها، اهداف و تکلیف روز فعال دانش‌آموز در برنامه ۱۲ روزه.
    """
    uid = user_id or active_student_id.get()
    plan = db.get_student_school_plan(uid)

    if not plan:
        return "هیچ برنامه فعالی وجود ندارد. ابتدا باید اطلاعات تحصیلی ثبت و برنامه ۱۲ روزه ایجاد شود."

    if plan.get("status") == "completed":
        return "دوره ۱۲ روزه با موفقیت تکمیل شده است. برای مشاهده گزارش نهایی درخواست کارنامه دهید."

    cur_day = plan.get("current_day", 1)
    day_info = next((d for d in plan.get("days", []) if d.get("day") == cur_day), None)

    if not day_info:
        return f"اطلاعات روز {cur_day} یافت نشد."

    exercises_text = "\n".join(f"  • {e}" for e in day_info.get("daily_exercises", []))
    return (
        f"📌 **ماموریت روز {cur_day} از ۱۲:**\n"
        f"🔹 **موضوع:** {day_info.get('theme')}\n"
        f"🎯 **هدف:** {day_info.get('learning_objective')}\n"
        f"💡 **نکته ذهنی/علمی:** {day_info.get('mindset_and_theory')}\n"
        f"⚡ **تمرین‌های روزانه:**\n{exercises_text}\n"
        f"📝 **تکلیف شبانه:** {day_info.get('homework_assignment')}\n"
        f"⚖️ **معیار قبولی:** {day_info.get('passing_criteria')}\n\n"
        f"پس از انجام تمرین، تکلیف خود را برای بررسی و باز شدن روز بعد ارسال کنید."
    )


@tool
def submit_and_evaluate_homework(submission_text: str, user_id: Optional[str] = None) -> str:
    """
    ثبت و ارزیابی تکلیف روز جاری دانش‌آموز.
    در صورت قبولی، دانش‌آموز به روز بعد هدایت می‌شود؛ در صورت عدم قبولی، راهنمایی برای اصلاح ارائه می‌گردد.
    """
    uid = user_id or active_student_id.get()
    plan = db.get_student_school_plan(uid)

    if not plan:
        return "ابتدا باید برنامه تحصیلی ۱۲ روزه ایجاد شود."

    cur_day = plan.get("current_day", 1)
    day_info = next((d for d in plan.get("days", []) if d.get("day") == cur_day), None)
    if not day_info:
        return f"اطلاعات روز {cur_day} یافت نشد."

    user_row = db.get_user(uid) or {}

    eval_result = evaluate_school_homework(
        day_number=cur_day,
        day_objective=day_info.get("learning_objective", ""),
        homework_prompt=day_info.get("homework_assignment", ""),
        passing_criteria=day_info.get("passing_criteria", ""),
        submission=submission_text,
        user_profile=user_row
    )

    passed = eval_result.get("passed", False)
    score = eval_result.get("score", 0)
    feedback = eval_result.get("feedback", "")

    # Update database progress
    updated_plan = db.update_student_day_progress(
        chat_id=uid,
        day_number=cur_day,
        homework=submission_text,
        evaluation=eval_result,
        passed=passed
    )

    if passed:
        new_day = (updated_plan or {}).get("current_day", cur_day + 1)
        if cur_day == 12 or (updated_plan and updated_plan.get("status") == "completed"):
            return (
                f"🎉 تبریک شگفت‌انگیز! تکلیف روز ۱۲ با نمره {score}/100 با موفقیت تأیید شد!\n"
                f"شما دوره ۱۲ روزه مربی‌گری تحصیلی را به پایان رساندید.\n"
                f"بازخورد مربی: {feedback}\n"
                f"اکنون می‌توانید کارنامه جامع نهایی خود را دریافت کنید."
            )
        return (
            f"✅ آفرین! تکلیف روز {cur_day} با نمره {score}/100 مورد تأیید قرار گرفت.\n"
            f"💡 بازخورد مربی: {feedback}\n\n"
            f"🔓 قفل روز {new_day} باز شد! برای شروع روز جدید آماده‌اید؟"
        )
    else:
        return (
            f"⚠️ تکلیف روز {cur_day} نیاز به تکمیل و بازنگری دارد (نمره: {score}/100).\n"
            f"نکات اصلاحی مربی: {feedback}\n"
            f"لطفاً تمرین را کامل‌تر انجام دهید و مجدداً ارسال کنید تا بتوانید به روز بعد صعود کنید."
        )


@tool
def generate_12day_final_report(user_id: Optional[str] = None) -> str:
    """
    تولید کارنامه و گزارش تحلیلی جامع پایان دوره ۱۲ روزه پس از اتمام تمامی روزها.
    """
    uid = user_id or active_student_id.get()
    plan = db.get_student_school_plan(uid)

    if not plan:
        return "هیچ برنامه‌ای برای این کاربر ثبت نشده است."

    # Check if final report already saved
    if plan.get("final_report"):
        rep = plan["final_report"]
        return (
            f"🎓 **کارنامه جامع پایان دوره ۱۲ روزه تحصیلی:**\n"
            f"🌟 **امتیاز کل:** {rep.get('overall_score')}/100\n"
            f"📋 **خلاصه تحول:** {rep.get('executive_summary')}\n"
            f"💪 **مهارت‌های تثبیت‌شده:** {', '.join(rep.get('strengths_mastered', []))}\n"
            f"🌱 **عادات پایدار ساخته‌شده:** {', '.join(rep.get('habits_built', []))}\n"
            f"🚀 **نقشه راه آینده:** {', '.join(rep.get('future_action_plan', []))}\n\n"
            f"💌 **پیام پایانی مربی:** {rep.get('final_coach_message')}"
        )

    user_row = db.get_user(uid) or {}
    report = generate_final_coaching_report(user_row, plan)
    db.save_student_final_report(uid, report)

    return (
        f"🎓 **کارنامه جامع پایان دوره ۱۲ روزه تحصیلی:**\n"
        f"🌟 **امتیاز کل دوره:** {report.get('overall_score')}/100\n"
        f"📋 **خلاصه عملکرد:** {report.get('executive_summary')}\n"
        f"💪 **نقاط قوت مسلط‌شده:** {', '.join(report.get('strengths_mastered', []))}\n"
        f"🌱 **عادات پایدار ساخته‌شده:** {', '.join(report.get('habits_built', []))}\n"
        f"🚀 **نقشه راه ۳۰ روز آینده:** {', '.join(report.get('future_action_plan', []))}\n\n"
        f"💌 **پیام پایانی مربی:** {report.get('final_coach_message')}"
    )


# ── Agent Class & Workflow ───────────────────────────────────────────

@register_agent
class SchoolAssistantAgent(BaseAgent):
    """
    School & Academic Coaching Agent for 12-day personal transformation.
    """
    name = "school_assistant"
    display_name = "دستیار و مربی تحصیلی ۱۲ روزه (School Assistant)"
    description = "مربی‌گری گام‌به‌گام تحصیلی ۱۲ روزه، برنامه‌ریزی مبتنی بر استعدادها و تست‌های روانشناسی، تمرین روزانه و ارزیابی تکالیف."
    version = "1.0.0"

    @property
    def system_instruction(self) -> str:
        return (
            "شما «مربی تحصیلی و دستیار رشد درسی نیورون» هستید؛ یک مربی باانگیزه، ساختاریافته، صمیمی، دلسوز و قاطع.\n"
            "ماموریت شما راهبری دانش‌آموز یا دانشجو در یک «دوره تحول و انضباط تحصیلی ۱۲ روزه» است.\n\n"
            "### روال کاری شما:\n"
            "۱. **بررسی وضعیت برنامه:** با ابزار `check_or_create_school_plan` وضعیت برنامه کاربر را بسنجید.\n"
            "۲. **پرسش‌های تشخیصی (در صورت عدم وجود برنامه):** اگر کاربر برنامه نداشت، پیش از ایجاد برنامه، ۲ تا ۳ سوال تشخیصی کلیدی (مقطع، رشته، بزرگترین چالش تحصیلی مثل تمرکز یا اهمال‌کاری، و ساعت مطالعه روزانه) بپرسید.\n"
            "۳. **ایجاد و ذخیره برنامه ۱۲ روزه:** پس از دریافت پاسخ‌ها، با ابزار `check_or_create_school_plan` برنامه اختصاصی ۱۲ روزه را بسازید.\n"
            "۴. **مربی‌گری روزانه:** برای روز فعال، از ابزار `get_current_day_mission` استفاده کرده، درس امروز را توضیح دهید، تمرین‌ها را تشریح کنید و در پایان تکلیف شبانه را مطالبه نمایید.\n"
            "۵. **ارزیابی تکالیف و ارتقای روز:** به محض ارسال پاسخ تکلیف توسط کاربر، از ابزار `submit_and_evaluate_homework` استفاده کنید. در صورت قبولی، تشویق کرده و روز بعد را باز کنید. در صورت نیاز به اصلاح، با راهنمایی دقیق بخواهید اصلاح کند.\n"
            "۶. **کارنامه جامع پایان دوره:** پس از اتمام روز ۱۲، با ابزار `generate_12day_final_report` کارنامه و نقشه راه آینده را ارائه دهید.\n"
            "۷. **شخصی‌سازی شناختی:** همیشه اطلاعات مغز کاربر (هوش‌ها، ویژگی‌های تست‌های روانشناسی و حافظه بلندمدت) را در لحن و توصیه‌های خود لحاظ کنید."
        )

    @property
    def tools(self) -> List[BaseTool]:
        return [
            check_or_create_school_plan,
            get_current_day_mission,
            submit_and_evaluate_homework,
            generate_12day_final_report
        ]

    @property
    def skills(self) -> Dict[str, Any]:
        return {
            "generate_12day_plan": generate_12day_school_plan,
            "evaluate_homework": evaluate_school_homework,
            "generate_final_report": generate_final_coaching_report
        }

    def build_graph(self, checkpointer: Optional[BaseCheckpointSaver] = None) -> Pregel:
        llm = get_neuron_llm()
        llm_with_tools = llm.bind_tools(self.tools)

        import time
        from app.agents.school_logger import log_brain_and_memory_context, log_turn_telemetry

        # Turn state tracking
        session_telemetry = {"ai_calls": 0, "in_tokens": 0, "out_tokens": 0, "start_time": time.time()}

        def coach_node(state: AgentState) -> Dict[str, Any]:
            uid = state.get("user_id") or "default"
            active_student_id.set(str(uid))

            messages_list = state.get("messages", [])

            # First entry in this turn: log session start & brain context
            if session_telemetry["ai_calls"] == 0:
                session_telemetry["start_time"] = time.time()
                last_msg = ""
                for m in reversed(messages_list):
                    if isinstance(m, HumanMessage):
                        last_msg = str(m.content)
                        break

                plan = db.get_student_school_plan(str(uid))
                cur_day = (plan or {}).get("current_day", 1)
                p_status = (plan or {}).get("status", "diagnostic")
                log_student_session_start(str(uid), last_msg, current_day=cur_day, status=p_status)
                log_brain_and_memory_context(state.get("brain_context", {}), self.system_instruction[:200])

            # Standard session message preparation with trim_messages & brain context
            full_messages = SessionMessageHandler.prepare_session_messages(
                messages=messages_list,
                system_instruction=self.system_instruction,
                brain_prompt=state.get("brain_prompt", ""),
                max_history=20
            )

            # Invoke LLM
            response = llm_with_tools.invoke(full_messages)
            session_telemetry["ai_calls"] += 1

            # Extract token usage metadata if available
            usage = getattr(response, "usage_metadata", None) or {}
            in_t = usage.get("input_tokens") or 0
            out_t = usage.get("output_tokens") or 0
            session_telemetry["in_tokens"] += in_t
            session_telemetry["out_tokens"] += out_t

            return {"messages": [response]}

        def route_tools_or_end(state: AgentState) -> str:
            """Standard LangGraph tools_condition routing with telemetry hook."""
            route = tools_condition(state)
            if route == END:
                _finalize_telemetry()
            return route

        def _finalize_telemetry():
            elapsed = time.time() - session_telemetry.get("start_time", time.time())
            ai_calls = session_telemetry.get("ai_calls", 1)
            in_t = session_telemetry.get("in_tokens", 0)
            out_t = session_telemetry.get("out_tokens", 0)
            log_turn_telemetry(ai_calls_count=ai_calls, input_tokens=in_t, output_tokens=out_t, duration_sec=elapsed)
            # Reset for next turn
            session_telemetry["ai_calls"] = 0
            session_telemetry["in_tokens"] = 0
            session_telemetry["out_tokens"] = 0

        workflow = StateGraph(AgentState)
        workflow.add_node("coach", coach_node)
        workflow.add_node("tools", ToolNode(self.tools))

        workflow.add_edge(START, "coach")
        workflow.add_conditional_edges("coach", route_tools_or_end, ["tools", END])
        workflow.add_edge("tools", "coach")

        return workflow.compile(checkpointer=checkpointer)

