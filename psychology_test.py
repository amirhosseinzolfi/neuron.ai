# psychology_test.py
# =====================================================================
# Interactive Psychological Assessment (LangGraph)
# - CLI & Telegram adapters
# - Back-compat shim for pt.all_tests["tests"] and pt.generate_images_for_prompt(...)
# - Rich-table LLM debug view (system prompt, raw user payload, raw AI response)
# =====================================================================

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, TypedDict

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from langgraph.graph import StateGraph

from database.prompts import FIRST_QUESTION_PROMPT
from ai_utils import (
    OPENAI_MODEL,
    OPENAI_BASE_URL,
    add_message,
    build_default_question_text,
    generate_image_prompt,
    get_ai_response,
    process_question_turn,
    summarize_results,
    analyze_final_result,  # <-- added
)

# --- image gen legacy shim (so telegram_handlers can call pt.generate_images_for_prompt) ---
try:
    from image_utils import generate_images_for_prompt as _generate_images_for_prompt
    def generate_images_for_prompt(prompt: str, user_name: str, out_dir: str, **kwargs):
        """Legacy shim that forwards to image_utils.generate_images_for_prompt(...)"""
        return _generate_images_for_prompt(prompt, user_name, out_dir, **kwargs)
except Exception as _e:
    def generate_images_for_prompt(*args, **kwargs):
        raise RuntimeError("image_utils.generate_images_for_prompt is unavailable") from _e

# -----------------------------------------------------------------------------
# Paths & logging
# -----------------------------------------------------------------------------

BASE_DIR = os.path.dirname(__file__)
TEST_JSON_PATH = os.path.join(BASE_DIR, "database", "test.json")
RESULTS_PATH = os.path.join(BASE_DIR, "database", "test-result.json")
CONV_PATH = os.path.join(BASE_DIR, "database", "conversation-history.json")

STREAMLIT_PORT = 8501
DEFAULT_USER_ID = "cli_user"

logging.basicConfig(level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)])
log = logging.getLogger("psychology_test")
console = Console()


# -----------------------------------------------------------------------------
# LangGraph state
# -----------------------------------------------------------------------------

class TestState(TypedDict, total=False):
    current_question: int
    finished: bool
    user_name: str
    user_age: int
    user_info: str
    user_id: str
    conversation_history: List[Dict[str, Any]]
    last_answer: Dict[str, Any]
    history_summary: str
    summary: str
    attempt_count: int
    message_count: int
    next_question_text: str
    test_data: Dict[str, Any]
    test_results: Dict[str, Any]
    chat_id: Optional[int]
    _debug: Dict[str, Any]  # holds last LLM call snapshot for rich table


# -----------------------------------------------------------------------------
# File I/O helpers
# -----------------------------------------------------------------------------

