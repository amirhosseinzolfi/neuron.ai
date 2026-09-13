"""
Life & Habit Coach Agent Definition
----------------------------------------------------------------------
Executive coaching, habit formation, and goal execution agent for Neuron.
"""

from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import tool, BaseTool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.pregel import Pregel
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agents.base import BaseAgent, AgentState
from app.agents.registry import register_agent
from app.agents.skills.goal_planner import plan_goal_milestones
from ai_utils import get_neuron_llm


# ── Agent Specific Tools ──────────────────────────────────────────────

@tool
def create_actionable_task(title: str, priority: str = "medium", category: str = "growth") -> str:
    """
    ثبت یک اقدام یا تسک مشخص در برنامه کاربر.
    title: عنوان دقیق کار.
    priority: اولویت ('high', 'medium', 'low').
    category: دسته‌بندی ('growth', 'health', 'career', 'routine').
    """
    return f"تسک جدید با موفقیت به برنامه شما افزوده شد: '{title}' [اولویت: {priority} | دسته: {category}]"


@tool
def track_habit_streak(habit_name: str, completed_today: bool) -> str:
    """
    ثبت وضعیت انجام یک عادت روزانه برای حفظ تداوم (Streak).
    habit_name: نام عادت (مثلاً مطالعه ۲۰ دقیقه، ورزش صبحگاهی).
    completed_today: آیا امروز انجام شد؟ (True/False).
    """
    status = "انجام شد ✅" if completed_today else "انجام نشد ❌"
    return f"عادت '{habit_name}' برای امروز ثبت شد: {status}. حفظ پیوستگی مهم‌ترین عامل موفقیت شماست."


# ── Agent Class & Workflow ───────────────────────────────────────────

@register_agent
class LifeCoachAgent(BaseAgent):
    """
    Life and Productivity Coach Agent.
    Specializes in goal breakdown, accountability, and daily routines.
    """
    name = "life_coach"
    display_name = "مربی رشد فردی و عادت‌ها (Life Coach)"
    description = "برنامه‌ریزی اهداف، تبدیل اهداف به اقدامات روزانه، ایجاد نظم و انگیزه برای اقدام."
    version = "1.0.0"

    @property
    def system_instruction(self) -> str:
        return (
            "شما یک مربی (Coach) پرانرژی، ساختاریافته، دقیق و الهام‌بخش هستید.\n"
            "ماموریت شما کمک به کاربر برای عبور از اهمال‌کاری و حرکت به سوی اهدافش است.\n\n"
            "### اصول مربیگری شما:\n"
            "۱. هدف‌های بزرگ و مبهم کاربر را با مهارت `goal_planning` به گام‌های کوچک و فوری تبدیل کنید.\n"
            "۲. برای هر هدف حداقل یک اقدام شفاف ۲۴ ساعته تعیین کرده و از ابزار `create_actionable_task` استفاده کنید.\n"
            "۳. پیوسته کاربر را در قبال قول‌هایی که می‌دهد مسئولیت‌پذیر (Accountable) نگه دارید.\n"
            "۴. از اطلاعات مغز کاربر (سوابق، تست‌ها و علایق) برای انتخاب بهترین استراتژی انگیزش بهره ببرید."
        )

    @property
    def tools(self) -> List[BaseTool]:
        return [create_actionable_task, track_habit_streak]

    @property
    def skills(self) -> Dict[str, Any]:
        return {
            "goal_planning": plan_goal_milestones
        }

    def build_graph(self, checkpointer: Optional[BaseCheckpointSaver] = None) -> Pregel:
        llm = get_neuron_llm()
        llm_with_tools = llm.bind_tools(self.tools)

        def coach_node(state: AgentState) -> Dict[str, Any]:
            system_prompt = self.system_instruction
            brain_prompt = state.get("brain_prompt", "")
            if brain_prompt:
                system_prompt = f"{system_prompt}\n\n=== اطلاعات مغز کاربر (User Brain Context) ===\n{brain_prompt}"

            messages = [SystemMessage(content=system_prompt)] + list(state.get("messages", []))
            response = llm_with_tools.invoke(messages)
            return {"messages": [response]}

        def should_continue(state: AgentState) -> str:
            messages = state.get("messages", [])
            if not messages:
                return END
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return "tools"
            return END

        workflow = StateGraph(AgentState)
        workflow.add_node("coach", coach_node)
        workflow.add_node("tools", ToolNode(self.tools))

        workflow.add_edge(START, "coach")
        workflow.add_conditional_edges("coach", should_continue, ["tools", END])
        workflow.add_edge("tools", "coach")

        return workflow.compile(checkpointer=checkpointer)

