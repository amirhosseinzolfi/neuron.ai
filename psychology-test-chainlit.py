import json
import logging
import asyncio
from typing import TypedDict, List, Dict, Any

import chainlit as cl
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import END

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
log = logging.getLogger("psychology-test")

# Import prompts
from prompts import CHATBOT_PERSONA_CHAINLIT

# --- Initialize LLM ---
llm = ChatOpenAI(
    base_url="http://localhost:15203/v1",
    model_name="gpt-4o",
    temperature=0.7,
    api_key="324"
)

# --- Load Test Data ---
with open('test.json', 'r') as f:
    test_data = json.load(f)
    log.info(f"Test data loaded: {test_data['test_name']}")

# --- Initialize Test Results ---
test_results = {
    "test_name": test_data['test_name'],
    "answers": []
}

# --- Define Test State ---
class TestState(TypedDict):
    current_question: int
    finished: bool
    user_name: str
    conversation_history: List[Dict[str, Any]]
    phase: str  # "awaiting_name", "awaiting_answer", "finished"

# --- Helper Functions ---
def get_ai_response(messages, user_name=None):
    """Send messages to the LLM with the persona and return the response."""
    log.debug(f"Sending {len(messages)} messages to AI")
    system_content = CHATBOT_PERSONA_CHAINLIT
    if user_name:
        system_content += f"\n\nYou're currently helping {user_name} complete a psychology test."
    
    formatted_messages = [SystemMessage(content=system_content)]
    for msg in messages:
        if msg["role"] == "user":
            formatted_messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            formatted_messages.append(AIMessage(content=msg["content"]))
    
    response = llm.invoke(formatted_messages).content.strip()
    log.debug(f"AI response: {response[:100]}...")
    return response

def conversationalize_question(question, question_number, total_questions, history, user_name):
    prompt = f"""We're on question {question_number} out of {total_questions}.
Transform this formal question into a friendly, conversational question that feels like a natural chat:
'{question}'

Make it engaging and personal, as if you're having a real conversation with the test-taker.
Add a brief transition or context if this is not the first question.
"""
    log.debug(f"Conversationalizing question: {question}")
    messages = history + [{"role": "user", "content": prompt}]
    response = get_ai_response(messages, user_name)
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response})
    log.debug(f"Conversationalized to: {response}")
    return response

def validate_answer(question, options, user_input, history, user_name):
    prompt = f"""Question: {question}
Options: {options}
User Response: {user_input}

Is the user's response clearly related to one of the provided options? 
Respond with ONLY "YES" or "NO".
"""
    log.debug(f"Validating answer: '{user_input}'")
    messages = history + [{"role": "user", "content": prompt}]
    response = get_ai_response(messages, user_name)
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response})
    log.debug(f"Validation result: {response}")
    return response.strip().upper() == "YES"

def generate_error_message(question, options, user_input, history, user_name):
    prompt = f"""The user ({user_name}) just answered "{user_input}" to this question: "{question}"
Options were: {options}

Their answer wasn't clear enough to match with one of the options.
Generate a friendly, helpful message explaining that their answer wasn't clear enough 
and encouraging them to try again. Be specific about why their response might not have matched
and provide guidance on how to respond more clearly.

If the user is asking something unrelated to the test or asking if you remember the conversation,
acknowledge that you do remember your conversation, but gently guide them back to the question at hand.
"""
    log.debug("Generating personalized error message")
    messages = history + [{"role": "user", "content": prompt}]
    response = get_ai_response(messages, user_name)
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response})
    log.debug(f"Error message: {response}")
    return response

def match_option(options, user_input, history, user_name):
    prompt = f"""Options: {options}
User said: '{user_input}'

Choose the option that best matches what the user said. 
Respond ONLY with the exact text of the matched option.
"""
    log.debug(f"Matching user input to options: '{user_input}'")
    messages = history + [{"role": "user", "content": prompt}]
    response = get_ai_response(messages, user_name)
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response})
    log.debug(f"Matched to option: {response}")
    return response

def generate_transition(current_question, next_question, test_progress, history, user_name):
    prompt = f"""The test-taker just answered this question: "{current_question}"
They're about to see this question: "{next_question}"
We're {test_progress}% through the test.

Create a very brief (1-2 sentences) transition between these questions that feels natural
and keeps the conversation flowing. Be encouraging and warm.
"""
    log.debug("Generating question transition")
    messages = history + [{"role": "user", "content": prompt}]
    response = get_ai_response(messages, user_name)
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response})
    log.debug(f"Transition: {response}")
    return response

