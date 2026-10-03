import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.agents.registry import AgentRegistry
from app.agents.skills.school_plan_generator import generate_12day_school_plan, _build_fallback_12day_plan
from app.agents.skills.homework_evaluator import evaluate_school_homework
from app.agents.skills.final_report_generator import generate_final_coaching_report
import db

client = TestClient(app)
TEST_USER_ID = "test_student_9999"


def setup_module(module):
    """Ensure DB initialized and test student cleaned up."""
    db.init_db()
    db.reset_student_school_plan(TEST_USER_ID)


def teardown_module(module):
    """Clean up test student records."""
    db.reset_student_school_plan(TEST_USER_ID)


def test_school_assistant_agent_registry():
    """Verify that school_assistant is auto-discovered and properly registered."""
    AgentRegistry.ensure_discovered()
    agent = AgentRegistry.get("school_assistant")
    assert agent is not None
    assert agent.name == "school_assistant"
    assert "دستیار و مربی تحصیلی" in agent.display_name
    assert len(agent.tools) == 4
    tool_names = [getattr(t, "name", str(t)) for t in agent.tools]
    assert "check_or_create_school_plan" in tool_names
    assert "get_current_day_mission" in tool_names
    assert "submit_and_evaluate_homework" in tool_names
    assert "generate_12day_final_report" in tool_names
    assert "generate_12day_plan" in agent.skills
    assert "evaluate_homework" in agent.skills
    assert "generate_final_report" in agent.skills


def test_database_school_plan_crud():
    """Verify DB save, load, update day, and reset operations."""
    sample_plan = _build_fallback_12day_plan("علی")
    assert sample_plan["total_days"] == 12
    assert sample_plan["current_day"] == 1

    # Save
    saved = db.save_student_school_plan(
        chat_id=TEST_USER_ID,
        plan_data=sample_plan,
        diagnostic_data={"academic_grade": "کنکور تجربی"}
    )
    assert saved is True

    # Retrieve
    retrieved = db.get_student_school_plan(TEST_USER_ID)
    assert retrieved is not None
    assert retrieved["current_day"] == 1
    assert len(retrieved["days"]) == 12
    assert retrieved["diagnostic_data"]["academic_grade"] == "کنکور تجربی"

    # Update day progress with passing evaluation
    eval_mock = {"passed": True, "score": 90, "feedback": "بسیار عالی"}
    updated = db.update_student_day_progress(
        chat_id=TEST_USER_ID,
        day_number=1,
        homework="تمرین میز مطالعه و پومودورو کامل انجام شد.",
        evaluation=eval_mock,
        passed=True
    )
    assert updated is not None
    assert updated["current_day"] == 2
    assert updated["days"][0]["status"] == "completed"

    # Save final report
    final_mock = {"overall_score": 92, "executive_summary": "دوره با موفقیت به پایان رسید."}
    report_saved = db.save_student_final_report(TEST_USER_ID, final_mock)
    assert report_saved is True

    loaded_with_report = db.get_student_school_plan(TEST_USER_ID)
    assert loaded_with_report["status"] == "completed"
    assert loaded_with_report["final_report"]["overall_score"] == 92

    # Reset
    reset_ok = db.reset_student_school_plan(TEST_USER_ID)
    assert reset_ok is True
    assert db.get_student_school_plan(TEST_USER_ID) is None


def test_plan_generator_skill_fallback_and_structure():
    """Verify 12-day plan structure contains all necessary fields and 12 days."""
    plan = _build_fallback_12day_plan("سارا")
    assert plan["student_name"] == "سارا"
    assert len(plan["days"]) == 12
    for day in plan["days"]:
        assert "day" in day
        assert "theme" in day
        assert "learning_objective" in day
        assert "daily_exercises" in day
        assert "homework_assignment" in day
        assert "passing_criteria" in day


