import json
import time
from typing import TypedDict, List, Dict, Any
from rich.console import Console
from rich.prompt import Prompt
from rich import print_json
from rich.panel import Panel
from rich.logging import RichHandler
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
import logging

#==============================================================================#
#                           CONFIGURATION & SETUP                              #
#==============================================================================#

# --- Initialize Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
log = logging.getLogger("psychology-test")

# --- Initialize Console ---
console = Console()

# Import all prompt constants from prompts.py
from prompts import (
    CHATBOT_PERSONA,
    INTRO_TEXT,
    QUESTION_WITH_ACKNOWLEDGMENT_PROMPT,
    FIRST_QUESTION_PROMPT,
    RESPONSE_ANALYSIS_PROMPT,
    RETRY_PROMPT_FIRST_ATTEMPT,
    RETRY_PROMPT_MULTIPLE_ATTEMPTS,
    FINAL_ACKNOWLEDGMENT_PROMPT,
    ANALYSIS_SUMMARY_PROMPT,
    CLOSING_MESSAGE_PROMPT,
    CONVERSATION_PATTERNS_PROMPT
)

# --- Initialize LLM ---
llm = ChatOpenAI(
    base_url="http://localhost:15203/v1",
    model_name="gpt-4o-mini",
    temperature=0.7,
    api_key="324"
)

#==============================================================================#
#                                DATA MODELS                                   #
#==============================================================================#

# --- Load Test Data --- 
with open('test.json', 'r') as f:
    all_tests = json.load(f)  # now contains a "tests" key
    log.info(f"{len(all_tests['tests'])} tests loaded.")

# Choose the active test (default to first if none is chosen)
test_data = {}  # will be set in initialize()

# --- Initialize Results ---
test_results = {
    "test_name": test_data.get('test_name', ''),
    "answers": []
}

# --- Define State ---
class TestState(TypedDict):
    current_question: int
    finished: bool
    user_name: str
    conversation_history: List[Dict[str, Any]]
    last_answer: Dict[str, str]  # Track the last answer for combining responses

#==============================================================================#
#                            HELPER FUNCTIONS                                  #
#==============================================================================#

def get_ai_response(state, additional_prompt=None):
    """Get AI responses using global state conversation history"""
    log.debug(f"Sending request to AI with conversation history of {len(state['conversation_history'])} messages")
    
    # Create system message with persona and user context if available
    system_content = CHATBOT_PERSONA
    if state.get("user_name"):
        system_content += f"\n\nYou're currently helping {state['user_name']} complete a psychology test."
        system_content += "\n\nIMPORTANT: This is an ongoing conversation. Maintain continuity in your responses. "
        system_content += "If this is an error message, do NOT start with a new greeting. Continue the conversation naturally."
    
    formatted_messages = [SystemMessage(content=system_content)]
    
    # Add conversation history - filtering out any context markers
    for msg in state['conversation_history']:
        if msg["role"] == "user":
            formatted_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            formatted_messages.append(AIMessage(content=msg["content"]))
    
    # Add the additional prompt if provided
    if additional_prompt:
        formatted_messages.append(HumanMessage(content=additional_prompt))
    
    # Get response from AI with timeout and error handling
    try:
        response = llm.invoke(formatted_messages, timeout=30).content.strip()
        log.debug(f"AI response: {response[:100]}...")
        
        # If additional prompt was provided, add the exchange to the conversation history
        if additional_prompt:
            state['conversation_history'].append({"role": "user", "content": additional_prompt})
            state['conversation_history'].append({"role": "assistant", "content": response})
            
        return response
    except Exception as e:
        log.error(f"Error getting AI response: {str(e)}")
        return "I apologize for the technical difficulty. Let's continue with the test."

