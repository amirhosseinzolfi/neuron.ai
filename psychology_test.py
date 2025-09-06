import json, time, logging, threading, random, os
from typing import TypedDict, List, Dict, Any
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.logging import RichHandler
from langgraph.graph import StateGraph
from prompts import INTRO_TEXT, FIRST_QUESTION_PROMPT
from ai_utils import (
    process_question_turn,
    summarize_results,
    generate_image_prompt,
    build_default_question_text,
    get_ai_response,
    add_message,         # NEW
    standard_message     # NEW
)
from image_utils import generate_images_for_prompt
import subprocess, sys, shutil

# Initialize Logging & Console
logging.basicConfig(level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)])
log = logging.getLogger("psychology-test")
console = Console()

# Load tests
with open('test.json', 'r') as f:
    all_tests = json.load(f)
    log.info(f"{len(all_tests['tests'])} tests loaded.")
test_data = {}
test_results = {"test_name": test_data.get("test_name", ""), "answers": []}

class TestState(TypedDict):
    current_question: int
    finished: bool
    user_name: str
    user_age: int
    user_info: str
    conversation_history: List[Dict[str, Any]]
    last_answer: Dict[str, str]
    history_summary: str
    summary: str  # NEW: LangGraph-style conversation summary
    attempt_count: int
    answers: List[Dict[str, Any]]
    chat_id: int
    message_count: int
    next_question_text: str  # NEW: AI/Default conversational text for the current question

