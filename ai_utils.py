"""
ai_utils.py
----------------------------------------------------------------------
All AI/LangChain-related utilities (LLM client, prompts, history, orchestration)
+ LLM debug trace capture for Rich-table rendering in psychology_test.py

ENV:
  OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL
  AI_HISTORY_SUMMARY_INTERVAL, AI_HISTORY_RETENTION, AI_HISTORY_TRIM_THRESHOLD
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from functools import lru_cache
from typing import Any, Dict, List, Optional
from logging.handlers import RotatingFileHandler
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from langchain_openai import ChatOpenAI
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from telegram_text_optimizer import format_analysis_for_telegram
import db

from prompts import (
    CHATBOT_PERSONA,
    COMBINED_SYSTEM_INSTRUCTION,
    ANALYSIS_SUMMARY_PROMPT,
    RESULT_CHATBOT_PERSONA,
    RESULT_ANALYZE_CHATBOT_PERSONA,
    IMAGE_PROMPT_SYSTEM,
    IMAGE_PROMPT_GENERATION_TEMPLATE,
    HISTORY_SUMMARIZATION_PROMPT,
    PROFILE_UPDATER,
)

# -----------------------------------------------------------------------------
# Logging (JSONL telemetry)
# -----------------------------------------------------------------------------

LOG = logging.getLogger("ai_utils")
if not LOG.handlers:
    logging.basicConfig(level=logging.INFO, format="%(message)s", datefmt="[%X]")
    LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(LOG_DIR, exist_ok=True)
    JSONL_PATH = os.path.join(LOG_DIR, "blue_ai_logs.jsonl")

    class JSONLineFormatter(logging.Formatter):
        def format(self, record):
            try:
                return json.dumps(
                    {"timestamp": time.time(), "level": record.levelname, "logger": record.name, "message": record.getMessage()},
                    ensure_ascii=False,
                )
            except Exception:
                return json.dumps({"timestamp": time.time(), "level": record.levelname, "message": record.getMessage()})

    h = RotatingFileHandler(JSONL_PATH, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    h.setFormatter(JSONLineFormatter())
    h.setLevel(logging.INFO)
    LOG.addHandler(h)
else:
    JSONL_PATH = None


def _write_event(event: Dict[str, Any]) -> None:
    if not JSONL_PATH:
        return
    try:
        event.setdefault("ts", time.time())
        with open(JSONL_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Config (exported so UI can show model/base)
# -----------------------------------------------------------------------------

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:15207/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "324")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

HISTORY_TRIM_THRESHOLD = int(os.getenv("AI_HISTORY_TRIM_THRESHOLD", "15"))
HISTORY_RETENTION = int(os.getenv("AI_HISTORY_RETENTION", "5"))
SUMMARY_INTERVAL = int(os.getenv("AI_HISTORY_SUMMARY_INTERVAL", "5"))


# -----------------------------------------------------------------------------
# LLM (singleton)
# -----------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    LOG.info(f"LLM init: model={OPENAI_MODEL} base_url={OPENAI_BASE_URL}")
    return ChatOpenAI(base_url=OPENAI_BASE_URL, model_name=OPENAI_MODEL, temperature=0.6, api_key=OPENAI_API_KEY)


# -----------------------------------------------------------------------------
# Conversation helpers
# -----------------------------------------------------------------------------

def _now_ts() -> float:
    return time.time()


def standard_message(role: str, content: str, *, context: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {"id": str(uuid.uuid4()), "role": role.lower(), "content": content or "", "ts": _now_ts(), "context": context or "", "meta": meta or {}}


def add_message(
    state: Dict[str, Any],
    role: str,
    content: str,
    *,
    context: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    persist_jsonl: bool = False,
) -> Dict[str, Any]:
    try:
        role = (role or "").lower()
        msg = standard_message(role, content, context=context, meta=meta)
        if role == "internal":
            if persist_jsonl:
                _write_event({"type": "internal_payload", "message": msg})
            return msg

        history = state.setdefault("conversation_history", [])
        last = next((m for m in reversed(history) if m.get("role") != "internal"), None)
        if role == "assistant" and last and last.get("role") == "assistant" and last.get("content", "").strip() == content.strip():
            return last

        history.append(msg)
        state["message_count"] = len(history)

        if len(history) > HISTORY_TRIM_THRESHOLD:
            state["conversation_history"] = history[-HISTORY_RETENTION:]

        if persist_jsonl:
            _write_event({"type": "history_message", "message": msg})
        return msg
    except Exception:
        fallback = {"role": role, "content": content, "context": context or ""}
        state.setdefault("conversation_history", []).append(fallback)
        state["message_count"] = len(state["conversation_history"])
        return fallback


def _conversation_history_to_messages(state: Dict[str, Any]) -> List[Any]:
    out: List[Any] = []
    for m in state.get("conversation_history", []):
        if m.get("role") == "user":
            out.append(HumanMessage(content=m.get("content", "")))
        elif m.get("role") == "assistant":
            out.append(AIMessage(content=m.get("content", "")))
    return out


def _build_system_instruction(state: Dict[str, Any], base_system: str) -> str:
    parts = [base_system]
    if state.get("user_info"):
        parts.append("\n\n[UserProfile]\n" + str(state["user_info"]))
    conv_summary = state.get("summary") or state.get("history_summary", "")
    if conv_summary:
        parts.append("\n\n[ConversationSummary]\n" + str(conv_summary))
    return "\n".join(parts)


# -----------------------------------------------------------------------------
# History summarization
# -----------------------------------------------------------------------------

def _should_summarize(state: Dict[str, Any]) -> bool:
    n = len(state.get("conversation_history", []))
    return n >= SUMMARY_INTERVAL and n % SUMMARY_INTERVAL == 0


def handle_history_summarization(state: Dict[str, Any]) -> None:
    if _should_summarize(state):
        msgs = [m for m in state.get("conversation_history", []) if m.get("role") in ("user", "assistant")]
        if len(msgs) < SUMMARY_INTERVAL:
            return
        recent = msgs[-SUMMARY_INTERVAL:]
        conv = "\n".join(f"{m['role']}: {m['content']}" for m in recent)
        prev = state.get("summary", "") or ""

        system_content = "You are a helpful assistant that summarizes conversations."
        if prev:
            system_content += "\n\n[Previous Summary]\n" + prev + "\n\nIntegrate the previous summary coherently."

        # record lengths before trimming for debug
        original_history_len = len(state.get("conversation_history", []))

        llm = get_llm()
        try:
            summary = llm.invoke([SystemMessage(content=system_content), HumanMessage(content=HISTORY_SUMMARIZATION_PROMPT.format(conversation=conv))]).content.strip()
            # store results and trim history
            state["summary"] = summary
            state["history_summary"] = summary
            state["conversation_history"] = state.get("conversation_history", [])[-HISTORY_RETENTION:]
            trimmed_to = len(state.get("conversation_history", []))
            _write_event({"type": "conversation_summary", "summary": summary, "message_count": trimmed_to})
            # store debug snapshot so UI can render system/user/response + trimming info
            try:
                _store_last_debug(state, call="history_summarization", system=system_content, user=conv, messages=len(recent), response=summary)
            except Exception:
                pass
            # store explicit extra debug fields
            dbg = state.setdefault("_debug", {})
            dbg["history_summary"] = summary
            dbg["history_trim_info"] = {"from": original_history_len, "to": trimmed_to, "retention": HISTORY_RETENTION}
        except Exception as e:
            LOG.error(f"History summarization failed: {e}")
            _write_event({"type": "conversation_summary_error", "error": str(e)})
            # store debug snapshot on failure
            try:
                _store_last_debug(state, call="history_summarization_error", system=system_content, user=conv, messages=len(recent), response=str(e))
            except Exception:
                pass
    elif len(state.get("conversation_history", [])) > HISTORY_TRIM_THRESHOLD:
        # trimming due to threshold - record debug info
        original = len(state.get("conversation_history", []))
        state["conversation_history"] = state.get("conversation_history", [])[-HISTORY_RETENTION:]
        trimmed = len(state.get("conversation_history", []))
        _write_event({"type": "history_trim", "from": original, "to": trimmed, "retention": HISTORY_RETENTION})
        try:
            _store_last_debug(state, call="history_trim", system="history_trim_process", user=f"trim from {original} to {trimmed}", messages=0, response=f"trimmed to {trimmed}")
        except Exception:
            pass


def update_user_profile_with_ai(chat_id: int, test_result_text: str):
    """
    Updates a user's profile using AI by combining their current information
    with new test results, with detailed terminal logging.
    """
    console = Console()
    console.rule(f"[bold blue]🤖 AI Profile Update for chat_id: {chat_id}", style="blue")

    try:
        # 1. Get current user data
        user_data = db.get_user(chat_id)
        if not user_data:
            console.log(f"[bold red]Error: No user found for chat_id: {chat_id}[/bold red]")
            return

        current_info = user_data.get("information") or ""

        # 2. Prepare the prompt for the AI
        prompt = (
            f"**User's Current Information:**\n{current_info}\n\n"
            f"**New Psychology Test Result:**\n{test_result_text}\n\n"
            "Based on the new test result, please update the user's information."
        )

        # 3. Call the AI
        llm = get_llm()
        system_message = SystemMessage(content=PROFILE_UPDATER)
        human_message = HumanMessage(content=prompt)
        
        console.log("[yellow]Invoking LLM for profile update...[/yellow]")
        response = llm.invoke([system_message, human_message])
        updated_info = response.content.strip()

        # 4. Log the interaction in tables
        # Table for before and after
        profile_table = Table(title="📄 User Profile Evolution", show_header=True, header_style="bold magenta")
        profile_table.add_column("Version", style="cyan")
        profile_table.add_column("Content", style="white")
        profile_table.add_row("📝 Previous Profile", current_info)
        profile_table.add_row("✨ Updated Profile", updated_info)
        console.print(profile_table)

        # Table for AI interaction
        ai_table = Table(title="🧠 AI Prompt & Response", show_header=True, header_style="bold green")
        ai_table.add_column("Component", style="cyan")
        ai_table.add_column("Details", style="white")
        ai_table.add_row("SYSTEM Prompt", PROFILE_UPDATER)
        ai_table.add_row("HUMAN Prompt", prompt)
        ai_table.add_row("AI Response", updated_info)
        console.print(ai_table)

        # 5. Save the updated information to the database
        db.update_user_profile(chat_id, information=updated_info)
        console.log(f"[bold green]✅ Successfully updated profile for chat_id: {chat_id} in the database.[/bold green]")

        # 6. Log the event to JSONL
        _write_event({
            "type": "ai_profile_update",
            "chat_id": chat_id,
            "previous_info_length": len(current_info),
            "new_info_length": len(updated_info)
        })

    except Exception as e:
        console.log(f"[bold red]❌ Failed to update user profile with AI for chat_id: {chat_id}. Error: {e}[/bold red]")
        _write_event({
            "type": "ai_profile_update_error",
            "chat_id": chat_id,
            "error": str(e)
        })
    finally:
        console.rule(style="blue")


# -----------------------------------------------------------------------------
# Question helpers & parsing
# -----------------------------------------------------------------------------

def normalize_option_texts(options: List[Any]) -> List[str]:
    return [(o.get("text") if isinstance(o, dict) and "text" in o else str(o)).strip() for o in (options or [])]


def build_default_question_text(user_name: str, question: str, options: List[Any], qnum: int, total: int, last_answer: Optional[Dict[str, Any]] = None) -> str:
    opts = normalize_option_texts(options)
    head = f"{user_name} عزیز، سوال {qnum}/{total}:\n{question}"
    if last_answer:
        sel = last_answer.get("selected_option", "")
        head = f"{user_name} عزیز، با توجه به پاسخ قبلی شما («{sel}»)، سوال {qnum}/{total}:\n{question}"
    lines = "\n".join(f"{i+1}. {t}" for i, t in enumerate(opts))
    return f"{head}\n\nگزینه‌ها:\n{lines}\n\nلطفاً شماره گزینه یا متن آن را بفرستید."


def extract_json(payload: str) -> Optional[Dict[str, Any]]:
    s = (payload or "").strip()
    try:
        data = json.loads(s)
        return data if isinstance(data, dict) else None
    except Exception:
        pass
    if "```" in s:
        for part in s.split("```"):
            part = part.strip()
            if not part:
                continue
            try:
                data = json.loads(part)
                if isinstance(data, dict):
                    return data
            except Exception:
                continue
    try:
        start = s.index("{"); end = s.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(s[start : end + 1])
            return data if isinstance(data, dict) else None
    except Exception:
        return None
    return None


# -----------------------------------------------------------------------------
# Debug trace helper (stored on state for Rich rendering by the UI)
# -----------------------------------------------------------------------------

def _store_last_debug(state: Dict[str, Any], *, call: str, system: str, user: str, messages: int, response: str) -> None:
    # Build a textual dump of the conversation history (role: content per line)
    messages_full = ""
    try:
        conv = state.get("conversation_history", []) if isinstance(state, dict) else []
        if conv:
            lines = []
            for m in conv:
                role = m.get("role", "")
                content = m.get("content", "") or ""
                lines.append(f"{role}: {content}")
            messages_full = "\n".join(lines)
    except Exception:
        messages_full = ""

    state.setdefault("_debug", {})["last_call"] = {
        "call": call,
        "system": system,
        "user": user,
        "messages": messages,
        "messages_full": messages_full,  # full conversation lines
        "response": response,
        "model": OPENAI_MODEL,
        "base_url": OPENAI_BASE_URL,
        "ts": time.time(),
    }


# -----------------------------------------------------------------------------
# Public AI calls
# -----------------------------------------------------------------------------

def get_ai_response(state: Dict[str, Any], additional_prompt: Optional[str] = None) -> str:
    handle_history_summarization(state)
    llm = get_llm()
    system_text = _build_system_instruction(state, CHATBOT_PERSONA)

    messages = [SystemMessage(content=system_text)]
    messages.extend(_conversation_history_to_messages(state))
    if additional_prompt:
        messages.append(HumanMessage(content=additional_prompt))

    _write_event({"type": "ai_generic_request", "msgs": len(messages)})
    try:
        resp = llm.invoke(messages).content.strip()
        add_message(state, "assistant", resp, context="ai_generic_response", persist_jsonl=True)
        _store_last_debug(
            state, call="get_ai_response", system=system_text, user=(additional_prompt or ""), messages=len(messages), response=resp
        )
        _write_event({"type": "ai_generic_response", "chars": len(resp)})
        return resp
    except Exception as e:
        LOG.error(f"get_ai_response failed: {e}")
        _write_event({"type": "ai_generic_error", "error": str(e)})
        _store_last_debug(state, call="get_ai_response", system=system_text, user=(additional_prompt or ""), messages=len(messages), response=str(e))
        return "خطایی رخ داد. لطفاً دوباره تلاش کنید."


def process_question_turn(
    state: Dict[str, Any],
    *,
    question_text: str,
    options: List[Any],
    user_input: str,
    qnum: int,
    total: int,
    next_question_text: Optional[str],
    next_options: Optional[List[Any]],
) -> Dict[str, Any]:
    handle_history_summarization(state)
    llm = get_llm()

    current_opts = normalize_option_texts(options)
    next_opts = normalize_option_texts(next_options) if next_options else []

    system_text = _build_system_instruction(state, COMBINED_SYSTEM_INSTRUCTION)
    payload = {"user_input": user_input}
    if next_question_text:
        payload[f"next_question_{qnum+1}"] = {"text": next_question_text, "options": next_opts}

    messages = [SystemMessage(content=system_text), HumanMessage(content=json.dumps(payload, ensure_ascii=False))]
    _write_event({"type": "process_question_turn_request", "q": qnum})

    raw_resp = ""
    try:
        raw_resp = llm.invoke(messages).content.strip()
        data = extract_json(raw_resp) or {}
        _write_event({"type": "process_question_turn_response", "q": qnum, "raw_len": len(raw_resp)})
    except Exception as e:
        LOG.error(f"process_question_turn LLM error: {e}")
        data = {}
        raw_resp = str(e)
        _write_event({"type": "process_question_turn_error", "q": qnum, "error": str(e)})

    _store_last_debug(state, call=f"process_question_turn[q{qnum}]", system=system_text, user=json.dumps(payload, ensure_ascii=False), messages=len(messages), response=raw_resp)

    valid = bool(data.get("valid", False))
    selected_option = data.get("selected_option")
    retry_message = data.get("retry_message")
    next_question = data.get("next_question")

    if not valid:
        ui = (user_input or "").strip()
        trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
        ui_norm = ui.translate(trans)
        digits = "".join(ch for ch in ui_norm if ch.isdigit())
        if digits.isdigit():
            idx = int(digits) - 1
            if 0 <= idx < len(current_opts):
                valid = True
                selected_option = current_opts[idx]
                retry_message = None
        else:
            low = ui_norm.strip().lower()
            for opt in current_opts:
                if low == str(opt).strip().lower():
                    valid = True
                    selected_option = str(opt)
                    retry_message = None
                    break

    if valid and not next_question and next_question_text:
        next_question = build_default_question_text(
            state.get("user_name", "کاربر"), next_question_text, next_opts, qnum + 1, total, {"selected_option": selected_option}
        )

    return {"valid": valid, "selected_option": selected_option, "retry_message": retry_message, "next_question": next_question}


def summarize_results(state: Dict[str, Any], results: Dict[str, Any]) -> str:
    llm = get_llm()
    answers_list = results.get("answers", [])
    formatted = [
        {"question": a.get("question", "N/A"), "selected_option": a.get("selected_option", "N/A"), "user_response": a.get("original_response", "N/A")}
        for a in answers_list
    ]
    formatted_answers = json.dumps(formatted, indent=2, ensure_ascii=False)
    complete_test_data = json.dumps(results, indent=2, ensure_ascii=False)

    # Prefer explicit user-provided info (first two questions) as the top of the prompt
    user_input_info = state.get("user_info", "")  # expected to contain name/age and personal info filled from first two questions
    conv_summary = state.get("history_summary") or state.get("summary", "")
    test_name = results.get("test_name") or state.get("test_data", {}).get("test_name", "") or "نامشخص"
    report_md = state.get("test_data", {}).get("result_format", {}).get("report_md", "") or "{}"

    # Build inline prompt (Persian) — include user_input_info at top as requested
    prompt_lines = [
        "با استفاده از اطلاعات زیر، یک تحلیل نهایی روانشناختی و شخصی‌سازی‌شده تولید کن:",
        "", 
        "اطلاعات ورودی کاربر (پاسخ‌های اولیه):",
        user_input_info,
        "",
        "خلاصهٔ گفتگو:",
        conv_summary,
        "",
        f"نام تست: {test_name}",
        "",
        "پاسخ‌ها (ساختار شده):",
        formatted_answers,
        "",
        "داده‌های کامل تست (JSON):",
        complete_test_data,
        "",
        "قالب خروجی مورد انتظار (report_md):",
        report_md,
        "",
        # Guidance for style (concise, Persian, use headings and emphasis as appropriate)
        ("لطفاً یک گزارش نهایی به زبان فارسی تولید کن؛ گزارش باید حرفه‌ای، همدلانه و کاربردی باشد، "
         "شامل بخش‌های قابل تشخیص (مثلاً مقدمه، تحلیل، نقاط قوت، نقاط قابل بهبود و توصیه‌های عملی). "
         "خروجی نهایی را به صورت یک سند Markdown خوانا برگردان. از توضیحات متادیتا یا بلوک‌های کدی خودداری کن.")
    ]
    prompt_final = "\n".join(prompt_lines)

    system_text = RESULT_CHATBOT_PERSONA
    raw_resp = ""
    try:
        raw_resp = llm.invoke([SystemMessage(content=system_text), HumanMessage(content=prompt_final)]).content.strip()
        _write_event({"type": "final_summary", "answers_count": len(answers_list), "chars": len(raw_resp)})
        return raw_resp
    except Exception as e:
        LOG.error(f"summarize_results failed: {e}")
        _write_event({"type": "final_summary_error", "error": str(e)})
        raw_resp = str(e)
        return "خطا در تولید خلاصه. لطفاً بعداً امتحان کنید."
    finally:
        _store_last_debug(state, call="summarize_results", system=system_text, user=prompt_final, messages=2, response=raw_resp)


def generate_image_prompt(summary: str) -> str:
    llm = get_llm()
    system_text = IMAGE_PROMPT_SYSTEM
    user_text = IMAGE_PROMPT_GENERATION_TEMPLATE.format(summary_text=summary)
    raw_resp = ""
    try:
        raw_resp = llm.invoke([SystemMessage(content=system_text), HumanMessage(content=user_text)]).content.strip()
        return raw_resp
    except Exception as e:
        LOG.error(f"generate_image_prompt failed: {e}")
        raw_resp = f"3D abstract blue-purple scene symbolizing personality insights: {summary[:60]} ..."
        return raw_resp
    finally:
        # Store last debug so UI can show the exact prompt & response
        dummy_state = {} if summary is None else {"_debug": {}}
        _store_last_debug(dummy_state, call="generate_image_prompt", system=system_text, user=user_text, messages=2, response=raw_resp)


def analyze_final_result(state: Dict[str, Any], final_text: str) -> str:
    """
    Produce a concise personalized analysis/caption suitable for display in UI.
    """
    llm = get_llm()
    system_text = RESULT_ANALYZE_CHATBOT_PERSONA + "\nتحلیل را به صورت ساختار‌یافته و خلاصه ارائه کن."
    
    # Prepare focused prompt for analysis
    user_name = state.get("user_name", "")
    user_age = state.get("user_age", "")
    test_name = state.get("test_data", {}).get("test_name", "")
    user_info = state.get("user_info", "") or ""
    prompt = (
        f"[اطلاعات کاربر]\n"
        f"نام: {user_name}\n"
        f"سن: {user_age}\n"
        f"تست: {test_name}\n\n"
        f"[پروفایل]\n{user_info}\n\n"
        f"[نتایج تحلیل]\n{final_text}"
    )

    raw_resp = ""
    try:
        raw_resp = llm.invoke([
            SystemMessage(content=system_text),
            HumanMessage(content=prompt)
        ]).content.strip()
        
        _write_event({"type": "analyze_final_result", "chars": len(raw_resp)})
        
        # Ensure we have proper sections in output
        if not any(keyword in raw_resp for keyword in ["نقاط قوت", "توصیه", "تحلیل"]):
            raw_resp = f"""# تحلیل شخصیت
{raw_resp}

# نقاط قوت
• قابل استخراج از متن بالا

# توصیه‌ها
• بر اساس تحلیل‌های فوق
"""
        
        # Optimize for Telegram display
        return format_analysis_for_telegram(raw_resp)
        
    except Exception as e:
        LOG.error(f"analyze_final_result failed: {e}")
        _write_event({"type": "analyze_final_result_error", "error": str(e)})
        raw_resp = "⚠️ متأسفانه در تحلیل نتایج خطایی رخ داد. لطفاً به پشتیبانی اطلاع دهید."
        return raw_resp
    finally:
        try:
            _store_last_debug(state, call="analyze_final_result", system=system_text, user=prompt, messages=2, response=raw_resp)
        except Exception:
            pass