def generate_acknowledgment(user_input, selected_option, history, user_name):
    prompt = f"""The user ({user_name}) just answered "{user_input}" to a question.
Their answer matched with: "{selected_option}"

Generate a very brief (1 sentence) acknowledgment of their answer that feels natural
and personal. Vary your responses so they don't all sound the same.
"""
    log.debug("Generating answer acknowledgment")
    messages = history + [{"role": "user", "content": prompt}]
    response = get_ai_response(messages, user_name)
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response})
    log.debug(f"Acknowledgment: {response}")
    return response

def analyze_answer(question, user_answer, selected_option, history, user_name):
    """Generate a brief psychological analysis for the given question/answer.
    The analysis should be in-depth yet succinct (limit to ~150 words)."""
    prompt = f"""Based on the following:
Question: {question}
User Answer: {user_answer}
Matched Option: {selected_option}

Taking into account the overall conversation history, provide a brief psychological analysis (no more than 150 words). 
Focus on key personality traits revealed by the response. Make the analysis expert, reflective, and engaging.
"""
    log.debug("Generating per-question psychological analysis")
    messages = history + [{"role": "user", "content": prompt}]
    response = get_ai_response(messages, user_name)
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response})
    log.debug(f"Per-question analysis: {response}")
    return response

def summarize_results(results, history, user_name):
    """Generate a final psychological analysis that takes into account
    the per-question analyses from the conversation history."""
    user_answers = json.dumps(results['answers'], indent=2)
    prompt = f"""You're providing a final psychological analysis based on the test '{results['test_name']}' and the entire conversation history.
The conversation history includes brief psychological analyses for each question.
Here are the user's answers: 
{user_answers}

Taking into account these insights and analyses, provide a final expert psychological summary that is in-depth yet succinct (limit to 200 words). 
Highlight key personality traits, potential strengths, areas for personal growth, and include a positive, engaging conclusion.
Make this analysis feel like a reflective conversation that connects deeply with the user.
"""
    log.info("Generating final personality analysis...")
    messages = history + [{"role": "user", "content": prompt}]
    response = get_ai_response(messages, user_name)
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": response})
    log.debug(f"Generated final analysis: {response[:100]}...")
    return response

# --- Async Helper Functions for Chainlit Flow ---
async def send_question(state: TestState):
    """Send the current question (with transition if needed) to the user."""
    idx = state["current_question"]
    question_data = test_data['questions'][idx]
    user_name = state["user_name"]
    
    # If not the first question, generate and send a transition
    if idx > 0:
        prev_question = test_data['questions'][idx-1]['question']
        current_question_text = question_data['question']
        progress = int((idx / len(test_data['questions'])) * 100)
        transition = await asyncio.to_thread(
            generate_transition, prev_question, current_question_text, progress, state["conversation_history"], user_name
        )
        state["conversation_history"].append({"role": "assistant", "content": transition})
        await cl.Message(content=transition).send()
    
    # Conversationalize the question
    question_text = await asyncio.to_thread(
        conversationalize_question, question_data['question'], idx + 1, len(test_data['questions']), state["conversation_history"], user_name
    )
    state["conversation_history"].append({"role": "assistant", "content": question_text})
    
    # Build options text
    options_text = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(question_data['options']))
    message_content = f"Question {idx+1}/{len(test_data['questions'])}:\n{question_text}\n\nOptions:\n{options_text}\n\nYour response:"
    await cl.Message(content=message_content).send()

async def summarize_test(state: TestState):
    """Generate and send the final psychological analysis and closing message."""
    user_name = state["user_name"]
    analysis = await asyncio.to_thread(
        summarize_results, test_results, state["conversation_history"], user_name
    )
    test_results["analysis"] = analysis
    test_results["user_name"] = user_name

    await cl.Message(content="🎉 Your Final Psychological Analysis:\n" + analysis).send()
    
    closing_prompt = f"""Create a warm closing message for {user_name} who just completed the '{test_data['test_name']}' test.
Thank them for participating, encourage them to reflect on the insights,
and wish them well on their journey of self-discovery.
"""
    closing_message = await asyncio.to_thread(
        get_ai_response, state["conversation_history"] + [{"role": "user", "content": closing_prompt}], user_name
    )
    state["conversation_history"].append({"role": "user", "content": closing_prompt})
    state["conversation_history"].append({"role": "assistant", "content": closing_message})
    await cl.Message(content=closing_message).send()