# Helper function to load existing test results
def load_test_results():
    """Load existing test results from test-result.json"""
    try:
        if os.path.exists('test-result.json'):
            with open('test-result.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle old format (without 'users' key) by converting it
                if 'users' not in data:
                    log.info("Converting old format test results to new format with 'users' key")
                    # Create new structure with old data under a generic user ID
                    old_test_name = data.get('test_name', 'Unknown Test')
                    timestamp = str(int(time.time()))
                    
                    # Initialize new format
                    new_data = {"users": {}}
                    
                    # Only convert if it looks like actual test data (has answers)
                    if 'answers' in data and len(data['answers']) > 0:
                        new_data["users"]["converted_legacy_data"] = {
                            f"{old_test_name}_{timestamp}": data
                        }
                        log.info(f"Converted {len(data.get('answers', []))} answers from old format")
                    
                    return new_data
                return data
        # Return empty structure with 'users' key if file doesn't exist
        return {"users": {}}
    except Exception as e:
        log.error(f"Error loading test-result.json: {e}")
        # Ensure we still return a valid structure
        return {"users": {}}

# Helper function to save test results
def save_test_results(results_data):
    """Save test results to test-result.json"""
    try:
        with open('test-result.json', 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=4, ensure_ascii=False)
        log.info("Test results saved to test-result.json")
        return True
    except Exception as e:
        log.error(f"Error saving test-result.json: {e}")
        return False

# GRAPH NODE FUNCTIONS
def initialize(state: TestState):
    console.clear()
    console.rule("[bold bright_cyan]✨ Interactive Psychological Assessment ✨[/bold bright_cyan]")
    
    # List available tests for the user to choose from
    console.print("[green]Available Tests:[/green]")
    for idx, test in enumerate(all_tests["tests"], 1):
        console.print(f"{idx}. {test['test_name']} ({test['estimated_time']})")
    
    # Ask user to choose a test
    while True:
        choice = Prompt.ask("[bold magenta]Enter the number of the test you want to take[/bold magenta]")
        if choice.strip().isdigit():
            choice_int = int(choice.strip())
            if 1 <= choice_int <= len(all_tests["tests"]):
                break
        console.print("[red]Invalid selection. Please enter a valid test number.[/red]")
    
    # Set active test_data
    global test_data
    test_data = all_tests["tests"][choice_int - 1]
    log.info(f"Test selected: {test_data['test_name']}")
    
    # Display introduction text from prompts and customized test details if needed
    console.print(Panel(INTRO_TEXT, border_style="bright_blue"))
    
    # Show selected-test details
    console.print(
        Panel(
            f"📝 [bold]{test_data['test_name']}[/bold]\n"
            f"- سوالات: {len(test_data['questions'])}\n"
            f"- زمان تقریبی: {test_data['estimated_time']}\n"
            f"- نتیجه: {test_data['outcome']}\n"
            f"- کاربرد: {test_data['usage']}",
            title="جزئیات تست",
            border_style="green"
        )
    )
    
    name_age_response = Prompt.ask("[bold magenta]Can I know your name and age please?[/bold magenta]")
    user_info_response = Prompt.ask("[bold magenta]Write some personal informations about your self for more personallzed result[/bold magenta]")

    # Simple extraction for name and age for logging/UI. AI will use the full context.
    user_name = name_age_response.split()[0] if name_age_response.split() else "User"
    age_str = "".join(filter(str.isdigit, name_age_response))
    user_age = int(age_str) if age_str.isdigit() else 0

    user_info = f"Name and age: {name_age_response}\nPersonal Information: {user_info_response}"

    # Build empty state first and then add standardized messages
    state_obj = {
        "current_question": 0,
        "finished": False,
        "user_name": user_name,
        "user_age": user_age,
        "user_info": user_info,
        "conversation_history": [],
        "last_answer": None,
        "history_summary": "",
        "summary": "",
        "attempt_count": 0,
        "answers": [],
        "chat_id": None,
        "message_count": 0,
        "next_question_text": ""
    }

    # Use add_message to create standardized assistant intro and user info messages
    add_message(state_obj, "assistant", INTRO_TEXT, context="system_intro", persist_jsonl=True)
    add_message(state_obj, "user", user_info, context="user_profile", persist_jsonl=True)

    log.info(f"Starting test with user: {user_name}")
    log.info(f"Conversation history initialized with {len(state_obj['conversation_history'])} messages")
    
    return state_obj

def ask_question(state: TestState):
    idx = state["current_question"]
    total = len(test_data['questions'])
    if idx >= total:
        state["finished"] = True
        return state

    qd = test_data['questions'][idx]

    # Generate first question via AI if not prepared, else use existing/default
    ai_generated_first = False
    if idx == 0 and not state.get("next_question_text"):
        # Build internal-only options payload for the AI (do NOT display to user)
        def _opt_text(o): return o.get("text") if isinstance(o, dict) and "text" in o else str(o)
        options_lines = "\n".join([f"{i+1}. {_opt_text(opt)}" for i, opt in enumerate(qd["options"])])
        first_prompt = (
            FIRST_QUESTION_PROMPT.format(
                question_number=1,
                total_questions=total,
                question=qd["question"]
            )
            + "\n- Options (internal; do NOT display to user):\n"
            + options_lines
            + "\n- IMPORTANT: Do NOT show options explicitly. Ask conversationally in Persian."
        )
        q_text = get_ai_response(state, additional_prompt=first_prompt)
        # Tag last assistant message (already appended by LLM) without altering its content
        for i in range(len(state['conversation_history']) - 1, -1, -1):
            if state['conversation_history'][i].get("role") == "assistant":
                state['conversation_history'][i]["context"] = f"question_{idx+1}"
                break
        state["next_question_text"] = q_text
        ai_generated_first = True
    else:
        q_text = state.get("next_question_text") or build_default_question_text(
            state["user_name"], qd["question"], qd["options"], idx + 1, total, state.get("last_answer")
        )

    console.rule(f"[bold cyan]Question {idx + 1}/{total}")
    console.print(Panel(f"[yellow]{q_text}[/yellow]", border_style="cyan", title=f"For {state['user_name']}", title_align="left"))

    # Add assistant message to history only if not already appended by AI
    if not ai_generated_first:
        add_message(state, "assistant", q_text, context=f"question_{idx+1}")
        state['message_count'] = len(state['conversation_history'])

    # Get user response
    attempt = 0
    while True:
        attempt += 1
        user_input = Prompt.ask("[bold magenta]Your response[/bold magenta]")
        add_message(state, "user", user_input, context=f"answer_attempt_{attempt}_q{idx+1}")

        # Prepare next question raw (so LLM can generate conversational next step in the same call)
        if idx + 1 < total:
            next_qd = test_data['questions'][idx + 1]
            next_raw_text = next_qd["question"]
            next_raw_options = next_qd["options"]
        else:
            next_raw_text, next_raw_options = None, None

        # Single LLM call for this attempt (validate + retry or next question)
        turn = process_question_turn(
            state=state,
            question_text=qd["question"],
            options=qd["options"],
            user_input=user_input,
            qnum=idx + 1,
            total=total,
            next_question_text=next_raw_text,
            next_options=next_raw_options
        )

        if turn.get("valid"):
            selected_option = turn.get("selected_option")

            # Persist answer result
            test_results["answers"].append({
                "question_id": qd.get('id', f"q_{idx+1}"),
                "question": qd["question"],
                "selected_option": selected_option,
                "original_response": user_input,
                "question_number": idx + 1,
                "timestamp": time.time()
            })

            # Prepare next question text (from LLM if provided)
            state["last_answer"] = {
                "response": user_input,
                "selected_option": selected_option,
                "question": qd["question"]
            }

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
                    state["last_answer"]
                )
                state["next_question_text"] = next_text
                # Also append assistant's next question to the history so the LLM sees it next turn
                add_message(state, "assistant", next_text, context=f"question_{idx+1}")

            state['message_count'] = len(state['conversation_history'])
            time.sleep(0.5)
            break
        else:
            retry_msg = turn.get("retry_message") or "لطفاً یکی از گزینه‌های معتبر را انتخاب کنید."
            console.print(Panel(f"[bold orange3]{retry_msg}[/bold orange3]", border_style="red"))
            add_message(state, "assistant", retry_msg, context=f"retry_q{idx+1}_attempt{attempt}")
            state['message_count'] = len(state['conversation_history'])
            # Loop for next attempt on the same question

    return state

