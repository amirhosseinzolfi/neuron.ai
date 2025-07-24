import time, logging, json, os
from typing import List, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.logging import RichHandler
from rich.table import Table  # Added
from rich.text import Text
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from prompts import (
    CHATBOT_PERSONA,
    QUESTION_WITH_ACKNOWLEDGMENT_PROMPT,
    FIRST_QUESTION_PROMPT,
    RESPONSE_ANALYSIS_PROMPT,
    RETRY_PROMPT,  # Updated import
    ANALYSIS_SUMMARY_PROMPT,
    RESULT_CHATBOT_PERSONA,
    IMAGE_PROMPT_SYSTEM,  # <-- Add this import
    IMAGE_PROMPT_GENERATION_TEMPLATE,  # <-- Add this import
)

# --- Initialize Logging & Console ---
logging.basicConfig(level=logging.INFO, format="%(message)s", datefmt="[%X]", handlers=[RichHandler(rich_tracebacks=True)])
log = logging.getLogger("ai_utils")
console = Console()

# --- Initialize LLMs ---
llm = ChatOpenAI(base_url="http://localhost:15207/v1", model_name="gpt-4o", temperature=0.7, api_key="324")
result_llm = ChatOpenAI(base_url="http://localhost:15207/v1", model_name="gpt-4o", temperature=0.7, api_key="324")

# History management
HISTORY_TRIM_THRESHOLD = 6
HISTORY_RETENTION = 2
SUMMARY_CONVERSATION_PROMPT = """Summarize the following conversation into concise bullet points.
Pay special attention to and retain any explicitly stated personal details by the user, such as their name, age, or profession (if mentioned), or other significant contextual information they provide, as these are important for ongoing personalization and context.
Focus on the main topics discussed and key information exchanged.

Conversation:
{conversation}"""

def handle_history_summarization(state):
    if len(state["conversation_history"]) > HISTORY_TRIM_THRESHOLD:
        conv = "\n".join(f"{m['role']}: {m['content']}" for m in state["conversation_history"])
        summary = llm.invoke([SystemMessage(content="You are a helpful assistant that summarizes conversations."),
                              HumanMessage(content=SUMMARY_CONVERSATION_PROMPT.format(conversation=conv))]).content.strip()
        state["history_summary"] = summary
        state["conversation_history"] = state["conversation_history"][-HISTORY_RETENTION:]

def get_ai_response(state, additional_prompt=None):
    """Get AI responses using global state conversation history"""
    handle_history_summarization(state)
    
    system_content_formatted = CHATBOT_PERSONA # Base persona now contains detailed retry logic

    if state.get("user_name"): # This part adds current user context to the system prompt
        system_content_formatted += (
            f"\n\nCurrently helping {state['user_name']} (age {state['user_age']}) " # user_profession_info removed
            "complete a psychology test."
        )
        system_content_formatted += "\n\nIMPORTANT: This is an ongoing conversation. Maintain continuity based on the full history provided."
    
    current_history_summary = state.get("history_summary", "") # Get current history summary
    if current_history_summary: # Add current history summary to system prompt if it exists
        system_content_formatted += f"\n\nConversation summary (use this along with recent history for full context):\n{current_history_summary}"
    
    messages = [SystemMessage(content=system_content_formatted)]
    for msg in state["conversation_history"]:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    
    user_prompt_for_log = "N/A"
    if additional_prompt:
        messages.append(HumanMessage(content=additional_prompt))
        user_prompt_for_log = additional_prompt

    log.info(f"Sending {len(messages)} messages to AI (including system, history, current).")

    try:
        resp = llm.invoke(messages).content.strip()

        # Create a Rich Table for detailed logging
        request_response_table = Table(title="AI Interaction Details (Conversational Turn)", show_lines=True, expand=False)
        request_response_table.add_column("Component", style="dim cyan", width=25)
        request_response_table.add_column("Content", style="white")

        request_response_table.add_row("System Instruction", system_content_formatted[:1000] + ("..." if len(system_content_formatted) > 1000 else ""))
        request_response_table.add_row("User/Task Prompt", user_prompt_for_log[:1000] + ("..." if len(user_prompt_for_log) > 1000 else ""))
        request_response_table.add_row("AI Response", resp[:1000] + ("..." if len(resp) > 1000 else ""))
        request_response_table.add_row("History Summary (Context)", current_history_summary[:1000] + ("..." if len(current_history_summary) > 1000 else "") if current_history_summary else "N/A")
        
        console.print(request_response_table)

        if additional_prompt:
            state["conversation_history"].append({"role": "user", "content": additional_prompt})
            state["conversation_history"].append({"role": "assistant", "content": resp})
        return resp
    except Exception as e:
        log.error(f"Error getting AI response: {e}")
        return "متأسفانه خطایی در برنامه رخ داد. لطفاً بعداً دوباره تلاش کنید."