# --- Chainlit Callbacks ---
@cl.on_chat_start
async def on_chat_start():
    """
    Initialize the conversation by sending an introduction and asking for the user’s name.
    """
    state: TestState = {
        "current_question": 0,
        "finished": False,
        "user_name": "",
        "conversation_history": [],
        "phase": "awaiting_name"
    }
    cl.user_session.set("state", state)
    
    intro_prompt = f"""Write a warm, friendly introduction for a psychology test called '{test_data['test_name']}' that will take about {test_data['estimated_time']}.
Explain that you'll be guiding them through some questions to understand their personality better.
Ask for their name to personalize the experience.
Make them feel comfortable and excited about the process.
"""
    intro_message = await asyncio.to_thread(get_ai_response, [{"role": "user", "content": intro_prompt}], None)
    state["conversation_history"].append({"role": "user", "content": intro_prompt})
    state["conversation_history"].append({"role": "assistant", "content": intro_message})
    
    await cl.Message(content=intro_message + "\n\nWhat's your name?").send()

@cl.on_message
async def on_message(message: cl.Message):
    """
    Process incoming messages. In the 'awaiting_name' phase the message is taken as the user’s name.
    In the 'awaiting_answer' phase the message is taken as an answer to the current question.
    """
    state: TestState = cl.user_session.get("state")
    if state is None:
        return  # Should not happen
    
    # Phase: waiting for user's name
    if state["phase"] == "awaiting_name":
        user_name = message.content.strip()
        state["user_name"] = user_name
        state["conversation_history"].append({"role": "user", "content": f"My name is {user_name}"})
        
        greeting_prompt = f"The user just told you their name is {user_name}. Give a warm, brief welcome using their name and express excitement about starting the test."
        greeting = await asyncio.to_thread(get_ai_response, state["conversation_history"] + [{"role": "user", "content": greeting_prompt}], user_name)
        state["conversation_history"].append({"role": "user", "content": greeting_prompt})
        state["conversation_history"].append({"role": "assistant", "content": greeting})
        await cl.Message(content=greeting).send()
        
        # Move to answering phase and send the first question
        state["phase"] = "awaiting_answer"
        await send_question(state)
    
    # Phase: waiting for an answer to a question
    elif state["phase"] == "awaiting_answer":
        current_idx = state["current_question"]
        question_data = test_data['questions'][current_idx]
        user_answer = message.content.strip()
        state["conversation_history"].append({"role": "user", "content": user_answer})
        
        is_valid = await asyncio.to_thread(
            validate_answer,
            question_data['question'],
            question_data['options'],
            user_answer,
            state["conversation_history"],
            state["user_name"]
        )
        if is_valid:
            selected_option = await asyncio.to_thread(
                match_option,
                question_data['options'],
                user_answer,
                state["conversation_history"],
                state["user_name"]
            )
            acknowledgment = await asyncio.to_thread(
                generate_acknowledgment,
                user_answer,
                selected_option,
                state["conversation_history"],
                state["user_name"]
            )
            state["conversation_history"].append({"role": "assistant", "content": acknowledgment})
            await cl.Message(content=acknowledgment).send()
            
            # Generate a brief per-question psychological analysis (max ~150 words)
            per_question_analysis = await asyncio.to_thread(
                analyze_answer,
                question_data['question'],
                user_answer,
                selected_option,
                state["conversation_history"],
                state["user_name"]
            )
            # Send this reflection to the user and add to history
            state["conversation_history"].append({"role": "assistant", "content": per_question_analysis})
            await cl.Message(content="🤔 Reflection: " + per_question_analysis).send()
            
            # Save the answer along with the analysis
            test_results["answers"].append({
                "question_id": question_data['id'],
                "question": question_data['question'],
                "selected_option": selected_option,
                "original_response": user_answer,
                "analysis": per_question_analysis
            })
            
            state["current_question"] += 1
            if state["current_question"] < len(test_data["questions"]):
                await send_question(state)
            else:
                state["finished"] = True
                state["phase"] = "finished"
                await summarize_test(state)
        else:
            error_message = await asyncio.to_thread(
                generate_error_message,
                question_data['question'],
                question_data['options'],
                user_answer,
                state["conversation_history"],
                state["user_name"]
            )
            state["conversation_history"].append({"role": "assistant", "content": error_message})
            await cl.Message(content=error_message + "\nPlease try again.").send()
    
    # Phase: finished
    elif state["phase"] == "finished":
        await cl.Message(content="The test has already been completed. Thank you!").send()