def decide_next(state: TestState):
    return {"next_node": "summarize" if state["finished"] else "ask_question"}

def summarize(state: TestState):
    console.rule("[bold blue]📝 Analyzing Your Personality Profile...[/bold blue]")
    
    for i, message in enumerate([
        "Analyzing response patterns...",
        "Identifying psychological traits...",
        "Compiling your personality profile...",
        "Drafting insights..."
    ]):
        console.print(f"[bright_magenta]{message}[/bright_magenta]")
        time.sleep(0.8)
    
    log.info(f"Generating in-depth analysis for {state['user_name']} with {len(test_results['answers'])} responses")
    analysis = summarize_results(state, test_results)
    test_results["analysis"] = analysis
    test_results["user_name"] = state["user_name"]
    test_results["analysis_timestamp"] = time.time()

    # Save to the new structured format
    all_results = load_test_results()
    # Use "cli_user" as the ID for command-line users
    user_id_str = "cli_user"
    
    if user_id_str not in all_results["users"]:
        all_results["users"][user_id_str] = {}
    
    test_name = test_data.get("test_name", "Unknown Test")
    timestamp_str = str(int(time.time()))
    
    all_results["users"][user_id_str][f"{test_name}_{timestamp_str}"] = test_results
    save_test_results(all_results)
    
    log.info(f"Test results saved to test-result.json for user {user_id_str}")

    console.print("\n[bold green]🎉 Your Personality Analysis:[/bold green]")
    console.print(Panel(analysis, 
                       border_style="bright_green", 
                       title=f"Personality Insights for {state['user_name']}", 
                       title_align="center"))
    
    closing_message = (
        f"🎉 آزمون «{test_data['test_name']}» برای {state['user_name']} به پایان رسید! "
        "امیدوارم این بینش‌ها برای شما مفید بوده باشد."
    )
    
    console.rule("[bold bright_magenta]✨ Test Completed ✨[/bold bright_magenta]")
    console.print(Panel(closing_message, border_style="bright_cyan"))
    
    log.info(f"Test completed for user: {state['user_name']}")
    log.info(f"Final conversation history size: {len(state['conversation_history'])} messages")
    
    with open('conversation-history.json', 'w') as f:
        json.dump(state['conversation_history'], f, indent=2)
    log.info(f"Conversation history saved to conversation-history.json")
    
    try:    
        img_prompt = generate_image_prompt(analysis)
        images = generate_images_for_prompt(img_prompt, state["user_name"], "/tmp", model="midjourney", num_images=1, width=512, height=512)
        log.info(f"Generated images: {images}")
    except Exception as e:
        log.error(f"Error generating images: {e}")
    
    return {}

