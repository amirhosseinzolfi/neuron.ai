import json, time, logging, threading, random, os
from typing import TypedDict, List, Dict, Any
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.logging import RichHandler
from langgraph.graph import StateGraph
from prompts import INTRO_TEXT
from ai_utils import (
    conversationalize_question,
    semantic_validate_and_match,
    generate_retry_message,
    summarize_results,
    generate_image_prompt,
)
from image_utils import generate_images_for_prompt

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
    conversation_history: List[Dict[str, Any]]
    last_answer: Dict[str, str]
    history_summary: str
    attempt_count: int
    answers: List[Dict[str, Any]]  # Add answers to TestState for Telegram flow
    chat_id: int  # Add chat_id to TestState for Telegram flow

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
    
    user_name = Prompt.ask("[bold magenta]Your Name[/bold magenta]")
    while True:
        age_str = Prompt.ask("[bold magenta]Your Age[/bold magenta]")
        if age_str.isdigit() and 0 < int(age_str) < 150:
            user_age = int(age_str)
            break
        console.print("[red]سن نامعتبر است. لطفاً عدد صحیح وارد کنید.[/red]")

    # Initialize conversation history with test introduction and user's name
    conversation_history = [
        {"role": "assistant", "content": INTRO_TEXT},
        {"role": "user", "content": f"My name is {user_name} and I am {user_age}"}
    ]
    
    log.info(f"Starting test with user: {user_name}")
    log.info(f"Conversation history initialized with {len(conversation_history)} messages")
    
    return {
        "current_question": 0, 
        "finished": False, 
        "user_name": user_name,
        "user_age": user_age,
        "conversation_history": conversation_history,
        "last_answer": None,
        "history_summary": "",
        "attempt_count": 0,
        "answers": [],
        "chat_id": None
    }

def ask_question(state: TestState):
    idx = state["current_question"]

    # Check if we've reached the end of questions
    if idx >= len(test_data['questions']):
        log.info("All questions answered, marking as finished")
        state["finished"] = True
        return state
    
    question_data = test_data['questions'][idx]
    
    # Create conversational question (with acknowledgment of previous answer if available)
    question_text = conversationalize_question(
        state,
        question_data['question'], 
        idx + 1, 
        len(test_data['questions'])
    )
    
    console.rule(f"[bold cyan]Question {idx + 1}/{len(test_data['questions'])}")
    console.print(Panel(f"[yellow]{question_text}[/yellow]", 
                       border_style="cyan", 
                       title=f"For {state['user_name']}", 
                       title_align="left"))
    
    # Add to conversation history with context marker to help AI understand flow
    state['conversation_history'].append({
        "role": "assistant", 
        "content": question_text,
        "context": f"question_{idx+1}"  # This won't be sent to AI but helps us track context
    })
    
    log.info(f"Asking question {idx + 1}: {question_data['question']}")
    
    # Display options
    console.print("[green]Options:[/green]")
    for i, opt_data in enumerate(question_data['options'], 1):
        if isinstance(opt_data, dict) and 'text' in opt_data:
            console.print(f"{i}. {opt_data['text']}")
        else:
            console.print(f"{i}. {opt_data}")
    
    attempt_count = 0
    while True:
        attempt_count += 1
        user_input = Prompt.ask("[bold magenta]Your response[/bold magenta]")
        log.debug(f"User input: '{user_input}'")
        
        # Add user input to conversation history with context marker
        state['conversation_history'].append({
            "role": "user", 
            "content": user_input,
            "context": f"answer_attempt_{attempt_count}_q{idx+1}"
        })
        
        # Use the semantic validation function with psychological analysis
        is_valid, selected_option, response_analysis = semantic_validate_and_match(
            state, 
            question_data['question'], 
            question_data['options'], 
            user_input
        )
        
        if is_valid and selected_option:
            # Store user's response data for acknowledgment in next question
            current_answer = {
                "response": user_input,
                "selected_option": selected_option,
                "question": question_data['question']
            }
            
            # Store both original response and psychological analysis
            test_results["answers"].append({
                "question_id": question_data['id'],
                "question": question_data['question'],
                "selected_option": selected_option,
                "original_response": user_input,
                "response_analysis": response_analysis,
                "question_number": idx + 1,  # Store question number for trend analysis
                "timestamp": time.time()  # Store timestamp for tracking response timing
            })
            
            # Add psychological analysis to conversation history for AI awareness
            # This helps the AI reference psychological insights in future interactions
            if response_analysis:
                state['conversation_history'].append({
                    "role": "system",  # Use system role so it's available to AI but not shown as part of conversation
                    "content": f"Psychological insight for question {idx+1}: {response_analysis}"
                })
            
            # For the final question only, mark test as finished
            if idx + 1 >= len(test_data["questions"]):
                # Mark test as finished when last question is answered
                state["finished"] = True
            
            log.info(f"Answer accepted: {selected_option}")
            log.info(f"Psychological analysis: {response_analysis}")
            state["current_question"] += 1
            state["last_answer"] = current_answer
            break
        else:
            # Use the enhanced retry message function
            error_message = generate_retry_message(
                state,
                question_data['question'], 
                question_data['options'], 
                user_input,
                attempt_count
            )
            console.print(Panel(f"[bold orange3]{error_message}[/bold orange3]", 
                              border_style="red"))
            
            # Add error message to conversation history with context marker
            state['conversation_history'].append({
                "role": "assistant", 
                "content": error_message,
                "context": f"error_response_q{idx+1}_attempt{attempt_count}"
            })
            
            log.info(f"Invalid answer attempt {attempt_count}: '{user_input}'")
    
    time.sleep(1)  # Give user time to read acknowledgment
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
        images = generate_images_for_prompt(img_prompt, state["user_name"], "/tmp", model="dall-e-3", num_images=1, width=512, height=512)
        log.info(f"Generated images: {images}")
    except Exception as e:
        log.error(f"Error generating images: {e}")
    
    return {}