def conversationalize_question(state, question, question_number, total_questions):
    """Generate a conversational question, optionally acknowledging the previous answer"""
    
    # If we have a previous answer, we'll acknowledge it and ask the next question
    if state.get("last_answer"):
        prompt = QUESTION_WITH_ACKNOWLEDGMENT_PROMPT.format(
            user_name=state['user_name'],
            last_response=state['last_answer']['response'],
            last_option=state['last_answer']['selected_option'],
            question_number=question_number,
            total_questions=total_questions,
            question=question
        )
    else:
        # First question has no previous answer to acknowledge
        prompt = FIRST_QUESTION_PROMPT.format(
            question_number=question_number,
            total_questions=total_questions,
            question=question
        )
    
    log.debug(f"Conversationalizing question: {question}")
    
    response = get_ai_response(state, prompt)
    log.debug(f"Conversationalized to: {response}")
    return response

def extract_conversation_patterns(state):
    """Extract patterns and themes from the user's conversation history"""
    
    # Skip if we don't have enough history yet
    if len(state['conversation_history']) < 4:
        return "Not enough conversation history to establish patterns."
    
    # Extract just the user messages to analyze their communication style
    user_messages = [msg["content"] for msg in state['conversation_history'] 
                    if msg["role"] == "user" and not msg.get("content", "").startswith("My name is")]
    
    # Extract previous answers for context
    previous_answers = []
    for answer in test_results.get('answers', []):
        previous_answers.append({
            'question': answer['question'],
            'response': answer['original_response'],
            'selected_option': answer['selected_option'],
            'analysis': answer.get('response_analysis', '')
        })
    
    if not user_messages and not previous_answers:
        return "Not enough data to establish communication patterns."
        
    prompt = CONVERSATION_PATTERNS_PROMPT.format(
        user_messages=json.dumps(user_messages, indent=2),
        previous_answers=json.dumps(previous_answers, indent=2)
    )

    # Create a temporary state copy to avoid circular updates
    temp_state = {
        "conversation_history": state['conversation_history'][:5],  # Use limited history
        "user_name": state.get("user_name", "the user")
    }
    
    try:
        response = get_ai_response(temp_state, prompt)
        return response
    except Exception as e:
        log.warning(f"Error extracting conversation patterns: {e}")
        return "Unable to extract communication patterns from conversation history."

def semantic_validate_and_match(state, question, options, user_input):
    """Advanced semantic validation and matching of user responses with comprehensive psychological analysis"""
    # Handle numeric responses directly
    if user_input.strip().isdigit():
        option_num = int(user_input.strip())
        if 1 <= option_num <= len(options):
            # Return validated and matched option with basic analysis
            selected_option = options[option_num - 1]
            analysis = f"The user selected option {option_num} directly. This shows clear decision-making and a preference for direct communication."
            return True, selected_option, analysis
    
    log.debug(f"Analyzing ambiguous input: '{user_input}'")
    
    # Check for keywords and common phrases that might indicate an option
    user_input_lower = user_input.lower()
    
    # Try to infer option by direct keywords - fast pre-check before LLM call
    for i, option in enumerate(options, 1):
        option_lower = option.lower()
        # Look for exact matches or clear indicators in the input
        if (option_lower in user_input_lower or 
            f"option {i}" in user_input_lower or 
            f"number {i}" in user_input_lower or
            f"{i}." in user_input):
            log.debug(f"Found direct keyword match for option {i}")
            return True, option, f"User indicated option {i} through contextual clues. The choice of '{option}' suggests {get_quick_analysis(i, question)}."
    
    # Extract conversation patterns for contextual analysis
    try:
        conversation_patterns = extract_conversation_patterns(state)
    except Exception as e:
        log.warning(f"Failed to extract conversation patterns: {e}")
        conversation_patterns = "No patterns extracted due to an error."
    
    prompt = RESPONSE_ANALYSIS_PROMPT.format(
        question=question,
        options=options,
        user_input=user_input,
        conversation_patterns=conversation_patterns
    )
    
    log.debug(f"Semantically analyzing: '{user_input}' with conversation context")
    
    try:
        response = get_ai_response(state, prompt)
        
        # Parse the response
        lines = response.strip().split('\n')
        valid = False
        matched_option = None
        analysis = None
        patterns = None
        
        for line in lines:
            if line.startswith("VALID:"):
                valid = line.replace("VALID:", "").strip().upper() == "YES"
            elif line.startswith("OPTION:"):
                option_text = line.replace("OPTION:", "").strip()
                if option_text != "NONE":
                    matched_option = option_text
            elif line.startswith("ANALYSIS:"):
                analysis = line.replace("ANALYSIS:", "").strip()
            elif line.startswith("PATTERNS:"):
                patterns = line.replace("PATTERNS:", "").strip()
        
        # Combine analysis with patterns if available
        if analysis and patterns:
            analysis = f"{analysis} {patterns}"
            
        # Limit analysis length to ensure it's concise
        if analysis:
            words = analysis.split()
            if len(words) > 70:  # 50 for analysis + 20 for patterns
                analysis = " ".join(words[:70]) + "..."
        
        log.debug(f"Validation: {valid}, Option: {matched_option}, Analysis: {analysis[:50]}...")
        
        # If we couldn't determine a valid match, make a best guess based on context
        if not valid or not matched_option:
            log.warning(f"Failed to match input '{user_input}' to an option. Making a best guess.")
            
            # If this is a programming-related response, lean toward logical/analytical
            if "programmer" in user_input_lower or "coding" in user_input_lower or "logic" in user_input_lower:
                for option in options:
                    if "logic" in option.lower() or "objective" in option.lower() or "analysis" in option.lower():
                        log.info(f"Interpreting programmer reference as a preference for {option}")
                        return True, option, f"User referenced being a programmer, suggesting a preference for logical thinking."
            
            # If still no match, prompt the user to be more specific
            return False, None, "Could not clearly determine user's preference."
        
        return valid, matched_option, analysis
        
    except Exception as e:
        log.error(f"Error during semantic validation: {str(e)}")
        
        # Fallback mechanism - if the function fails, ask the user to try again with a clearer response
        return False, None, "Technical issue processing your response. Please try again with a clearer answer."