# --- TELEGRAM INTERFACE HELPER FUNCTIONS ---

def tele_initialize(user_name: str, age: int, user_info: str, test_type: str = "MBTI", chat_id: int = None):
    global test_data
    # allow numeric selection
    if test_type.isdigit():
        idx = int(test_type) - 1 # User sees 1-based, code uses 0-based
        all_tests_list = all_tests["tests"]
        if 0 <= idx < len(all_tests_list):
            test_data = all_tests_list[idx]
        else: # Fallback to first test if index is out of bounds
            log.warning(f"Invalid test index {idx+1} selected. Defaulting to first test.")
            test_data = all_tests_list[0]
    else:
        # named-type logic (less used now, but kept for compatibility)
        selected_test_obj = next((t for t in all_tests["tests"] if t["test_name"].upper() == test_type.upper()), None)
        if selected_test_obj:
            test_data = selected_test_obj
        else: # Fallback to first test if name not found
            log.warning(f"Test name '{test_type}' not found. Defaulting to first test.")
            test_data = all_tests["tests"][0]
    
    log.info(f"Telegram: Test selected - {test_data['test_name']}")

    # Build a standardized conversation_history using add_message (keeps format consistent with CLI)
    state = {
        "current_question":  0,
        "finished":          False,
        "user_name":         user_name,
        "user_age":          age,
        "user_info":         user_info,
        "conversation_history": [],
        "last_answer":       None,
        "history_summary":   "",
        "summary":           "",
        "attempt_count":     0,
        "answers":           [],
        "chat_id":           chat_id,
        "message_count":     0,
        "next_question_text": ""
    }

    # add initial assistant intro and user profile into history (persist_jsonl optional)
    add_message(state, "assistant", INTRO_TEXT, context="system_intro", persist_jsonl=True)
    add_message(state, "user", user_info, context="user_profile", persist_jsonl=True)

    state["message_count"] = len(state["conversation_history"])
    return state

def tele_get_question(state):
    if state["finished"]:
        return None
    idx = state["current_question"]
    total = len(test_data["questions"])

    ai_generated_first = False
    if idx == 0 and not state.get("next_question_text"):
        # Build internal-only options payload for the AI (do NOT display to user)
        def _opt_text(o): return o.get("text") if isinstance(o, dict) and "text" in o else str(o)
        options_lines = "\n".join([f"{i+1}. {_opt_text(opt)}" for i, opt in enumerate(test_data["questions"][idx]["options"])])
        first_prompt = (
            FIRST_QUESTION_PROMPT.format(
                question_number=1,
                total_questions=total,
                question=test_data["questions"][idx]["question"]
            )
            + "\n- Options (internal; do NOT display to user):\n"
            + options_lines
            + "\n- IMPORTANT: Do NOT show options explicitly. Ask conversationally in Persian."
        )
        text = get_ai_response(state, additional_prompt=first_prompt)
        # Tag last assistant message (already appended by LLM) without altering its content
        for i in range(len(state['conversation_history']) - 1, -1, -1):
            if state['conversation_history'][i].get("role") == "assistant":
                state['conversation_history'][i]["content"] = text  # ensure latest text is set
                state['conversation_history'][i]["context"] = f"question_{idx+1}"
                break
        state["next_question_text"] = text
        ai_generated_first = True
    else:
        text = state.get("next_question_text") or build_default_question_text(
            state["user_name"],
            test_data["questions"][idx]["question"],
            test_data["questions"][idx]["options"],
            idx + 1,
            total,
            state.get("last_answer")
        )

    if not ai_generated_first:
        add_message(state, "assistant", text, context=f"question_{idx+1}")
    return f"✅سوال {idx+1}/{total}\n{text}"