def conversationalize_question(state, question, qnum, total):
    # --- Helper to get current question's options ---
    current_options_text = ""
    try:
        # Try to import test_data dynamically to access options
        # This is to ensure the most current test_data is used, especially in tele_bot context
        from psychology_test import test_data as current_test_data_module
        
        if state["current_question"] < len(current_test_data_module['questions']):
            question_data_for_options = current_test_data_module['questions'][state["current_question"]]
            options_list = question_data_for_options.get('options', [])
            
            normalized_option_texts = [
                (opt.get('text') if isinstance(opt, dict) and 'text' in opt else opt)
                for opt in options_list
            ]
            
            if normalized_option_texts:
                # Correctly format for RTL by ensuring number and text are together
                options_lines = [
                    f"{i+1}. {opt_text.strip()}" for i, opt_text in enumerate(normalized_option_texts)
                ]
                current_options_text = "\n\nAvailable options:\n" + "\n".join(options_lines)
        else:
            log.warning("Current question index out of bounds for fetching options.")
            
    except ImportError:
        log.error("Could not import test_data from psychology_test to fetch options for conversationalize_question.")
    except KeyError:
        log.error("KeyError while accessing test_data or questions for options in conversationalize_question.")
    except Exception as e:
        log.error(f"Unexpected error fetching options for conversationalize_question: {e}")


    if state.get("last_answer"):
        prompt = QUESTION_WITH_ACKNOWLEDGMENT_PROMPT.format(
            user_name=state["user_name"], last_response=state["last_answer"]["response"],
            last_option=state["last_answer"]["selected_option"],
            question_number=qnum, total_questions=total, question=question
        )
    else:
        prompt = FIRST_QUESTION_PROMPT.format(question_number=qnum, total_questions=total, question=question)
    
    # Append the options to the prompt
    prompt += current_options_text
    
    return get_ai_response(state, prompt)

def semantic_validate_and_match(state, question, options, user_input):
    ui = user_input.strip()
    # --- normalize option texts ---
    opt_texts = [
        (o['text'] if isinstance(o, dict) and 'text' in o else o)
        for o in options
    ]

    # direct numeric input
    if ui.isdigit():
        idx = int(ui) - 1
        if 0 <= idx < len(opt_texts):
            return True, opt_texts[idx], f"User selected option {ui} directly."
        return False, None, f"Invalid numeric input. Option {ui} is not available."
    
    # LLM-based analysis using normalized texts
    prompt = RESPONSE_ANALYSIS_PROMPT.format(
        question=question,
        options="\n".join(f"- {t}" for t in opt_texts), # This uses normalized opt_texts
        user_input=ui
    )
    resp = get_ai_response(state, prompt)

    valid, matched, analysis = False, None, "Could not clearly determine user's preference."
    for line in resp.splitlines():
        if line.startswith("VALID:"):
            valid = line.split("VALID:")[1].strip().upper() == "YES"
        if line.startswith("OPTION:"):
            opt = line.split("OPTION:")[1].strip()
            if opt.upper() != "NONE":
                matched = opt
        if line.startswith("ANALYSIS:"):
            analysis = line.split("ANALYSIS:")[1].strip()

    # map matched text back to chosen option text
    final = None
    if matched:
        for t in opt_texts:
            if t.lower() == matched.lower():
                final = t
                break
        if not final:
            valid = False

    # truncate over-long analysis
    if len(analysis.split()) > 70:
        analysis = " ".join(analysis.split()[:70]) + "..."
    return (valid and final is not None), final, analysis

def generate_retry_message(state, question, options, user_input, attempts):
    if attempts > 1:
        context_summary = "The user has made multiple attempts and might be confused or trying to provide more context. Refer to CHATBOT_PERSONA for detailed guidance on handling this."
    else:
        context_summary = "This is the user's first failed attempt for this question. Refer to CHATBOT_PERSONA for detailed guidance."

    # Normalize options to a list of strings (texts)
    normalized_option_texts = [
        (opt.get('text') if isinstance(opt, dict) and 'text' in opt else opt)
        for opt in options
    ]
    options_str = "\n".join(f"- {opt_text}" for opt_text in normalized_option_texts)

    prompt = RETRY_PROMPT.format(
        user_name=state["user_name"],
        user_age=state["user_age"],
        # user_profession removed from here
        question=question,
        options=options_str, # Use the formatted string of option texts
        user_input=user_input,
        attempt_count=attempts,
        context_summary=context_summary
    )
    return get_ai_response(state, prompt)

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
    
    # 6. Generate the prompt for final analysis
    prompt_final_summary = ANALYSIS_SUMMARY_PROMPT.format(
        test_name=test_name, 
        user_name=user_name,
        user_age=user_age, 
        formatted_answers=fa,
        complete_test_data=complete_test_data,  # This now only contains the current test data
        test_result_format=test_result_format_content,
        test_result_format_source=result_format_source_description
    )
    
    # Define system instruction before creating the table
    system_instruction_final_summary = RESULT_CHATBOT_PERSONA
    
    log.info("Generating in-depth personality analysis...")
    log.info(f"Using test format from: {result_format_source_description}")
    
    # Log details before calling the LLM for summarization - IMPROVED to show full content
    summary_ai_call_table = Table(title="AI Interaction Details (Final Summary Generation)", show_lines=True, expand=True)
    summary_ai_call_table.add_column("Component", style="dim cyan", width=20)
    summary_ai_call_table.add_column("Content", style="white", overflow="fold")

    history_summary_context = state.get("history_summary", "N/A")

    # Add full content to table with overflow handling
    summary_ai_call_table.add_row("System Instruction", Text(system_instruction_final_summary))
    summary_ai_call_table.add_row("History Summary", Text(history_summary_context))
    summary_ai_call_table.add_row("User/Task Prompt", Text(prompt_final_summary))
    
    resp = result_llm.invoke([SystemMessage(content=system_instruction_final_summary), HumanMessage(content=prompt_final_summary)]).content.strip()
    
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