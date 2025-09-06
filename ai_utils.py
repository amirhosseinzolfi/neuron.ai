import time, logging, json, os
from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.logging import RichHandler
from rich.table import Table
from rich.text import Text
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from prompts import (
    CHATBOT_PERSONA,
    COMBINED_SYSTEM_INSTRUCTION,  # Add this import
    QUESTION_WITH_ACKNOWLEDGMENT_PROMPT,
    FIRST_QUESTION_PROMPT,
    RESPONSE_ANALYSIS_PROMPT,
    RETRY_PROMPT,  # Updated import
    ANALYSIS_SUMMARY_PROMPT,
    RESULT_CHATBOT_PERSONA,
    IMAGE_PROMPT_SYSTEM,
    IMAGE_PROMPT_GENERATION_TEMPLATE,
)
import subprocess, uuid
from logging.handlers import RotatingFileHandler

# --- Initialize Logging & Console ---
logging.basicConfig(level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)])
log = logging.getLogger("ai_utils")
console = Console()

# NEW: ensure logs directory exists and add a rotating JSONL file handler
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
JSONL_PATH = os.path.join(LOG_DIR, "blue_ai_logs.jsonl")

class JSONLineFormatter(logging.Formatter):
    def format(self, record):
        base = {
            "timestamp": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        # include any extra json-able attributes attached to record
        extra = {k: v for k, v in record.__dict__.items() if k not in logging.LogRecord(None, None, None, None, None, None, None).__dict__}
        base.update(extra)
        try:
            return json.dumps(base, ensure_ascii=False)
        except Exception:
            return json.dumps({"timestamp": time.time(), "level": record.levelname, "message": record.getMessage()})

json_handler = RotatingFileHandler(JSONL_PATH, maxBytes=5_000_000, backupCount=3, encoding="utf-8")
json_handler.setFormatter(JSONLineFormatter())
json_handler.setLevel(logging.INFO)
log.addHandler(json_handler)

def _write_structured_event(event: Dict[str, Any]):
    """Append an arbitrary JSON event to the JSONL log file (best-effort)."""
    try:
        event.setdefault("ts", time.time())
        with open(JSONL_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        log.debug(f"Failed to write structured event: {e}")

# --- Initialize single main LLM (used for Q&A, validation, summary, and image prompt) ---
llm = ChatOpenAI(base_url="http://localhost:15207/v1", model_name="gpt-4o", temperature=0.6, api_key="324")

# --- History management settings (unchanged) ---
HISTORY_TRIM_THRESHOLD = 15  # Increased threshold since we're summarizing less frequently
HISTORY_RETENTION = 5  # Retain more recent messages
SUMMARY_INTERVAL = 5  # Summarize every 5 messages
SUMMARY_CONVERSATION_PROMPT = """Summarize the following conversation into concise bullet points.
Pay special attention to and retain any explicitly stated personal details by the user, such as their name, age, or profession (if mentioned), or other significant contextual information they provide, as these are important for ongoing personalization and context.
Focus on the main topics discussed and key information exchanged.

Conversation:
{conversation}"""

def normalize_option_texts(options: List[Any]) -> List[str]:
    return [(o.get("text") if isinstance(o, dict) and "text" in o else str(o)).strip() for o in options]

def build_default_question_text(user_name: str, question: str, options: List[Any], qnum: int, total: int, last_answer: Optional[Dict[str, Any]] = None) -> str:
    opts = normalize_option_texts(options)
    head = f"{user_name} عزیز، سوال {qnum}/{total}:\n{question}".strip()
    if last_answer:
        head = f"{user_name} عزیز، با توجه به پاسخ قبلی شما («{last_answer.get('selected_option','')}»)، سوال {qnum}/{total}:\n{question}"
    options_lines = "\n".join([f"{i+1}. {t}" for i, t in enumerate(opts)])
    return f"{head}\n\nگزینه‌ها:\n{options_lines}\n\nلطفاً شماره گزینه یا متن آن را بفرستید."

def extract_json(payload: str) -> Optional[Dict[str, Any]]:
    s = payload.strip()
    # Try raw JSON
    try:
        return json.loads(s)
    except Exception:
        pass
    # Try to extract from code fences
    if "```" in s:
        parts = s.split("```")
        for part in parts:
            try:
                return json.loads(part.strip())
            except Exception:
                continue
    # Try to locate first { ... }
    try:
        start = s.index("{")
        end = s.rfind("}")
        if start >= 0 and end >= 0 and end > start:
            return json.loads(s[start:end+1])
    except Exception:
        return None
    return None

def should_summarize_history(state):
    """Check if history should be summarized based on message count"""
    history_length = len(state["conversation_history"])
    
    # Only summarize if we have enough messages and it's at the interval
    if history_length >= SUMMARY_INTERVAL and history_length % SUMMARY_INTERVAL == 0:
        log.info(f"Triggering history summarization at {history_length} messages")
        return True
    return False

def handle_history_summarization(state):
    """Handle conversation history summarization every 5 messages"""
    if should_summarize_history(state):
        log.info(f"Summarizing conversation history ({len(state['conversation_history'])} messages)")
        
        # Get messages to summarize (exclude system messages for cleaner summary)
        messages_to_summarize = [
            msg for msg in state["conversation_history"] 
            if msg.get("role") != "system"
        ]
        
        if len(messages_to_summarize) >= SUMMARY_INTERVAL:
            conv = "\n".join(f"{m['role']}: {m['content']}" for m in messages_to_summarize)
            
            try:
                summary_response = llm.invoke([
                    SystemMessage(content="You are a helpful assistant that summarizes conversations."),
                    HumanMessage(content=SUMMARY_CONVERSATION_PROMPT.format(conversation=conv))
                ]).content.strip()
                
                # Store summary using LangGraph-style key
                if state.get("summary"):
                    state["summary"] += f"\n\nRecent conversation:\n{summary_response}"
                else:
                    state["summary"] = summary_response
                # Keep legacy key for compatibility
                state["history_summary"] = state["summary"]

                # Keep only the most recent messages after summarization
                state["conversation_history"] = state["conversation_history"][-HISTORY_RETENTION:]
                
                log.info(f"History summarized. Retained {len(state['conversation_history'])} recent messages")
                
            except Exception as e:
                log.error(f"Error during history summarization: {e}")
    
    # Fallback: if history gets too long without summarization, force trim
    elif len(state["conversation_history"]) > HISTORY_TRIM_THRESHOLD:
        log.warning(f"History length ({len(state['conversation_history'])}) exceeded threshold. Force trimming...")
        state["conversation_history"] = state["conversation_history"][-HISTORY_RETENTION:]

# NEW: standardized message helpers ------------------------------------------------
def _now_ts() -> float:
    return time.time()

def standard_message(role: str, content: str, context: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a standardized conversation message dict following LangGraph-friendly shape.

    Note:
      - 'role' is one of: 'user', 'assistant', 'system', 'internal'
      - 'content' stores the raw text
      - 'context' stores short question/context info (used to render "user: ...\ncontext: ...")
      - 'meta' can carry arbitrary structured data
    """
    return {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": content,
        "ts": _now_ts(),
        "context": context or "",
        "meta": meta or {}
    }

def add_message(state: Dict[str, Any], role: str, content: str, context: Optional[str] = None, meta: Optional[Dict[str, Any]] = None, persist_jsonl: bool = False) -> Dict[str, Any]:
    """
    Append a standardized message to state['conversation_history'] and keep message_count updated.
    - 'internal' role messages are not appended to conversation_history (they are internal payloads).
    - Prevent appending duplicate consecutive assistant messages.
    """
    try:
        role_norm = (role or "").lower()
        msg = standard_message(role_norm, content, context=context, meta=meta)

        # INTERNAL messages: do NOT append to the conversational history (they pollute LLM input).
        if role_norm == "internal":
            # Still write a structured event for auditing/debugging if requested
            if persist_jsonl:
                _write_structured_event({"type": "internal_payload", "message": msg})
            log.info(f"[history:no-save][internal] {content[:200]!r}")
            return msg

        # Prevent duplicate consecutive assistant messages
        last_msg = None
        if state.get("conversation_history"):
            # find last non-internal message if any
            for m in reversed(state["conversation_history"]):
                if m.get("role") != "internal":
                    last_msg = m
                    break

        if role_norm == "assistant" and last_msg and last_msg.get("role") == "assistant":
            if (last_msg.get("content", "").strip() == content.strip()):
                log.debug(f"Duplicate assistant message detected; skipping append. Content preview: {content[:200]!r}")
                return last_msg

        # Append and maintain counts/trim
        state.setdefault("conversation_history", []).append(msg)
        state["message_count"] = len(state["conversation_history"])

        if len(state["conversation_history"]) > HISTORY_TRIM_THRESHOLD:
            state["conversation_history"] = state["conversation_history"][-HISTORY_RETENTION:]

        # persist if requested
        if persist_jsonl:
            _write_structured_event({"type": "history_message", "message": msg})

        # Log exact saved message for clarity (role + preview)
        log.info(f"[history:append] role={role_norm} content={content[:200]!r} (len={len(content)})")

        return msg
    except Exception as e:
        log.debug(f"add_message failed: {e}")
        fallback = {"role": role, "content": content, "context": context or ""}
        state.setdefault("conversation_history", []).append(fallback)
        state["message_count"] = len(state["conversation_history"])
        return fallback

# NEW: helper to convert internal history to LLM messages in LangGraph friendly syntax
def _conversation_history_to_messages(state: Dict[str, Any]) -> List[Any]:
    """
    Convert state's conversation_history into a list of langchain message objects.
    - Skip 'internal' messages (they're not part of the LLM-visible chat).
    - Avoid sending duplicate consecutive assistant messages.
    """
    messages = []
    last_assistant_content = None
    for msg in state.get("conversation_history", []):
        r = msg.get("role", "")
        content = msg.get("content", "") or ""
        ctx = msg.get("context", "") or ""

        # Skip internal messages entirely
        if r == "internal":
            continue

        if r == "user":
            combined = f"user: {content}\ncontext: {ctx}".strip()
            messages.append(HumanMessage(content=combined))
            last_assistant_content = None  # reset assistant dedupe on user turn
        elif r == "assistant":
            # Avoid sending duplicate assistant messages multiple times
            if content.strip() == (last_assistant_content or "").strip():
                continue
            messages.append(AIMessage(content=content))
            last_assistant_content = content
        elif r == "system":
            combined = f"system: {content}\ncontext: {ctx}".strip()
            messages.append(HumanMessage(content=combined))
            last_assistant_content = None
        else:
            messages.append(HumanMessage(content=f"{r}: {content}"))
            last_assistant_content = None
    return messages

def _build_system_instruction(state: Dict[str, Any], base_system: str) -> str:
    """
    Compose the top-level system instruction combining base_system and a concise conversation summary.
    Keep summaries short and efficient (LangGraph style) and avoid duplicating the full history.
    """
    system_content = base_system
    # Insert user_info if present (compact)
    if state.get("user_info"):
        system_content += (
            "\n\n[UserProfile]\n" + state["user_info"] + "\n"
            "Use this to personalize the conversation."
        )
    # Attach only the compact summary (state['summary']) — kept updated by handle_history_summarization
    conv_summary = state.get("summary") or state.get("history_summary", "")
    if conv_summary:
        system_content += "\n\n[ConversationSummary]\n" + conv_summary
    return system_content

# --- Main AI response function (updated to use standardized history formatting) ---
def get_ai_response(state, additional_prompt=None):
    """Get AI responses using global state conversation history (LangGraph-style formatting)"""
    # Only handle summarization every SUMMARY_INTERVAL messages
    handle_history_summarization(state)

    # Build efficient system instruction once (do not inject multiple system messages from history)
    system_content_formatted = _build_system_instruction(state, CHATBOT_PERSONA)

    # Build messages: top-level system + converted conversation history (user/assistant/internal)
    messages = [SystemMessage(content=system_content_formatted)]
    messages.extend(_conversation_history_to_messages(state))

    user_prompt_for_log = "N/A"
    if additional_prompt:
        # Additional prompt is treated as a user/human instruction (keeps it visible for LLM)
        messages.append(HumanMessage(content=additional_prompt))
        user_prompt_for_log = additional_prompt

    log.info(f"Sending {len(messages)} messages to AI (system + history + current prompt).")

    try:
        resp = llm.invoke(messages).content.strip()

        # Always persist assistant messages to conversation history (LangGraph: assistant entries must be kept)
        add_message(state, "assistant", resp, context="ai_generic_response", persist_jsonl=True)

        # Structured turn event
        try:
            turn_event = {
                "type": "ai_turn",
                "id": str(uuid.uuid4()),
                "last_user": next((m["content"] for m in reversed(state.get("conversation_history", [])) if m.get("role") == "user"), None),
                "additional_prompt": (additional_prompt or "")[:2000],
                "response": resp[:8000],
                "conversation_summary": (state.get("summary") or state.get("history_summary",""))[:2000],
                "message_count": len(state.get("conversation_history", []))
            }
            _write_structured_event(turn_event)
        except Exception:
            pass

        # compact console report
        request_response_table = Table(title="AI Interaction Details (Conversational Turn)", show_lines=True, expand=True)
        request_response_table.add_column("Component", style="dim cyan", width=28)
        request_response_table.add_column("Content", style="white", overflow="fold")
        request_response_table.add_row("System Instruction", Text(system_content_formatted))
        last_user_msg = next((m["content"] for m in reversed(state.get("conversation_history", [])) if m.get("role") == "user"), "N/A")
        request_response_table.add_row("Last User Message", Text(last_user_msg))
        request_response_table.add_row("User/Task Prompt", Text(user_prompt_for_log))
        request_response_table.add_row("AI Response", Text(resp))
        request_response_table.add_row("Conversation Summary", Text(state.get("summary") or state.get("history_summary", "N/A")))
        console.print(request_response_table)

        return resp
    except Exception as e:
        log.error(f"Error getting AI response: {e}")
        _write_structured_event({"type": "ai_error", "error": str(e), "stage": "get_ai_response"})
        return "متأسفانه خطایی در برنامه رخ داد. لطفاً بعداً دوباره تلاش کنید."

# --- process_question_turn (minor update to include compact system summary) ---
def process_question_turn(
    state: Dict[str, Any],
    question_text: str,
    options: List[Any],
    user_input: str,
    qnum: int,
    total: int,
    next_question_text: Optional[str],
    next_options: Optional[List[Any]]
) -> Dict[str, Any]:
    """
    Single LLM call per user attempt.
    Returns:
      {
        "valid": bool,
        "selected_option": Optional[str],
        "retry_message": Optional[str],
        "next_question": Optional[str]
      }
    """
    handle_history_summarization(state)

    current_opts = normalize_option_texts(options)
    next_opts = normalize_option_texts(next_options) if next_options else []

    # Use the combined system instruction from prompts.py and include compact conversation summary
    system_instr = _build_system_instruction(state, COMBINED_SYSTEM_INSTRUCTION)

    # Build human payload: include next question only if it exists; always include user_input
    human_payload = {"user_input": user_input}
    if next_question_text:
        human_payload[f"next_question_{qnum+1}"] = {"text": next_question_text, "options": next_opts}
    human_content = json.dumps(human_payload, ensure_ascii=False)

    # Store the internal payload in history as an 'internal' record (keeps history but not duplicative system instruction)
    payload_for_history = {}
    if next_question_text:
        payload_for_history[f"next_question_{qnum+1}"] = {"text": next_question_text, "options": next_opts}
    history_content = json.dumps(payload_for_history, ensure_ascii=False) if payload_for_history else "(no-next-question)"
    add_message(state, "internal", history_content, context=f"payload_q{qnum}")

    messages = [
        SystemMessage(content=system_instr),
        HumanMessage(content=human_content)
    ]

    # Console table for diagnostics
    process_question_table = Table(title="AI Interaction Details (Question Processing)", show_lines=True, expand=True)
    process_question_table.add_column("Component", style="dim cyan", width=28)
    process_question_table.add_column("Content", style="white", overflow="fold")
    process_question_table.add_row("System Instruction", Text(system_instr))
    process_question_table.add_row("Human Payload (JSON)", Text(human_content))
    process_question_table.add_row("User Input", Text(user_input))
    process_question_table.add_row("Question Context", Text(f"Q{qnum}/{total}: {question_text}"))
    process_question_table.add_row("Available Options", Text(", ".join(current_opts)))
    process_question_table.add_row("Conversation Summary", Text(state.get("summary") or state.get("history_summary", "") or "N/A"))

    try:
        resp = llm.invoke(messages).content.strip()
        data = extract_json(resp) or {}

        # --- CHANGED: do NOT save raw LLM response as an 'assistant' message.
        # Save it as 'internal' instead so it won't be included in LLM-visible history.
        # This prevents the duplicate entries: code-fenced JSON + human-friendly assistant text.

        _write_structured_event({
            "type": "process_question_turn",
            "id": str(uuid.uuid4()),
            "qnum": qnum,
            "question": question_text[:1000],
            "user_input": user_input[:1000],
            "raw_response": resp[:8000],
            "parsed": data,
            "conversation_summary": state.get("summary") or state.get("history_summary","")
        })
        process_question_table.add_row("AI Response (Raw JSON)", Text(resp))
        process_question_table.add_row("Parsed JSON Valid", Text(str(data.get("valid", False))))
        process_question_table.add_row("Selected Option", Text(str(data.get("selected_option", "None"))))
    except Exception as e:
        logging.getLogger("ai_utils").error(f"LLM error in process_question_turn: {e}")
        data = {}
        process_question_table.add_row("Error", Text(str(e)))
        _write_structured_event({"type": "llm_error", "error": str(e), "stage": "process_question_turn", "qnum": qnum})

    console.print(process_question_table)

    # Fallback parsing and local validation (unchanged logic)
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
            ui_lower = ui_norm.strip().lower()
            for opt in current_opts:
                if ui_lower == str(opt).strip().lower():
                    valid = True
                    selected_option = str(opt)
                    retry_message = None
                    break

    if valid and not next_question and next_question_text:
        next_question = build_default_question_text(
            state.get("user_name", "کاربر"),
            next_question_text,
            next_opts,
            qnum + 1,
            total,
            {"selected_option": selected_option}
        )

    return {
        "valid": valid,
        "selected_option": selected_option,
        "retry_message": retry_message,
        "next_question": next_question
    }

def summarize_results(state, results):
    log.info(f"--- Entering summarize_results ---")
    
    # 1. Get answers from results and format them - prioritize the current test answers
    answers_list = results.get("answers", [])
    if not answers_list:
        log.warning("No answers found in results dictionary. Analysis may be incomplete.")
    
    # Format answers for the summary prompt - ONLY use the current test answers
    formatted = [{"question": a.get("question", "N/A"), 
                  "selected_option": a.get("selected_option", "N/A"), 
                  "user_response": a.get("original_response", "N/A")} 
                 for a in answers_list]
    fa = json.dumps(formatted, indent=2, ensure_ascii=False)
    
    # 2. We'll stop trying to load more test results from file since we want to use only the current answers
    # This ensures we're ONLY analyzing the current test session's answers
    complete_test_data = json.dumps(results, indent=2, ensure_ascii=False)
    log.info(f"Using only current test answers: {len(answers_list)} responses")
    
    # 3. Get test name and ensure it's valid
    test_name = results.get("test_name", "")
    if not test_name:
        log.warning("Test name is empty in results. Will try to find it in test_data.")
        if state.get("test_data", {}).get("test_name"):
            test_name = state["test_data"]["test_name"]
            log.info(f"Found test name in test_data: {test_name}")
        else:
            log.warning("Test name not found in state's test_data. Will try to find it in global test_data.")
            # Try to import test_data from psychology_test module
            try:
                import psychology_test
                if hasattr(psychology_test, 'test_data') and psychology_test.test_data.get("test_name"):
                    test_name = psychology_test.test_data.get("test_name")
                    log.info(f"Found test name in global test_data: {test_name}")
                else:
                    test_name = "نامشخص (اطلاعات آزمون یافت نشد)"
                    log.warning(f"Could not find test name in global test_data. Using default: {test_name}")
            except Exception as e:
                log.error(f"Error trying to import psychology_test module: {e}")
                test_name = "نامشخص (اطلاعات آزمون یافت نشد)"
                log.warning(f"Could not find test name. Using default: {test_name}")
    
    # 4. Get the correct result format for the selected test
    test_result_format_content = ""
    result_format_source_description = ""
    
    # First check if test_data is in state
    if state.get("test_data", {}).get("result_format", {}).get("report_md"):
        test_result_format_content = state["test_data"]["result_format"]["report_md"]
        result_format_source_description = "report_md template from state's test_data"
        log.info(f"Using report_md template from state's test_data")
    else:
        # Try to get from psychology_test module
        try:
            import psychology_test
            if hasattr(psychology_test, 'test_data') and psychology_test.test_data.get("result_format", {}).get("report_md"):
                test_result_format_content = psychology_test.test_data["result_format"]["report_md"]
                result_format_source_description = "report_md template from global test_data"
                log.info(f"Using report_md template from global test_data")
            else:
                log.warning("Could not find report_md in global test_data. Will try test.json")
                # Try to load from test.json
                try:
                    with open('/root/blue-psychology-test/test.json', 'r', encoding='utf-8') as f:
                        all_tests = json.load(f).get("tests", [])
                        for test in all_tests:
                            if test.get("test_name") == test_name:
                                if isinstance(test.get("result_format", {}).get("report_md"), str):
                                    test_result_format_content = test["result_format"]["report_md"]
                                    result_format_source_description = "report_md template (loaded from test.json)"
                                    log.info(f"Found result format in test.json for test: {test_name}")
                                    break
                except Exception as e:
                    log.error(f"Error loading test.json: {e}")
        except Exception as e:
            log.error(f"Error trying to import psychology_test module: {e}")
            # Try to load from test.json if couldn't get from module
            try:
                with open('/root/blue-psychology-test/test.json', 'r', encoding='utf-8') as f:
                    all_tests = json.load(f).get("tests", [])
                    for test in all_tests:
                        if test.get("test_name") == test_name:
                            if isinstance(test.get("result_format", {}).get("report_md"), str):
                                test_result_format_content = test["result_format"]["report_md"]
                                result_format_source_description = "report_md template (loaded from test.json)"
                                log.info(f"Found result format in test.json for test: {test_name}")
                                break
            except Exception as e:
                log.error(f"Error loading test.json: {e}")
    
    # If still not found, fall back to using empty JSON
    if not test_result_format_content:
        test_result_format_content = "{}"
        result_format_source_description = "empty JSON structure (fallback)"
        log.warning(f"Could not find any result format. Using fallback empty JSON.")
    
    # 5. Prepare the user details
    user_name = state.get("user_name", "کاربر ناشناس")
    user_age = state.get("user_age", "نامشخص")
    user_info = state.get("user_info", "No additional information provided.")
    
    # 6. Generate the prompt for final analysis
    prompt_final_summary = ANALYSIS_SUMMARY_PROMPT.format(
        test_name=test_name, 
        user_name=user_name,
        user_age=user_age,
        user_info=user_info,
        formatted_answers=fa,
        complete_test_data=complete_test_data,  # This now only contains the current test data
        test_result_format=test_result_format_content,
        test_result_format_source=result_format_source_description
    )
    
    # Use the single main llm for summary:
    system_instruction_final_summary = RESULT_CHATBOT_PERSONA
    
    log.info("Generating in-depth personality analysis...")
    log.info(f"Using test format from: {result_format_source_description}")
    
    # Log details before calling the LLM for summarization - IMPROVED to show full content
    summary_ai_call_table = Table(title="AI Interaction Details (Final Summary Generation)", show_lines=True, expand=True)
    summary_ai_call_table.add_column("Component", style="dim cyan", width=20)
    summary_ai_call_table.add_column("Content", style="white", overflow="fold")

    history_summary_context = state.get("summary") or state.get("history_summary", "N/A")

    # Add full content to table with overflow handling
    summary_ai_call_table.add_row("System Instruction", Text(system_instruction_final_summary))
    summary_ai_call_table.add_row("History Summary", Text(history_summary_context))
    summary_ai_call_table.add_row("User/Task Prompt", Text(prompt_final_summary))
    
    resp = llm.invoke([SystemMessage(content=system_instruction_final_summary), HumanMessage(content=prompt_final_summary)]).content.strip()
    
    # NEW: structured log for final summary generation
    try:
        _write_structured_event({
            "type": "final_summary",
            "id": str(uuid.uuid4()),
            "test_name": test_name,
            "user": {"name": user_name, "age": user_age},
            "answers_count": len(answers_list),
            "prompt": prompt_final_summary[:8000],
            "response_snippet": resp[:8000],
            "result_format_source": result_format_source_description
        })
    except Exception:
        pass

    summary_ai_call_table.add_row("AI Response", Text(resp))
    console.print(summary_ai_call_table)
    
    log.info(f"--- Exiting summarize_results ---")
    return resp

def generate_image_prompt(summary: str) -> str:
    system_message = SystemMessage(content=IMAGE_PROMPT_SYSTEM)
    human_message_content = IMAGE_PROMPT_GENERATION_TEMPLATE.format(summary_text=summary)
    human_message = HumanMessage(content=human_message_content)
    
    log.info(f"Generating image prompt based on summary (first 100 chars): {summary[:100]}...")
    
    # Log details before calling the LLM for image prompt generation
    image_prompt_ai_call_table = Table(title="AI Interaction Details (Image Prompt Generation)", show_lines=True, expand=False)
    image_prompt_ai_call_table.add_column("Component", style="dim cyan", width=25)
    image_prompt_ai_call_table.add_column("Content", style="white")
    image_prompt_ai_call_table.add_row("System Instruction", IMAGE_PROMPT_SYSTEM)
    image_prompt_ai_call_table.add_row("User/Task Prompt (Template Used)", IMAGE_PROMPT_GENERATION_TEMPLATE.split("Personality Summary:")[0] + "...") # Show template structure
    image_prompt_ai_call_table.add_row("Summary (Input)", summary[:500] + ("..." if len(summary) > 500 else ""))
    
    try:
        response = llm.invoke([system_message, human_message]).content.strip()
        image_prompt_ai_call_table.add_row("AI Response (Generated Prompt)", response)
        console.print(image_prompt_ai_call_table)
        log.info(f"Generated image prompt: {response}")
        return response
    except Exception as e:
        log.error(f"Error generating image prompt: {e}")
        image_prompt_ai_call_table.add_row("Error", str(e))
        console.print(image_prompt_ai_call_table)
        # Fallback prompt in case of error
        return f"3D animated character, minimalist, blue and indigo background, representing personality: {summary[:50]}"