def tele_process_answer(state, user_input):
    idx = state.get("current_question", 0)
    if state.get("finished") or idx >= len(test_data.get("questions", [])):
        return {"ack": None, "next": None}

    qd = test_data["questions"][idx]
    total = len(test_data["questions"])
    add_message(state, "user", user_input, context=f"answer_q{idx+1}")

    if idx + 1 < total:
        next_qd = test_data["questions"][idx + 1]
        next_raw_text, next_raw_options = next_qd["question"], next_qd["options"]
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
        next_options=next_raw_options
    )

    if turn.get("valid"):
        selected = turn.get("selected_option")
        if "answers" not in state:
            state["answers"] = []
        state["answers"].append({
            "question_id": qd.get('id', f"q_{idx+1}"),
            "question": qd["question"],
            "selected_option": selected,
            "original_response": user_input,
            "question_number": idx + 1,
            "timestamp": time.time()
        })
        state["last_answer"] = {"response": user_input, "selected_option": selected, "question": qd["question"]}
        state["current_question"] += 1

        if state["current_question"] >= total:
            state["finished"] = True
            state["next_question_text"] = ""
            return {"ack": None, "next": None}
        else:
            nxt = turn.get("next_question") or build_default_question_text(
                state["user_name"],
                test_data["questions"][state["current_question"]]["question"],
                test_data["questions"][state["current_question"]]["options"],
                state["current_question"] + 1,
                total,
                state["last_answer"]
            )
            state["next_question_text"] = nxt
            add_message(state, "assistant", nxt, context=f"question_{state['current_question']+1}")
            return {"ack": None, "next": f"✅سوال {state['current_question'] + 1}/{total}\n{nxt}"}
    else:
        retry_msg = turn.get("retry_message") or "لطفاً یکی از گزینه‌های معتبر را انتخاب کنید."
        add_message(state, "assistant", retry_msg, context=f"retry_q{idx+1}")
        return {"ack": retry_msg, "next": None}

def tele_summarize(state):
    # ...existing save + summarize logic unchanged...
    return summarize_results(state, {
        "test_name": state.get("test_data", {}).get("test_name", test_data.get("test_name", "")),
        "answers": state.get("answers", []),
        "user_name": state.get("user_name", "Unknown User"),
        "user_age": state.get("user_age", 0),
        "user_info": state.get("user_info", "")
    })

def _is_streamlit_running(port: int = 8501) -> bool:
    # Basic check: try to connect via requests if available, otherwise check process list
    try:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False

def start_streamlit_ui_if_needed():
    """Start the streamlit UI as a background process if streamlit is installed and not already running."""
    try:
        if _is_streamlit_running():
            log.info("Streamlit UI already running on port 8501")
            return
        # find streamlit executable
        streamlit_exe = shutil.which("streamlit")
        if not streamlit_exe:
            log.warning("Streamlit executable not found in PATH. Install streamlit to enable web UI.")
            return
        ui_path = os.path.join(os.path.dirname(__file__), "streamlit_ui.py")
        cmd = [streamlit_exe, "run", ui_path, "--server.port", "8501", "--server.headless", "true"]
        # Launch detached process
        log.info("Starting Streamlit UI in background (port 8501)...")
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=os.path.dirname(__file__), start_new_session=True)
    except Exception as e:
        log.error(f"Failed to start Streamlit UI: {e}")

# GRAPH SETUP
graph = StateGraph(TestState)

# Nodes
graph.add_node("initialize", initialize)
graph.add_node("ask_question", ask_question)
graph.add_node("decide_next", decide_next)
graph.add_node("summarize", summarize)

# Edges & Conditional Edges
graph.set_entry_point("initialize")
graph.add_edge("initialize", "ask_question")
graph.add_edge("ask_question", "decide_next")
graph.add_edge("decide_next", "summarize")
graph.add_conditional_edges(
    "decide_next",
    lambda state: state["next_node"],
    {
        "ask_question": "ask_question",
        "summarize": "summarize"
    }
)

# Compile Graph
compiled_graph = graph.compile()

# APPLICATION ENTRY
if __name__ == "__main__":
    log.info("Launching the Comprehensive AI Psychological Test Platform")
    # Start Streamlit UI automatically (non-blocking)
    start_streamlit_ui_if_needed()
    compiled_graph.invoke({})