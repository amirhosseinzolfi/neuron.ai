"""
Goal and Milestone Planner Skill
----------------------------------------------------------------------
Deconstructs complex goals into actionable SMART milestones and micro-habits.
"""

from typing import Dict, Any, List
import json
from langchain_core.messages import SystemMessage, HumanMessage
from ai_utils import get_neuron_llm

GOAL_PLANNER_SYSTEM_PROMPT = """
شما یک کوچ بین‌المللی برنامه‌ریزی و رشد فردی (Life & Executive Coach) هستید.
وظیفه شما تجزیه هدف کاربر به گام‌های عملی، شفاف و قابل اندازه‌گیری (SMART) است.
خروجی باید دقیقاً یک JSON معتبر با ساختار زیر باشد:
{
  "goal_summary": "خلاصه بازتعریف‌شده هدف",
  "milestones": [
    {
      "step": 1,
      "title": "عنوان گام اول",
      "action_item": "عمل مشخص و روزانه",
      "timeframe": "بازه زمانی پیشنهادی"
    }
  ],
  "potential_obstacles": ["موانع ذهنی یا عملی احتمالی"],
  "accountability_metric": "معیار شفاف برای سنجش موفقیت"
}
فقط و فقط یک آبجکت معتبر JSON بدون متن اضافی برگردانید.
"""


def plan_goal_milestones(goal_text: str, user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Skill: Deconstructs an ambitious user goal into structured milestones.
    """
    if not goal_text:
        return {}

    llm = get_neuron_llm()
    profile_ctx = f"\nپروفایل کاربر: {json.dumps(user_profile, ensure_ascii=False)}" if user_profile else ""

    messages = [
        SystemMessage(content=GOAL_PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=f"هدف یا خواسته کاربر:{profile_ctx}\n\n{goal_text}")
    ]

    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())
    except Exception as e:
        return {
            "goal_summary": goal_text,
            "milestones": [],
            "potential_obstacles": [],
            "accountability_metric": "تلاش مستمر",
            "error": str(e)
        }

