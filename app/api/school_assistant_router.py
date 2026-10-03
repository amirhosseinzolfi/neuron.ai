"""
School Assistant FastAPI Router
----------------------------------------------------------------------
Dedicated endpoints for managing 12-day student school plans, daily missions,
homework submission and grading, and final graduation reports.
Prefix: /school
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

import db
from app.services.brain_service import get_brain_service
from app.agents.skills.school_plan_generator import generate_12day_school_plan
from app.agents.skills.homework_evaluator import evaluate_school_homework
from app.agents.skills.final_report_generator import generate_final_coaching_report

router = APIRouter(prefix="/school", tags=["School Assistant"])


# ── Request / Response Models ─────────────────────────────────────────

class PlanGenerationRequest(BaseModel):
    academic_grade: Optional[str] = Field("متوسطه/کنکور", description="مقطع تحصیلی دانش‌آموز")
    study_field: Optional[str] = Field("عمومی/تجربی/ریاضی/انسانی", description="رشته یا گروه آزمایشی")
    main_bottleneck: Optional[str] = Field("اهمال‌کاری و تمرکز", description="بزرگترین چالش مطالعه")
    daily_study_hours: Optional[str] = Field("۴ ساعت", description="میانگین ساعات مطالعه در دسترس")
    custom_goals: Optional[str] = Field(None, description="اهداف خاص مدنظر دانش‌آموز")


class HomeworkSubmissionRequest(BaseModel):
    submission_text: str = Field(..., min_length=5, description="متن کامل تکلیف، پاسخ‌ها یا گزارش تمرین روزانه")


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("/plan/{user_id}", summary="Get Student 12-Day Plan")
async def get_student_plan(user_id: str):
    """
    Retrieve the active 12-day academic coaching plan and progress for a user.
    """
    plan = db.get_student_school_plan(user_id)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f"No active 12-day school plan found for user '{user_id}'. You can generate one via POST /school/plan/{user_id}/generate"
        )
    return {
        "success": True,
        "user_id": user_id,
        "plan": plan
    }


@router.post("/plan/{user_id}/generate", summary="Generate or Initialize 12-Day Plan")
async def generate_plan_endpoint(user_id: str, request: PlanGenerationRequest):
    """
    Generate and save a personalized 12-day coaching plan using brain context
    (psychological tests, demographics, and Mem0 memories).
    """
    brain_service = get_brain_service()
    snapshot = brain_service.get_user_brain_snapshot(user_id=user_id, memory_limit=5)

    diag_data = {
        "academic_grade": request.academic_grade,
        "study_field": request.study_field,
        "main_bottleneck": request.main_bottleneck,
        "daily_study_hours": request.daily_study_hours,
        "custom_goals": request.custom_goals
    }

    try:
        new_plan = generate_12day_school_plan(
            user_profile=snapshot.get("profile", {}),
            diagnostic_info=diag_data,
            psych_tests=snapshot.get("psychology_tests", []),
            memories=snapshot.get("long_term_memories", [])
        )

        saved = db.save_student_school_plan(
            chat_id=user_id,
            plan_data=new_plan,
            diagnostic_data=diag_data,
            status="active"
        )

        if not saved:
            raise HTTPException(status_code=500, detail="Failed to persist plan to database.")

        return {
            "success": True,
            "user_id": user_id,
            "message": "12-day personalized school plan successfully generated.",
            "plan": new_plan
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating plan: {str(e)}")


@router.get("/day/{user_id}/current", summary="Get Current Day Mission")
async def get_current_day_mission_endpoint(user_id: str):
    """
    Get the lesson, exercises, and homework prompt for the student's active day.
    """
    plan = db.get_student_school_plan(user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No active plan found for this student.")

    cur_day = plan.get("current_day", 1)
    day_info = next((d for d in plan.get("days", []) if d.get("day") == cur_day), None)

    if not day_info:
        raise HTTPException(status_code=404, detail=f"Day {cur_day} details not found in plan.")

    return {
        "success": True,
        "user_id": user_id,
        "current_day": cur_day,
        "total_days": plan.get("total_days", 12),
        "status": plan.get("status", "active"),
        "day_details": day_info
    }


@router.post("/homework/{user_id}/submit", summary="Submit & Evaluate Daily Homework")
async def submit_homework_endpoint(user_id: str, request: HomeworkSubmissionRequest):
    """
    Submit homework for the current active day.
    The evaluator skill grades the submission. If passed, automatically advances to the next day!
    """
    plan = db.get_student_school_plan(user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No active plan found for this student.")

    cur_day = plan.get("current_day", 1)
    day_info = next((d for d in plan.get("days", []) if d.get("day") == cur_day), None)
    if not day_info:
        raise HTTPException(status_code=404, detail=f"Day {cur_day} not found.")

    user_row = db.get_user(user_id) or {}

    try:
        eval_result = evaluate_school_homework(
            day_number=cur_day,
            day_objective=day_info.get("learning_objective", ""),
            homework_prompt=day_info.get("homework_assignment", ""),
            passing_criteria=day_info.get("passing_criteria", ""),
            submission=request.submission_text,
            user_profile=user_row
        )

        passed = eval_result.get("passed", False)
        updated_plan = db.update_student_day_progress(
            chat_id=user_id,
            day_number=cur_day,
            homework=request.submission_text,
            evaluation=eval_result,
            passed=passed
        )

        return {
            "success": True,
            "user_id": user_id,
            "day": cur_day,
            "passed": passed,
            "score": eval_result.get("score"),
            "feedback": eval_result.get("feedback"),
            "strengths": eval_result.get("strengths_identified", []),
            "areas_for_improvement": eval_result.get("areas_for_improvement", []),
            "next_day_unlocked": passed,
            "new_current_day": (updated_plan or {}).get("current_day", cur_day),
            "plan_status": (updated_plan or {}).get("status", "active")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error evaluating homework: {str(e)}")


@router.get("/report/{user_id}", summary="Get Final Graduation Report")
async def get_final_report_endpoint(user_id: str):
    """
    Get the 12-day graduation and achievement report.
    Generates it on the fly if Day 12 is completed and report was not saved yet.
    """
    plan = db.get_student_school_plan(user_id)
    if not plan:
        raise HTTPException(status_code=404, detail="No school plan found for this user.")

    # If already generated
    if plan.get("final_report"):
        return {
            "success": True,
            "user_id": user_id,
            "report": plan["final_report"]
        }

    # Generate report
    user_row = db.get_user(user_id) or {}
    try:
        report = generate_final_coaching_report(user_row, plan)
        db.save_student_final_report(user_id, report)
        return {
            "success": True,
            "user_id": user_id,
            "report": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating final report: {str(e)}")


@router.post("/plan/{user_id}/reset", summary="Reset Student School Plan")
async def reset_plan_endpoint(user_id: str):
    """
    Reset a student's school plan to start the 12-day program fresh.
    """
    success = db.reset_student_school_plan(user_id)
    return {
        "success": success,
        "user_id": user_id,
        "message": "Student school plan has been reset."
    }