# --- TELEGRAM INTERFACE HELPER FUNCTIONS (re-added) ---

def tele_initialize(user_name: str, age: int, test_type: str = "MBTI", chat_id: int = None):
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

    conversation_history = [
        {"role": "assistant", "content": INTRO_TEXT},
        {"role": "user",      "content": f"My name is {user_name} and I am {age}"}
    ]
    return {
        "current_question":  0,
        "finished":          False,
        "user_name":         user_name,
        "user_age":          age,
        "conversation_history": conversation_history,
        "last_answer":       None,
        "history_summary":   "",
        "attempt_count":     0,
        "answers":           [],  # Initialize empty answers list
        "chat_id":           chat_id  # Store Telegram chat ID
    }

def tele_get_question(state):
    if state["finished"]:
        return None
    idx = state["current_question"]
    total = len(test_data["questions"])
    qd = test_data["questions"][idx]
    
    # Pass the original question text, conversationalize_question will add options
    text = conversationalize_question(state, qd["question"], idx + 1, total)
    
    state["conversation_history"].append({
        "role": "assistant", "content": text, "context": f"question_{idx+1}"
    })
    return f"✅سوال {idx+1}/{total}\n{text}"

def tele_process_answer(state, user_input):
    idx = state.get("current_question", 0)
    if state.get("finished") or idx >= len(test_data.get("questions", [])):
        return {"ack": None, "next": None} # Should not happen if finished is managed correctly

    qd = test_data["questions"][idx]
    question_text = qd["question"] # Get question text for storing

    valid, selected, analysis = semantic_validate_and_match(
        state, qd["question"], qd["options"], user_input # qd["options"] is passed directly
    )
    if valid and selected:
        state["attempt_count"] = 0 # Reset on valid answer
        state["conversation_history"].append({
            "role": "system",
            "content": f"Psychological insight: {analysis}"
        })
        state["last_answer"] = { # Store last valid answer for acknowledgment in next question
            "response": user_input,
            "selected_option": selected,
            "question": question_text
        }
        
        # Append answer details to state["answers"]
        if "answers" not in state:
            state["answers"] = []
        state["answers"].append({
            "question_id": qd.get('id', f"q_{idx+1}"), # Use question id or generate one
            "question": question_text,
            "selected_option": selected,
            "original_response": user_input,
            "response_analysis": analysis,
            "question_number": idx + 1,
            "timestamp": time.time()
        })
            
        state["current_question"] += 1
        
        # Check if this was the last question
        if state["current_question"] >= len(test_data["questions"]):
            state["finished"] = True
            return {"ack": None, "next": None}
        else:
            next_q_text = tele_get_question(state)
            return {"ack": None, "next": next_q_text} # Return None for ack, only next question.
    else:
        state["attempt_count"] = state.get("attempt_count", 0) + 1
        err = generate_retry_message(
            state, qd["question"], qd["options"], user_input, # qd["options"] is passed directly
            state["attempt_count"]
        )
        # Add error/retry message to history as assistant message
        state["conversation_history"].append({"role": "assistant", "content": err})
        return {"ack": err, "next": None} # Only send retry ack, wait for user's next input

def tele_summarize(state):
    # Make sure test_data is available in state
    if not state.get("test_data") and "test_data" in globals():
        state["test_data"] = test_data
        log.info("Added global test_data to state for summary generation")
    
    # Ensure we have the current test name
    test_name = state.get("test_data", {}).get("test_name", "")
    if not test_name and "test_data" in globals():
        test_name = test_data.get("test_name", "")
    
    # Log the current answers for debugging
    if state.get("answers"):
        log.info(f"Current test session has {len(state['answers'])} answers ready for analysis")
    else:
        log.warning("No answers found in current state, this may cause incomplete analysis")
    
    # Prepare results for summarization - only use current session data
    # Don't attempt to load from test-result.json as that may mix with other tests
    result = summarize_results(state, {
        "test_name": test_name,
        "answers": state.get("answers", []),
        "user_name": state.get("user_name", "Unknown User"),
        "user_age": state.get("user_age", 0)
    })
    
    # Now save the results (after analysis is complete)
    if state.get("answers") and state.get("chat_id"):
        all_results = load_test_results()
        users_dict = all_results.get("users", {})
        
        chat_id_str = str(state["chat_id"])
        if chat_id_str not in users_dict:
            users_dict[chat_id_str] = {}
        
        # Create test results object with analysis included
        test_result_obj = {
            "test_name": test_name,
            "answers": state["answers"],
            "user_name": state.get("user_name", "Unknown User"),
            "user_age": state.get("user_age", 0),
            "analysis": result,
            "analysis_timestamp": time.time()
        }
        
        # Use timestamp to make each test entry unique
        timestamp_str = str(int(time.time()))
        users_dict[chat_id_str][f"{test_name}_{timestamp_str}"] = test_result_obj
        
        # Make sure the users dict is attached to all_results
        all_results["users"] = users_dict
        
        save_test_results(all_results)
        log.info(f"Saved test results for user {chat_id_str} to test-result.json with {len(state['answers'])} answers")
    
    return result

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
    compiled_graph.invoke({})