# Add this helper function for quick context-based analysis
def get_quick_analysis(option_number, question):
    """Get a quick analysis based on option number and question content"""
    if "party" in question.lower():
        return "extroverted tendencies" if option_number == 1 else "introverted tendencies"
    elif "decision" in question.lower():
        return "analytical thinking style" if option_number == 1 else "values-based decision making"
    elif "future" in question.lower() or "plan" in question.lower():
        return "structured approach to planning" if option_number == 1 else "flexible approach to life"
    else:
        return "clear preference for this option"

def generate_retry_message(state, question, options, user_input, attempt_count):
    """Generate an increasingly helpful message for invalid answers based on attempt count"""
    # Extract relevant previous mentions that might need to be referenced
    context_summary = ""
    mentions = []
    
    # Look at recent history for context
    for msg in state['conversation_history'][-10:]:
        if msg["role"] == "user" and "programmer" in msg["content"].lower():
            mentions.append("being a programmer")
        # Add more patterns as needed
    
    if mentions:
        context_summary = "The user has previously mentioned: " + ", ".join(mentions) + "."
    
    if attempt_count >= 2:
        # More direct guidance for repeat attempts
        prompt = RETRY_PROMPT_MULTIPLE_ATTEMPTS.format(
            user_name=state['user_name'],
            question=question,
            options=options,
            user_input=user_input,
            attempt_count=attempt_count
        )
    else:
        # Standard first attempt guidance
        prompt = RETRY_PROMPT_FIRST_ATTEMPT.format(
            user_name=state['user_name'],
            question=question,
            options=options,
            user_input=user_input,
            context_summary=context_summary
        )

    response = get_ai_response(state, prompt)
    return response

def generate_final_acknowledgment(state, user_input, selected_option):
    """Generate acknowledgment for the final question only"""
    prompt = FINAL_ACKNOWLEDGMENT_PROMPT.format(
        user_name=state['user_name'],
        user_input=user_input,
        selected_option=selected_option,
        test_name=test_data.get('test_name', 'the test')
    )
    log.debug("Generating final answer acknowledgment")
    
    response = get_ai_response(state, prompt)
    log.debug(f"Final acknowledgment: {response}")
    return response