def _load_all_tests() -> Dict[str, Any]:
    if not os.path.exists(TEST_JSON_PATH):
        raise FileNotFoundError(f"Missing test bank file: {TEST_JSON_PATH}")
    with open(TEST_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    tests = data.get("tests", [])
    if not tests:
        raise ValueError("No tests found in test.json (expected key 'tests').")
    return data


def load_results_safe() -> Dict[str, Any]:
    try:
        if not os.path.exists(RESULTS_PATH):
            return {"users": {}}
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "users" in data:
            return data
        out = {"users": {}}
        stamp = str(int(time.time()))
        if data.get("answers"):
            tname = data.get("test_name", "Unknown")
            out["users"]["converted_legacy_data"] = {f"{tname}_{stamp}": data}
        return out
    except Exception as e:
        log.error(f"Error loading results: {e}")
        return {"users": {}}


def save_results_safe(results: Dict[str, Any]) -> bool:
    try:
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        log.error(f"Error saving results: {e}")
        return False


def persist_conversation_safe(state: TestState) -> None:
    try:
        with open(CONV_PATH, "w", encoding="utf-8") as f:
            json.dump(state.get("conversation_history", []), f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error(f"Error writing conversation history: {e}")


# -----------------------------------------------------------------------------
# Optional Streamlit UI
# -----------------------------------------------------------------------------

def _is_port_open(port: int) -> bool:
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def start_streamlit_ui_if_needed() -> None:
    try:
        if _is_port_open(STREAMLIT_PORT):
            return
        exe = shutil.which("streamlit")
        if not exe:
            return
        ui_path = os.path.join(BASE_DIR, "streamlit_ui.py")
        subprocess.Popen(
            [exe, "run", ui_path, "--server.port", str(STREAMLIT_PORT), "--server.headless", "true"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=BASE_DIR,
            start_new_session=True,
        )
    except Exception:
        pass


# -----------------------------------------------------------------------------
# CLI helpers (pure UI)
# -----------------------------------------------------------------------------

def _print_banner() -> None:
    console.clear()
    console.rule("[bold bright_cyan]✨ Interactive Psychological Assessment ✨[/bold bright_cyan]")


def _select_test_interactive(all_tests: Dict[str, Any]) -> Dict[str, Any]:
    tests: List[Dict[str, Any]] = all_tests["tests"]
    console.print("[green]Available Tests:[/green]")
    for i, t in enumerate(tests, 1):
        console.print(f"{i}. {t['test_name']} ({t.get('estimated_time', '?')})")
    while True:
        choice = Prompt.ask("[bold magenta]Enter the number of the test you want to take[/bold magenta]").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(tests):
            return tests[int(choice) - 1]
        console.print("[red]Invalid selection. Please enter a valid test number.[/red]")


def _gather_user_profile() -> Dict[str, Any]:
    name_age = Prompt.ask("[bold magenta]Your name & age?[/bold magenta]")
    more_info = Prompt.ask("[bold magenta]Anything about you that helps personalize the result?[/bold magenta]")
    tokens = name_age.split()
    user_name = tokens[0] if tokens else "User"
    digits = "".join(ch for ch in name_age if ch.isdigit())
    user_age = int(digits) if digits.isdigit() else 0
    return {"user_name": user_name, "user_age": user_age, "user_info": f"Name & age: {name_age}\nPersonal information: {more_info}"}


def _normalize_option_text(opt: Any) -> str:
    return str(opt.get("text", "")) if isinstance(opt, dict) else str(opt)


# -----------------------------------------------------------------------------
# Rich table for LLM debug traces
# -----------------------------------------------------------------------------

def _render_ai_debug(state: TestState, title: str) -> None:
    dbg_outer = state.setdefault("_debug", {}) or {}
    dbg = dbg_outer.get("last_call") or {}
    if not dbg and not dbg_outer:
        return

    # --- dedupe: skip rendering if this snapshot was already printed ---
    try:
        ts = dbg.get("ts")
        last_rendered = dbg_outer.get("_last_rendered_ts")
        if ts and last_rendered and ts == last_rendered:
            return  # already rendered this exact snapshot
    except Exception:
        pass
    # -------------------------------------------------------------------

    tbl = Table(title=f"🔍 LLM Debug · {title}", show_lines=True, expand=True, title_style="bold cyan")
    tbl.add_column("Field", style="bold magenta", no_wrap=True)
    tbl.add_column("Content", style="white", overflow="fold")

    # Basic metadata
    tbl.add_row("Call", dbg.get("call", ""))
    tbl.add_row("Model", dbg.get("model", OPENAI_MODEL))
    tbl.add_row("Base URL", dbg.get("base_url", OPENAI_BASE_URL))
    tbl.add_row("Messages (count)", str(dbg.get("messages", "")))

    # System instruction (full)
    tbl.add_row("System (AI Instruction)", dbg.get("system", "") or "")

    # Full raw user prompt sent to LLM
    tbl.add_row("User Prompt (Raw)", dbg.get("user", "") or "")

    # Full raw AI response
    tbl.add_row("AI Response (Raw)", dbg.get("response", "") or "")

    # Full detailed conversation lines (role: content)
    # prefer messages_full if present in debug, otherwise fall back to state conversation_history
    messages_full = dbg.get("messages_full")
    if not messages_full:
        conv = state.get("conversation_history", []) or []
        conv_lines = []
        for m in conv:
            role = m.get("role", "")
            content = m.get("content", "") or ""
            conv_lines.append(f"{role}: {content}")
        messages_full = "\n".join(conv_lines)
    tbl.add_row("Messages (detailed)", messages_full or "")

    # history summary (from debug outer or state)
    history_summary = dbg_outer.get("history_summary") or state.get("history_summary") or ""
    tbl.add_row("History Summary (generated)", history_summary)

    # trimming info (debug)
    trim_info = dbg_outer.get("history_trim_info") or {}
    try:
        import json as _json
        trim_str = _json.dumps(trim_info, ensure_ascii=False)
    except Exception:
        trim_str = str(trim_info)
    tbl.add_row("History Trim Info", trim_str)

    # include full conversation history for full context (role: content per line) - keep for backward compat
    conv = state.get("conversation_history", []) or []
    if conv:
        conv_lines = []
        for m in conv:
            role = m.get("role", "")
            content = m.get("content", "")
            conv_lines.append(f"{role}: {content}")
        conv_text = "\n".join(conv_lines)
    else:
        conv_text = ""
    tbl.add_row("Full Conversation History", conv_text)

    console.print(tbl)

    # record that we rendered this snapshot so duplicates are skipped next time
    try:
        if dbg.get("ts"):
            state.setdefault("_debug", {})["_last_rendered_ts"] = dbg.get("ts")
    except Exception:
        pass

# -----------------------------------------------------------------------------
# LangGraph nodes (AI orchestration via ai_utils)
# -----------------------------------------------------------------------------

def initialize(state: TestState) -> TestState:
    _print_banner()
    all_tests = _load_all_tests()
    active_test = _select_test_interactive(all_tests)

    console.print(
        Panel(
            f"📝 [bold]{active_test['test_name']}[/bold]\n"
            f"- Questions: {len(active_test['questions'])}\n"
            f"- Est. time: {active_test.get('estimated_time', '?')}",
            title="Test Details",
            border_style="green",
        )
    )

    profile = _gather_user_profile()
    new_state: TestState = {
        "current_question": 0,
        "finished": False,
        "user_name": profile["user_name"],
        "user_age": profile["user_age"],
        "user_info": profile["user_info"],
        "user_id": DEFAULT_USER_ID,
        "conversation_history": [],
        "last_answer": {},
        "history_summary": "",
        "summary": "",
        "attempt_count": 0,
        "message_count": 0,
        "next_question_text": "",
        "test_data": active_test,
        "test_results": {"test_name": active_test.get("test_name", ""), "answers": []},
        "chat_id": None,
        "_debug": {},
    }

    add_message(new_state, "user", new_state["user_info"], context="user_profile", persist_jsonl=True)
    log.info(f"Starting test: {active_test.get('test_name')} | user={new_state['user_name']}")
    return new_state


def ask_question(state: TestState) -> TestState:
    test_data = state["test_data"]
    idx = state["current_question"]
    total = len(test_data["questions"])

    if idx >= total:
        state["finished"] = True
        return state

    qd = test_data["questions"][idx]
    is_first = idx == 0
    ai_generated_first = False

    # Prepare question text
    if is_first and not state.get("next_question_text"):
        options_lines = "\n".join([f"{i+1}. {_normalize_option_text(o)}" for i, o in enumerate(qd["options"])])
        first_prompt = (
            FIRST_QUESTION_PROMPT.format(question_number=1, total_questions=total, question=qd["question"])
            + "\n- Options (internal):\n"
            + options_lines
            + "\n- Do NOT show options explicitly. Ask conversationally in Persian."
        )
        q_text = get_ai_response(state, additional_prompt=first_prompt)
        # show full LLM trace
        _render_ai_debug(state, "First Question Generation")
        # retag last assistant message as Q1
        for i in range(len(state["conversation_history"]) - 1, -1, -1):
            if state["conversation_history"][i].get("role") == "assistant":
                state["conversation_history"][i]["context"] = f"question_{idx+1}"
                break
        state["next_question_text"] = q_text
        ai_generated_first = True
    else:
        q_text = state.get("next_question_text") or build_default_question_text(
            state["user_name"], qd["question"], qd["options"], idx + 1, total, state.get("last_answer")
        )

    # Render question
    console.rule(f"[bold cyan]Question {idx + 1}/{total}")
    console.print(Panel(f"[yellow]{q_text}[/yellow]", border_style="cyan", title=f"For {state['user_name']}", title_align="left"))

    if not ai_generated_first:
        add_message(state, "assistant", q_text, context=f"question_{idx+1}")
        state["message_count"] = len(state["conversation_history"])

    # Attempt loop
    attempt = 0
    while True:
        attempt += 1
        user_input = Prompt.ask("[bold magenta]Your response[/bold magenta]").strip()
        add_message(state, "user", user_input, context=f"answer_attempt_{attempt}_q{idx+1}")

        if idx + 1 < total:
            next_q = test_data["questions"][idx + 1]
            next_raw_text, next_raw_options = next_q["question"], next_q["options"]
        else:
            next_raw_text, next_raw_options = None, None

        turn = process_question_turn(
            state=state,
            question_text=qd["question"],
            options=qd["options"],
            user_input=user_input,
            qnum=idx + 1,
            total=total,
            next_question_text=next_raw_text,
            next_options=next_raw_options,
        )

        # show full LLM trace for this validation/next-step call
        _render_ai_debug(state, f"Answer Q{idx+1} (attempt {attempt})")

        if turn.get("valid"):
            selected_option = turn.get("selected_option")
            state["test_results"]["answers"].append(
                {
                    "question_id": qd.get("id", f"q_{idx+1}"),
                    "question": qd["question"],
                    "selected_option": selected_option,
                    "original_response": user_input,
                    "question_number": idx + 1,
                    "timestamp": time.time(),
                }
            )
            state["last_answer"] = {"response": user_input, "selected_option": selected_option, "question": qd["question"]}

            idx += 1
            state["current_question"] = idx

            if idx >= total:
                state["finished"] = True
                state["next_question_text"] = ""
            else:
                next_text = turn.get("next_question") or build_default_question_text(
                    state["user_name"],
                    test_data["questions"][idx]["question"],
                    test_data["questions"][idx]["options"],
                    idx + 1,
                    total,
                    state["last_answer"],
                )
                state["next_question_text"] = next_text
                add_message(state, "assistant", next_text, context=f"question_{idx+1}")

            state["message_count"] = len(state["conversation_history"])
            time.sleep(0.2)
            break

        retry_msg = turn.get("retry_message") or "لطفاً یکی از گزینه‌های معتبر را انتخاب کنید."
        console.print(Panel(f"[bold orange3]{retry_msg}[/bold orange3]", border_style="red"))
        add_message(state, "assistant", retry_msg, context=f"retry_q{idx+1}_attempt{attempt}")
        state["message_count"] = len(state["conversation_history"])

    return state


def decide_next(state: TestState) -> Dict[str, str]:
    return {"next_node": "summarize" if state.get("finished") else "ask_question"}


def summarize(state: TestState) -> TestState:
    console.rule("[bold blue]📝 Analyzing Your Personality Profile...[/bold blue]")
    for msg in ("Analyzing response patterns...", "Identifying psychological traits...", "Compiling your personality profile..."):
        console.print(f"[bright_magenta]{msg}[/bright_magenta]")
        time.sleep(0.5)

    # Ensure conversation summary is up to date before final analysis
    from ai_utils import handle_history_summarization
    handle_history_summarization(state)
    
    # Full textual analysis used in PDF and stored as test_results["analysis"]
    analysis = summarize_results(state, state["test_results"])
    _render_ai_debug(state, "Final Summary")
    state["test_results"]["analysis"] = analysis
    state["test_results"]["user_name"] = state["user_name"]
    state["test_results"]["analysis_timestamp"] = time.time()

    # NEW: produce a concise personalized analysis/caption for image caption
    try:
        caption = analyze_final_result(state, analysis)
        state["test_results"]["analysis_caption"] = caption
    except Exception as e:
        log.error(f"Failed to produce analysis caption: {e}")
        state["test_results"]["analysis_caption"] = ""

    all_results = load_results_safe()
    bucket = all_results.setdefault("users", {}).setdefault(state["user_id"], {})
    key = f"{state['test_data'].get('test_name', 'Unknown')}_{int(time.time())}"
    bucket[key] = state["test_results"]
    save_results_safe(all_results)

    console.print(Panel(analysis, border_style="bright_green", title=f"Personality Insights for {state['user_name']}", title_align="center"))
    console.print(Panel(f"🎉 Test «{state['test_data']['test_name']}» finished!", border_style="bright_cyan"))

    persist_conversation_safe(state)

    # Optional: image prompt + legacy shim call (if you want to actually generate images here)
    try:
        img_prompt = generate_image_prompt(analysis)
        _render_ai_debug(state, "Image Prompt")
        # Example actual generation (kept optional):
        # images = generate_images_for_prompt(img_prompt, state["user_name"], "/tmp", model="midjourney", num_images=1, width=512, height=512)
        # log.info(f"Generated images: {images}")
    except Exception as e:
        log.error(f"Image prompt error: {e}")

    return state


# -----------------------------------------------------------------------------
# Telegram helpers
# -----------------------------------------------------------------------------

def tele_initialize(user_name: str, age: int, user_info: str, test_type: str = "1", chat_id: Optional[int] = None) -> TestState:
    all_tests = _load_all_tests()
    tests = all_tests["tests"]
    if test_type.isdigit():
        idx = max(0, min(int(test_type) - 1, len(tests) - 1))
        active = tests[idx]
    else:
        active = next((t for t in tests if t["test_name"].upper() == test_type.upper()), tests[0])

    state: TestState = {
        "current_question": 0,
        "finished": False,
        "user_name": user_name,
        "user_age": age,
        "user_info": user_info,
        "user_id": str(chat_id or DEFAULT_USER_ID),
        "conversation_history": [],
        "last_answer": {},
        "history_summary": "",
        "summary": "",
        "attempt_count": 0,
        "message_count": 0,
        "next_question_text": "",
        "test_data": active,
        "test_results": {"test_name": active.get("test_name", ""), "answers": []},
        "chat_id": chat_id,
        "_debug": {},
    }
    add_message(state, "user", user_info, context="user_profile", persist_jsonl=True)
    state["message_count"] = len(state["conversation_history"])
    # Render debug info to terminal for Telegram init (shows system/user/AI texts, summary, trim info)
    try:
        _render_ai_debug(state, "Tele Initialize")
    except Exception:
        pass
    return state


def tele_get_question(state: TestState) -> Optional[str]:
    if state.get("finished"):
        return None
    test_data = state["test_data"]
    idx = state["current_question"]
    total = len(test_data["questions"])

    if idx == 0 and not state.get("next_question_text"):
        options_lines = "\n".join([f"{i+1}. {_normalize_option_text(o)}" for i, o in enumerate(test_data["questions"][idx]["options"])])
        first_prompt = FIRST_QUESTION_PROMPT.format(question_number=1, total_questions=total, question=test_data["questions"][idx]["question"])
        text = get_ai_response(state, additional_prompt=first_prompt + "\n- Options (internal):\n" + options_lines + "\nDo NOT show options explicitly.")
        # Tag last assistant message
        for i in range(len(state["conversation_history"]) - 1, -1, -1):
            if state["conversation_history"][i].get("role") == "assistant":
                state["conversation_history"][i]["context"] = f"question_{idx+1}"
                break
        state["next_question_text"] = text
    else:
        text = state.get("next_question_text") or build_default_question_text(
            state["user_name"], test_data["questions"][idx]["question"], test_data["questions"][idx]["options"], idx + 1, total, state.get("last_answer")
        )

    if not any(m for m in state["conversation_history"] if m.get("context") == f"question_{idx+1}" and m.get("role") == "assistant"):
        add_message(state, "assistant", text, context=f"question_{idx+1}")
        # show LLM debug snapshot for this generated question (useful when running Telegram tests)
        try:
            _render_ai_debug(state, f"Tele Get Question Q{idx+1}")
        except Exception:
            pass
    return f"✅سوال {idx+1}/{total}\n{text}"


def tele_process_answer(state: TestState, user_input: str) -> Dict[str, Optional[str]]:
    idx = state.get("current_question", 0)
    test_data = state["test_data"]
    questions = test_data.get("questions", [])
    if state.get("finished") or idx >= len(questions):
        return {"ack": None, "next": None}

    qd = questions[idx]
    add_message(state, "user", user_input, context=f"answer_q{idx+1}")

    if idx + 1 < len(questions):
        next_raw_text, next_raw_options = questions[idx + 1]["question"], questions[idx + 1]["options"]
    else:
        next_raw_text, next_raw_options = None, None

    turn = process_question_turn(
        state=state,
        question_text=qd["question"],
        options=qd["options"],
        user_input=user_input,
        qnum=idx + 1,
        total=len(questions),
        next_question_text=next_raw_text,
        next_options=next_raw_options,
    )

    # Render debug snapshot to terminal so Telegram runs log LLM system/user/response + trimming info
    try:
        _render_ai_debug(state, f"Tele Process Answer Q{idx+1}")
    except Exception:
        pass

    # You could forward the debug table to log here if running headless; kept UI-only in CLI.

    if turn.get("valid"):
        selected = turn.get("selected_option")
        state["test_results"]["answers"].append(
            {
                "question_id": qd.get("id", f"q_{idx+1}"),
                "question": qd["question"],
                "selected_option": selected,
                "original_response": user_input,
                "question_number": idx + 1,
                "timestamp": time.time(),
            }
        )
        state["last_answer"] = {"response": user_input, "selected_option": selected, "question": qd["question"]}
        state["current_question"] += 1

        if state["current_question"] >= len(questions):
            state["finished"] = True
            state["next_question_text"] = ""
            return {"ack": None, "next": None}

        nxt = turn.get("next_question") or build_default_question_text(
            state["user_name"],
            questions[state["current_question"]]["question"],
            questions[state["current_question"]]["options"],
            state["current_question"] + 1,
            len(questions),
            state["last_answer"],
        )
        state["next_question_text"] = nxt
        add_message(state, "assistant", nxt, context=f"question_{state['current_question']+1}")
        # Also print debug for the next question generation
        try:
            _render_ai_debug(state, f"Tele Next Question Q{state['current_question']+1}")
        except Exception:
            pass
        return {"ack": None, "next": f"✅سوال {state['current_question'] + 1}/{len(questions)}\n{nxt}"}

    retry_msg = turn.get("retry_message") or "لطفاً یکی از گزینه‌های معتبر را انتخاب کنید."
    add_message(state, "assistant", retry_msg, context=f"retry_q{idx+1}")
    # show debug for retry message as well
    try:
        _render_ai_debug(state, f"Tele Retry Q{idx+1}")
    except Exception:
        pass
    return {"ack": retry_msg, "next": None}


def tele_summarize(state: TestState) -> str:
    payload = {
        "test_name": state["test_data"].get("test_name", ""),
        "answers": state.get("test_results", {}).get("answers", []),
        "user_name": state.get("user_name", "Unknown User"),
        "user_age": state.get("user_age", 0),
        "user_info": state.get("user_info", ""),
    }
    summary = summarize_results(state, payload)
    # Print final summary debug to terminal for Telegram sessions
    try:
        _render_ai_debug(state, "Tele Final Summary")
    except Exception:
        pass
    return summary


# -----------------------------------------------------------------------------
# Legacy shim for older Telegram handlers (pt.all_tests["tests"])
# -----------------------------------------------------------------------------

try:
    all_tests: Dict[str, Any] = _load_all_tests()
except Exception as e:
    log.error(f"Failed to load tests for legacy export: {e}")
    all_tests = {"tests": []}


def get_all_tests() -> Dict[str, Any]:
    return _load_all_tests()


def get_test_list() -> List[Dict[str, Any]]:
    return _load_all_tests().get("tests", [])


# -----------------------------------------------------------------------------
# Graph wiring
# -----------------------------------------------------------------------------

graph = StateGraph(TestState)
graph.add_node("initialize", initialize)
graph.add_node("ask_question", ask_question)
graph.add_node("decide_next", decide_next)
graph.add_node("summarize", summarize)

graph.set_entry_point("initialize")
graph.add_edge("initialize", "ask_question")
graph.add_edge("ask_question", "decide_next")
graph.add_conditional_edges("decide_next", lambda s: s["next_node"], {"ask_question": "ask_question", "summarize": "summarize"})
compiled_graph = graph.compile()


# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    start_streamlit_ui_if_needed()
    compiled_graph.invoke({})
