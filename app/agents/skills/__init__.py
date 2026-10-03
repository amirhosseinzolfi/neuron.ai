"""
AI Skills Package
----------------------------------------------------------------------
Reusable, modular AI skills and cognitive processing routines.
"""

from typing import Any
import re
import json

from .psych_analyzer import analyze_cognitive_patterns
from .goal_planner import plan_goal_milestones
from .school_plan_generator import generate_12day_school_plan
from .homework_evaluator import evaluate_school_homework
from .final_report_generator import generate_final_coaching_report


def safe_extract_text(content: Any) -> str:
    """
    Safely extract a plain string from LLM message content.
    Handles str, list of content blocks (dicts/strings), and fallback objects.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(str(block.get("text", "")))
            elif isinstance(block, str):
                parts.append(block)
            elif hasattr(block, "text"):
                parts.append(str(block.text))
            elif hasattr(block, "content"):
                parts.append(str(block.content))
            else:
                parts.append(str(block))
        return "\n".join(p for p in parts if p).strip()
    return str(content).strip()


def extract_clean_json(text: str) -> Any:
    """
    Extracts and parses JSON from raw LLM output even if surrounded by
    markdown fences, thinking blocks, or conversational preamble.
    """
    if not text:
        raise ValueError("Empty text received for JSON extraction")

    # 1. Direct parse attempt
    clean_text = text.strip()
    try:
        return json.loads(clean_text)
    except Exception:
        pass

    # 2. Strip code fences
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    try:
        return json.loads(clean_text)
    except Exception:
        pass

    # 3. Regex slice from first '{' or '[' to last '}' or ']'
    m = re.search(r"(\{.*\}|\[.*\])", text, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    raise ValueError(f"Could not parse valid JSON from text: {text[:200]}")


__all__ = [
    "analyze_cognitive_patterns",
    "plan_goal_milestones",
    "generate_12day_school_plan",
    "evaluate_school_homework",
    "generate_final_coaching_report",
    "safe_extract_text",
    "extract_clean_json"
]