def summarize_results(state, results):
    """Generate comprehensive psychological analysis using all response insights and conversation patterns"""
    # Format answers to include psychological insights for better analysis
    formatted_answers = []
    all_psychological_insights = []
    
    for answer in results['answers']:
        formatted_answers.append({
            "question": answer['question'],
            "selected_option": answer['selected_option'],
            "user_response": answer['original_response'],
            "psychological_insight": answer.get('response_analysis', "No specific insight available")
        })
        
        # Collect all psychological insights for comprehensive analysis
        if answer.get('response_analysis'):
            all_psychological_insights.append(answer['response_analysis'])
    
    # Get overall conversation patterns for meta-analysis
    conversation_patterns = extract_conversation_patterns(state)
    
    # Add collected insights to conversation patterns for better context
    if all_psychological_insights:
        conversation_patterns += "\n\nPSYCHOLOGICAL INSIGHTS SUMMARY:\n" + "\n".join([
            f"- {insight}" for insight in all_psychological_insights
        ])
    
    user_answers_json = json.dumps(formatted_answers, indent=2)
    
    prompt = ANALYSIS_SUMMARY_PROMPT.format(
        test_name=results['test_name'],
        user_name=state['user_name'],
        formatted_answers=user_answers_json,
        conversation_patterns=conversation_patterns
    )
    
    log.info("Generating in-depth personality analysis...")
    
    response = get_ai_response(state, prompt)
    log.debug(f"Generated analysis: {response[:100]}...")
    return response

#==============================================================================#
#                           GRAPH NODE FUNCTIONS                               #
#==============================================================================#

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
    
    user_name = Prompt.ask("[bold magenta]Your Name[/bold magenta]")
    
    # Initialize conversation history with test introduction and user's name
    conversation_history = [
        {"role": "assistant", "content": INTRO_TEXT},
        {"role": "user", "content": f"My name is {user_name}"}
    ]
    
    log.info(f"Starting test with user: {user_name}")
    log.info(f"Conversation history initialized with {len(conversation_history)} messages")
    
    return {
        "current_question": 0, 
        "finished": False, 
        "user_name": user_name,
        "conversation_history": conversation_history,
        "last_answer": None
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
    for i, opt in enumerate(question_data['options'], 1):
        console.print(f"{i}. {opt}")
    
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
            
            # For the final question only, show a separate acknowledgment
            if idx + 1 >= len(test_data["questions"]):
                acknowledgment = generate_final_acknowledgment(state, user_input, selected_option)
                console.print(f"[bright_green]{acknowledgment}[/bright_green]")
                state['conversation_history'].append({
                    "role": "assistant", 
                    "content": acknowledgment,
                    "context": "final_acknowledgment"
                })
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
    if state["finished"]:
        return {"next_node": "summarize"}
    else:
        return {"next_node": "ask_question"}

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

    with open('test-result.json', 'w') as f:
        json.dump(test_results, f, indent=4)
    log.info(f"Test results saved to test-result.json")

    console.print("\n[bold green]🎉 Your Personality Analysis:[/bold green]")
    console.print(Panel(analysis, 
                       border_style="bright_green", 
                       title=f"Personality Insights for {state['user_name']}", 
                       title_align="center"))
    
    closing_prompt = CLOSING_MESSAGE_PROMPT.format(
        user_name=state['user_name'],
        test_name=test_data['test_name']
    )
    closing_message = get_ai_response(state, closing_prompt)
    
    console.rule("[bold bright_magenta]✨ Test Completed ✨[/bold bright_magenta]")
    console.print(Panel(closing_message, border_style="bright_cyan"))
    
    log.info(f"Test completed for user: {state['user_name']}")
    log.info(f"Final conversation history size: {len(state['conversation_history'])} messages")
    
    with open('conversation-history.json', 'w') as f:
        json.dump(state['conversation_history'], f, indent=2)
    log.info(f"Conversation history saved to conversation-history.json")
    
    # Instead of returning END, return an empty dict
    return {}

#==============================================================================#
#                                GRAPH SETUP                                   #
#==============================================================================#

# --- Graph Setup ---
graph = StateGraph(TestState)

# --- Nodes ---
graph.add_node("initialize", initialize)
graph.add_node("ask_question", ask_question)
graph.add_node("decide_next", decide_next)
graph.add_node("summarize", summarize)

# --- Edges & Conditional Edges ---
graph.set_entry_point("initialize")
graph.add_edge("initialize", "ask_question")
graph.add_edge("ask_question", "decide_next")
graph.add_conditional_edges(
    "decide_next",
    lambda state: state["next_node"],
    {
        "ask_question": "ask_question",
        "summarize": "summarize"
    }
)

# --- Compile Graph ---
compiled_graph = graph.compile()

#==============================================================================#
#                               APPLICATION ENTRY                              #
#==============================================================================#

# --- Run Graph ---
if __name__ == "__main__":
    log.info("Launching the Comprehensive AI Psychological Test Platform")
    compiled_graph.invoke({})

# ===== Telegram Interface Helper Functions =====

def tele_initialize(user_name: str, test_type: str = "MBTI"):
	# Select test data based on test_type:
	global test_data
	if test_type.upper() == "MBTI":
		test_data = all_tests["tests"][0]
	elif test_type.upper() == "DISK":
		test_data = all_tests["tests"][1] if len(all_tests["tests"]) > 1 else all_tests["tests"][0]
	else:
		test_data = all_tests["tests"][0]
	conversation_history = [
		{"role": "assistant", "content": INTRO_TEXT},
		{"role": "user", "content": f"My name is {user_name}"}
	]
	state = {
		"current_question": 0,
		"finished": False,
		"user_name": user_name,
		"conversation_history": conversation_history,
		"last_answer": None
	}
	return state

def tele_get_question(state):
    if state["finished"]:
        return None
    idx = state["current_question"]
    question_data = test_data['questions'][idx]
    question_text = conversationalize_question(
        state,
        question_data['question'],
        idx + 1,
        len(test_data['questions'])
    )
    # Prepare options text
    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(question_data['options'])])
    # Update conversation history
    state['conversation_history'].append({
        "role": "assistant",
        "content": question_text,
        "context": f"question_{idx+1}"
    })
    return f"Question {idx+1}/{len(test_data['questions'])}:\n{question_text}\nOptions:\n{options_text}"

