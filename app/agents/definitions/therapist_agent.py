"""
Therapist Agent Definition
----------------------------------------------------------------------
Clinical psychology and mental well-being agent for Neuron.
Encapsulates its own tools, skills, persona, and LangGraph workflow.
"""

from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import tool, BaseTool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.pregel import Pregel
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agents.base import BaseAgent, AgentState
from app.agents.registry import register_agent
from app.agents.skills.psych_analyzer import analyze_cognitive_patterns
from database.prompts import NEURON
from ai_utils import get_neuron_llm


# ── Agent Specific Tools ──────────────────────────────────────────────

@tool
def suggest_breathing_exercise(technique_name: str, duration_minutes: int = 3) -> str:
    """
    راهنمایی و اجرای تمرین‌های تنفسی آرامش‌بخش برای مهار اضطراب و استرس.
    تکنیک‌های معتبر: 'box_breathing' (تنفس مربعی ۴-۴-۴-۴)، '4-7-8' (آرامش عمیق)، 'diaphragmatic' (تنفس دیافراگمی).
    """
    exercises = {
        "box_breathing": "تکنیک تنفس مربعی: ۴ ثانیه دم عمیق، ۴ ثانیه حبس نفس، ۴ ثانیه بازدم آرام، ۴ ثانیه مکث. تکرار برای ۴ چرخه.",
        "4-7-8": "تکنیک ۴-۷-۸: ۴ ثانیه دم آرام از بینی، ۷ ثانیه حبس نفس، ۸ ثانیه بازدم کامل با صدای آرام از دهان.",
        "diaphragmatic": "تنفس دیافراگمی: یک دست روی سینه و یک دست روی شکم. تمرکز بر بالا آمدن شکم هنگام دم عمیق."
    }
    desc = exercises.get(technique_name.lower(), exercises["4-7-8"])
    return f"تمرین تنفسی فعال شد:\n{desc}\nمدت زمان پیشنهادی: {duration_minutes} دقیقه. لطفاً در وضعیت راحتی بنشینید و شروع کنید."


@tool
def log_mood_entry(mood_score: int, primary_feeling: str, notes: str = "") -> str:
    """
    ثبت وضعیت خلق‌وخوی فعلی کاربر در گزارش درمانی.
    mood_score: عدد بین ۱ (بسیار غمگین/مضطرب) تا ۱۰ (بسیار پرانرژی و آرام).
    primary_feeling: حس اصلی مثل اضطراب، امیدواری، خستگی، سردرگمی.
    notes: توضیحات کوتاه اضافی.
    """
    score_clamped = max(1, min(10, mood_score))
    return f"وضعیت خلق کاربر با موفقیت ثبت شد: نمره {score_clamped}/10 | حس غالب: {primary_feeling} | یادداشت: {notes or 'بدون یادداشت'}"


# ── Agent Class & Workflow ───────────────────────────────────────────

@register_agent
class TherapistAgent(BaseAgent):
    """
    Therapist Agent for cognitive and emotional wellness.
    Fully integrated with the user's Brain and Mem0 long-term memory.
    """
    name = "therapist"
    display_name = "روان‌درمانگر و مشاور نیورون"
    description = "مشاوره روانشناختی، کاهش اضطراب، تحلیل الگوهای افکار و تمرین‌های آرامش‌بخش ذهن."
    version = "1.0.0"

    @property
    def system_instruction(self) -> str:
        base_instruction = NEURON or "شما یک روانشناس بالینی خردمند، همدل و آگاه هستید."
        return (
            f"{base_instruction}\n\n"
            "### دستورالعمل‌های اختصاصی ایجنت درمانگر:\n"
            "۱. ابتدا احساسات کاربر را بدون قضاوت تأیید (Validate) کنید.\n"
            "۲. از سوالات سقراطی باز برای شناخت خطاهای فکری استفاده کنید.\n"
            "۳. در صورت وجود اضطراب بالا، از ابزار `suggest_breathing_exercise` کمک بگیرید.\n"
            "۴. همیشه به محتوای [مغز و سوابق کاربر] که در ابتدای پرامپت تزریق می‌شود توجه کنید و بدون اشاره فنی، صحبت‌ها را شخصی‌سازی کنید."
        )

    @property
    def tools(self) -> List[BaseTool]:
        return [suggest_breathing_exercise, log_mood_entry]

    @property
    def skills(self) -> Dict[str, Any]:
        return {
            "cognitive_pattern_analysis": analyze_cognitive_patterns
        }

    def build_graph(self, checkpointer: Optional[BaseCheckpointSaver] = None) -> Pregel:
        """
        Builds the LangGraph cyclical execution workflow:
        START -> agent_node -> (has tools? -> tools_node -> agent_node) -> END
        """
        llm = get_neuron_llm()
        llm_with_tools = llm.bind_tools(self.tools)

        def agent_node(state: AgentState) -> Dict[str, Any]:
            # 1. System instruction
            system_prompt = self.system_instruction

            # 2. Injected Brain Context (Profile + Tests + Mem0 Facts)
            brain_prompt = state.get("brain_prompt", "")
            if brain_prompt:
                system_prompt = f"{system_prompt}\n\n=== اطلاعات مغز کاربر (User Brain Context) ===\n{brain_prompt}"

            messages = [SystemMessage(content=system_prompt)] + list(state.get("messages", []))

            # 3. Call LLM
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

        # Build Graph
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", ToolNode(self.tools))

        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", should_continue, ["tools", END])
        workflow.add_edge("tools", "agent")

        return workflow.compile(checkpointer=checkpointer)