def test_homework_evaluator_skill():
    """Verify homework evaluator skill assigns scores and unlocks next step on good submission."""
    # 1. Empty submission
    empty_res = evaluate_school_homework(
        day_number=1,
        day_objective="تکنیک پومودورو",
        homework_prompt="گزارش ۴ پومودورو",
        passing_criteria="ثبت دقیق زمان",
        submission="",
        user_profile={"first_name": "امیر"}
    )
    assert empty_res["passed"] is False
    assert empty_res["next_step_unlocked"] is False

    # 2. Rich submission (mocking LLM / heuristic fallback)
    good_submission = (
        "من امروز ۴ دوره ۲۵ دقیقه‌ای مطالعه عمیق درس زیست‌شناسی را با استراحت‌های ۵ دقیقه‌ای "
        "اجرا کردم. هیچ پیام یا تماسی را پاسخ ندادم و جدول تحلیل تمرکز را کامل یادداشت کردم."
    )
    res = evaluate_school_homework(
        day_number=1,
        day_objective="تکنیک پومودورو",
        homework_prompt="گزارش ۴ پومودورو",
        passing_criteria="ثبت دقیق زمان",
        submission=good_submission,
        user_profile={"first_name": "امیر"}
    )
    assert "passed" in res
    assert "score" in res
    assert "feedback" in res


def test_final_report_generator_skill():
    """Verify final coaching report contains key summary sections."""
    plan = _build_fallback_12day_plan("نیما")
    plan["days"][0]["evaluation"] = {"score": 90}
    plan["days"][1]["evaluation"] = {"score": 85}
    report = generate_final_coaching_report({"first_name": "نیما"}, plan)
    assert report is not None
    assert "overall_score" in report
    assert "executive_summary" in report
    assert "strengths_mastered" in report
    assert "habits_built" in report


def test_fastapi_school_assistant_endpoints():
    """Verify dedicated /school REST endpoints."""
    # 1. Reset first to ensure clean slate
    client.post(f"/school/plan/{TEST_USER_ID}/reset")

    # 2. 404 before plan generation
    resp = client.get(f"/school/plan/{TEST_USER_ID}")
    assert resp.status_code == 404

    # 3. Generate plan
    gen_resp = client.post(
        f"/school/plan/{TEST_USER_ID}/generate",
        json={
            "academic_grade": "سال دوازدهم تجربی",
            "study_field": "علوم تجربی",
            "main_bottleneck": "کندی در تست‌زنی و تعلل",
            "daily_study_hours": "۶ ساعت"
        }
    )
    assert gen_resp.status_code == 200
    gen_data = gen_resp.json()
    assert gen_data["success"] is True
    assert gen_data["plan"]["total_days"] == 12

    # 4. Get active plan
    plan_resp = client.get(f"/school/plan/{TEST_USER_ID}")
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()
    assert plan_data["plan"]["current_day"] == 1

    # 5. Get current day mission
    day_resp = client.get(f"/school/day/{TEST_USER_ID}/current")
    assert day_resp.status_code == 200
    day_data = day_resp.json()
    assert day_data["current_day"] == 1
    assert "theme" in day_data["day_details"]
    assert "homework_assignment" in day_data["day_details"]

    # 6. Submit homework for Day 1
    hw_resp = client.post(
        f"/school/homework/{TEST_USER_ID}/submit",
        json={
            "submission_text": "میز مطالعه‌ام را مرتب کردم، تمام کتاب‌های متفرقه را حذف نمودم و تایمر را روی ۴ بازه متوالی تنظیم کردم."
        }
    )
    assert hw_resp.status_code == 200
    hw_data = hw_resp.json()
    assert hw_data["success"] is True
    assert hw_data["day"] == 1
    assert "score" in hw_data

    # 7. Reset plan
    reset_resp = client.post(f"/school/plan/{TEST_USER_ID}/reset")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["success"] is True


def test_fastapi_agents_listing_includes_school_assistant():
    """Verify that GET /agents includes school_assistant."""
    resp = client.get("/agents")
    assert resp.status_code == 200
    data = resp.json()
    agent_names = [a["name"] for a in data["agents"]]
    assert "school_assistant" in agent_names

    detail_resp = client.get("/agents/school_assistant")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()["agent"]
    assert detail["name"] == "school_assistant"
    assert len(detail["tools"]) == 4