def tele_process_answer(state, user_input):
    idx = state["current_question"]
    question_data = test_data['questions'][idx]
    # Append user answer to conversation history
    state['conversation_history'].append({
        "role": "user",
        "content": user_input,
        "context": f"telegram_answer_q{idx+1}"
    })
    is_valid, selected_option, response_analysis = semantic_validate_and_match(
        state,
        question_data['question'],
        question_data['options'],
        user_input
    )
    if is_valid and selected_option:
        current_answer = {
            "response": user_input,
            "selected_option": selected_option,
            "question": question_data['question']
        }
        test_results["answers"].append({
            "question_id": question_data['id'],
            "question": question_data['question'],
            "selected_option": selected_option,
            "original_response": user_input,
            "response_analysis": response_analysis,
            "question_number": idx + 1,
            "timestamp": time.time()
        })
        if response_analysis:
            state['conversation_history'].append({
                "role": "system",
                "content": f"Psychological insight for question {idx+1}: {response_analysis}"
            })
        state["current_question"] += 1
        state["last_answer"] = current_answer
        if state["current_question"] >= len(test_data['questions']):
            state["finished"] = True
            acknowledgment = generate_final_acknowledgment(state, user_input, selected_option)
            state['conversation_history'].append({
                "role": "assistant",
                "content": acknowledgment,
                "context": "final_acknowledgment"
            })
            return {"ack": acknowledgment, "next": None}
        else:
            return {"ack": f"Answer accepted: {selected_option}", "next": tele_get_question(state)}
    else:
        # For simplicity, return a generic error message and re-send the same question
        error_message = "Invalid answer. Please try again."
        state['conversation_history'].append({
            "role": "assistant",
            "content": error_message,
            "context": f"error_response_q{idx+1}"
        })
        return {"ack": error_message, "next": tele_get_question(state)}

def tele_summarize(state):
    analysis = summarize_results(state, test_results)
    test_results["analysis"] = analysis
    test_results["user_name"] = state["user_name"]
    test_results["analysis_timestamp"] = time.time()
    return analysis
