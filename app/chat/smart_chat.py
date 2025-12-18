# @/smart_chat.py
"""
Defines a smart chat agent using LangGraph & LangChain.
Refined version with:
- Standard LangGraph-style conversational state (messages + summary + user_profile)
- Token-budget–based history summarization
- Clear separation of system prompts from persistent state
"""

# =============================================================================
# 📦 Standard & Typing Imports
# =============================================================================
import json
import os
import time
import sqlite3
import threading
from typing import Annotated, Any, Dict, List, Optional, TypedDict, Union

# =============================================================================
# 🧠 LangChain / LangGraph Imports
# =============================================================================
from langchain_core.messages import (
    AnyMessage,
    SystemMessage,
    HumanMessage,
    AIMessage,
    BaseMessage,
)
from langchain_core.messages.utils import count_tokens_approximately
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.pregel import Pregel
from langgraph.checkpoint.sqlite import SqliteSaver

from rich.panel import Panel
from rich.table import Table

# =============================================================================
# 🎛️ Console / UI Utilities (rich + logging helpers)
# =============================================================================
from .logging_utils import (
    build_progress,
    console,
    create_error_table,
    create_session_table,
    create_success_table,
    log_agent_initialization,
    log_config,
    log_context_building,
    log_empty_message,
    log_history_retrieval,
    log_history_state,
    log_invocation_payload,
    log_llm_error,
    log_llm_response,
    log_memory_initialization,
    log_memory_results,
    log_memory_search,
    log_memory_search_error,
    log_memory_storage,
    log_memory_user_resolution,
    log_message_stats,
    log_refinement_error,
    log_response_refinement,
    log_stream_completion,
    log_stream_event,
    log_stream_start,
    log_summarization_skip,
    log_summarization_trigger,
    log_summary_action,
    log_system_instructions,
    log_user_profile,
    logger,
)

# =============================================================================
# 🔧 Project Utilities & Prompts
# =============================================================================
from ai_utils import get_neuron_llm
from telegram_text_optimizer import optimize_for_telegram
from db import get_user
from database.prompts import NEURON, HISTORY_SUMMARIZATION_PROMPT
from app.services.memory_service import get_memory_service

MEMORY_SEARCH_LIMIT = int(os.getenv("MEMORY_API_SEARCH_LIMIT", "5"))

# =============================================================================
# ⚙️ Conversation History / Summarization Settings
# =============================================================================
TOKEN_BUDGET = 2800
RECENT_MESSAGES_KEEP = 8
MIN_MESSAGES_TO_SUMMARIZE = 12
SUMMARY_PROMPT_TEMPLATE = HISTORY_SUMMARIZATION_PROMPT

# =============================================================================
# 🧱 State Definition
# =============================================================================
class AgentState(TypedDict, total=False):
    """LangGraph state for the smart chat agent."""
    messages: Annotated[List[AnyMessage], add_messages]
    summary: Optional[str]
    summary_upto: Optional[int]
    user_profile: Optional[Dict[str, Any]]
    user_id: Optional[str]


# =============================================================================
# 🧩 Helper Functions
# =============================================================================

def _convert_to_langchain_message(msg: AnyMessage) -> AnyMessage:
    """Convert message with media metadata to proper LangChain format."""
    if isinstance(msg, HumanMessage) and hasattr(msg, "additional_kwargs"):
        media = msg.additional_kwargs.get("media")
        if media:
            content: List[Dict[str, Any]] = []
            if isinstance(msg.content, str) and msg.content:
                content.append({"type": "text", "text": msg.content})
            
            if media.get("type") == "image":
                content.append({
                    "type": "image_url",
                    "image_url": f"data:{media['mime_type']};base64,{media['data']}",
                })
            elif media.get("type") == "audio":
                content.append({
                    "type": "media",
                    "mime_type": media["mime_type"],
                    "data": media["data"],
                })
            return HumanMessage(content=content)
    return msg


def _build_transcript(messages: List[AnyMessage]) -> str:
    """Convert messages into a plain-text transcript."""
    lines: List[str] = []
    for m in messages:
        role = getattr(m, "type", m.__class__.__name__)
        content = getattr(m, "content", "")
        if isinstance(content, str) and content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _extract_text_content(message: AnyMessage) -> str:
    """Return a plain-text view of a LangChain message."""
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, dict):
                text_value = block.get("text")
                if text_value:
                    parts.append(str(text_value))
        return " ".join(parts)
    return str(content)


def _resolve_memory_user_id(state: AgentState) -> str:
    """Return the canonical user ID for Mem0."""
    user_profile = state.get("user_profile") or {}
    chat_id = user_profile.get("chat_id") if isinstance(user_profile, dict) else None
    if chat_id is not None:
        return str(chat_id)

    state_user_id = state.get("user_id")
    if state_user_id is not None:
        try:
            numeric_id = int(state_user_id)
            user_data = get_user(numeric_id)
            if user_data and user_data.get("chat_id") is not None:
                return str(user_data["chat_id"])
        except (TypeError, ValueError):
            pass

    return str(state_user_id or "anonymous")


def _build_system_messages(state: AgentState, memory_context: str = "") -> List[SystemMessage]:
    """Construct the system prompt stack."""
    system_messages = [SystemMessage(content=NEURON)]
    
    # User Profile
    user_profile = state.get("user_profile")
    if user_profile:
        try:
            profile_json = json.dumps(user_profile, indent=2, ensure_ascii=False)
            system_messages.append(SystemMessage(
                content=f"User Profile Data:\n```json\n{profile_json}\n```"
            ))
        except Exception:
            system_messages.append(SystemMessage(content=f"User Profile: {user_profile}"))

    # Summary
    if state.get("summary"):
        system_messages.append(SystemMessage(
            content=f"[Conversation Summary]\n{state['summary']}"
        ))

    # Mem0 Context
    if memory_context:
        system_messages.append(SystemMessage(content=f"[Mem0 Memory]\n{memory_context}"))

    return system_messages


def _summarize_logic(llm, state: AgentState) -> Dict[str, Any]:
    """Calculate summary updates if needed. Returns dict of updates."""
    messages = state.get("messages", []) or []
    n = len(messages)
    
    if n <= MIN_MESSAGES_TO_SUMMARIZE:
        log_summarization_skip(f"insufficient messages ({n} <= {MIN_MESSAGES_TO_SUMMARIZE})")
        return {}

    last_upto = state.get("summary_upto") or 0
    last_upto = max(0, min(last_upto, n))
    
    unsummarized = messages[last_upto:]
    if len(unsummarized) <= MIN_MESSAGES_TO_SUMMARIZE:
        log_summarization_skip(f"insufficient unsummarized ({len(unsummarized)} <= {MIN_MESSAGES_TO_SUMMARIZE})")
        return {}

    try:
        token_count = count_tokens_approximately(unsummarized)
        if token_count <= TOKEN_BUDGET:
            log_summarization_skip(f"within budget ({token_count} <= {TOKEN_BUDGET})")
            return {}
    except Exception:
        return {}

    # Perform summarization
    to_summarize = unsummarized[:-RECENT_MESSAGES_KEEP]
    if not to_summarize:
        log_summarization_skip("no messages to summarize after keeping recent")
        return {}

    log_summarization_trigger(n, len(unsummarized), token_count, TOKEN_BUDGET)
    transcript = _build_transcript(to_summarize)[:8000]
    existing_summary = state.get("summary") or ""
    
    try:
        prompt_text = SUMMARY_PROMPT_TEMPLATE.format(
            conversation=transcript,
            previous_summary=existing_summary
        )
    except KeyError:
        prompt_text = SUMMARY_PROMPT_TEMPLATE.format(conversation=transcript)

    try:
        summary_msg = llm.invoke([
            SystemMessage(content="You summarize chats."),
            HumanMessage(content=prompt_text)
        ])
        new_summary = summary_msg.content.strip()
        
        combined_summary = (existing_summary + "\n" + new_summary).strip() if existing_summary else new_summary
        new_upto = n - len(unsummarized[-RECENT_MESSAGES_KEEP:])
        
        log_summary_action("updated" if existing_summary else "created", combined_summary, len(to_summarize))
        
        return {
            "summary": combined_summary,
            "summary_upto": new_upto
        }
    except Exception as e:
        logger.error(f"Summarization failed: {e}", exc_info=True)
        console.log(f"[yellow]⚠️ Summarization failed: {e}[/yellow]")
        return {}


# =============================================================================
# 🤖 Agent Graph Factory
# =============================================================================

def get_chat_agent(memory: SqliteSaver) -> Pregel:
    """Return a compiled chat agent graph with SQLite-backed memory."""
    log_agent_initialization("start")

    try:
        llm = get_neuron_llm()
        log_agent_initialization("llm_ready")

        def chatbot(state: AgentState) -> Dict[str, Any]:
            """Main chatbot node logic."""
            updates: Dict[str, Any] = {}
            
            # 1. Summarization (use base LLM to avoid tool calls)
            summary_updates = _summarize_logic(llm, state)
            if summary_updates:
                updates.update(summary_updates)
                # Apply updates locally for current turn context
                state = {**state, **summary_updates} # type: ignore

            # 2. Prepare Context
            memory_user_id = _resolve_memory_user_id(state)
            log_memory_user_resolution(state.get("user_id", "unknown"), memory_user_id)
            memory_service = get_memory_service()
            
            # Get last user message text for memory search
            messages = state.get("messages", []) or []
            last_human_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
            last_user_text = _extract_text_content(last_human_msg) if last_human_msg else ""

            # Search Mem0
            memory_context = ""
            if last_user_text:
                try:
                    log_memory_search(memory_user_id, last_user_text, MEMORY_SEARCH_LIMIT)
                    memories = memory_service.search_memories(
                        user_id=memory_user_id,
                        query=last_user_text,
                        limit=MEMORY_SEARCH_LIMIT
                    )
                    if memories:
                        memory_context = "Relevant memories:\n" + "\n".join(f"- {m['content']}" for m in memories)
                        log_memory_results(memory_user_id, len(memories), memories)
                except Exception as e:
                    log_memory_search_error(memory_user_id, e)

            # 3. Build Messages
            system_msgs = _build_system_messages(state, memory_context)
            
            # Filter messages based on summary_upto
            summary_upto = state.get("summary_upto", 0) or 0
            active_messages = messages[summary_upto:]
            
            # Convert media messages
            convo_messages = [_convert_to_langchain_message(m) for m in active_messages]
            
            full_prompt = system_msgs + convo_messages
            
            # Logging
            log_context_building(
                has_profile=bool(state.get("user_profile")),
                has_summary=bool(state.get("summary")),
                has_memory=bool(memory_context),
                active_messages=len(active_messages)
            )
            log_system_instructions([m.content for m in system_msgs])
            log_invocation_payload(full_prompt)

            # 4. Invoke LLM
            llm_start = time.time()
            try:
                response = llm.invoke(full_prompt)
                log_llm_response(response, time.time() - llm_start)
            except Exception as e:
                log_llm_error(e, time.time() - llm_start)
                response = AIMessage(content="متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید.")

            # 5. Store Memory (Background)
            if last_user_text and isinstance(response, AIMessage):
                ai_text = response.content
                log_memory_storage(memory_user_id, "initiated")
                def _store():
                    try:
                        memory_service.add_memory(
                            user_id=memory_user_id,
                            messages=[
                                {"role": "user", "content": last_user_text},
                                {"role": "assistant", "content": ai_text}
                            ],
                            metadata={"timestamp": time.time(), "source": "smart_chat"}
                        )
                        log_memory_storage(memory_user_id, "success")
                    except Exception as e:
                        log_memory_storage(memory_user_id, "error")
                        logger.error(f"Memory storage failed for {memory_user_id}: {e}", exc_info=True)
                threading.Thread(target=_store, daemon=True).start()

            # Return updates (new message + any summary changes)
            updates["messages"] = [response]
            return updates

        log_agent_initialization("graph_built")
        graph = StateGraph(AgentState)
        graph.add_node("chatbot", chatbot)
        graph.add_edge(START, "chatbot")

        log_agent_initialization("compiled")
        compiled_agent: Pregel = graph.compile(checkpointer=memory)

        log_agent_initialization("success")
        return compiled_agent

    except Exception as e:
        log_agent_initialization("error", str(e))
        logger.error(f"Agent initialization error: {e}", exc_info=True)
        raise


# =============================================================================
# 💾 Memory / Checkpointer Factory
# =============================================================================

def get_memory() -> SqliteSaver:
    """Return a SqliteSaver instance for use as LangGraph checkpointer."""
    log_memory_initialization("start")

    try:
        db_path = "database/psychology_bot.db"
        log_memory_initialization("db_path", db_path=db_path)

        # Test database connection first
        conn = sqlite3.connect(db_path, check_same_thread=False)
        log_memory_initialization("connected")

        # Create SqliteSaver instance
        memory_saver = SqliteSaver(conn=conn)
        log_memory_initialization("saver_created")
        log_memory_initialization("ready")

        return memory_saver

    except Exception as e:
        log_memory_initialization("error", error=str(e))
        logger.error(f"Memory initialization error: {e}", exc_info=True)
        raise


# =============================================================================
# 💬 Chat API (entrypoint for a single turn)
# =============================================================================

def chat(agent: Pregel, user_id: str, message: str, thread_id: Optional[str] = None):
    """Interact with the chat agent with comprehensive logging.

    Returns either:
    - history (if message is empty), or
    - a dict: {"raw": str, "refined": str} for UI consumption.
    """
    start_time = time.time()

    # Session info table
    console.print(create_session_table(user_id, message))

    config = {"configurable": {"thread_id": thread_id or user_id}}
    log_config(config)

    # Empty message → return history
    if not message.strip():
        log_empty_message()
        try:
            state = agent.get_state(config)
            history = state.values.get("messages", [])
            log_history_retrieval(len(history))
            return history
        except Exception as e:
            console.log(f"[red]❌ Error getting history: {e}[/red]")
            logger.error(f"History retrieval error: {e}", exc_info=True)
            return []

    log_stream_start()

    # -------------------------------------------------------------------------
    # Build user profile (from DB) for personalization
    # -------------------------------------------------------------------------
    user_profile = None
    try:
        try:
            uid: Any = int(user_id)
        except Exception:
            uid = user_id
        user_profile = get_user(uid)
        log_user_profile(user_id, user_profile)
    except Exception as e:
        console.log(f"[yellow]⚠️ Could not load user profile: {e}[/yellow]")
        logger.warning(f"User profile load error for {user_id}: {e}")

    # We only send the new human message + user_profile into the graph.
    # System prompts (NEURON, profile text, summary) are handled inside the node.
    input_data: AgentState = {
        "messages": [HumanMessage(content=message)],
        "user_profile": user_profile,
        "user_id": user_id,
    }
    
    log_message_stats(input_data["messages"], "Input prepared")

    try:
        # ---------------------------------------------------------------------
        # Stream processing with progress indicator
        # ---------------------------------------------------------------------
        with build_progress() as progress:
            task = progress.add_task("Processing message...", total=None)

            events = agent.stream(input_data, config, stream_mode="values")
            progress.update(task, description="Streaming events...")

            event_count = 0
            for event in events:
                event_count += 1
                progress.update(
                    task, description=f"Processing event {event_count}..."
                )

                log_stream_event(event_count, event)

                if isinstance(event, dict) and "messages" in event:
                    messages = event["messages"]

                    if messages:
                        # The last message should be the AI's response
                        ai_message = messages[-1]

                        if isinstance(ai_message, AIMessage):
                            content = ai_message.content
                            duration = time.time() - start_time

                            # Telegram-optimized/refined version for UI display
                            try:
                                refined = optimize_for_telegram(content or "")
                                log_response_refinement(len(content or ""), len(refined))
                            except Exception as e:
                                log_refinement_error(e)
                                refined = content or ""

                            # Success table
                            log_stream_completion(event_count, duration)
                            console.print(
                                create_success_table(
                                    duration, event_count, content
                                )
                            )

                            # Return raw + refined forms (handlers use refined for UI)
                            return {"raw": content, "refined": refined}
                        else:
                            console.log(
                                f"[yellow]⚠️ Last message is not AIMessage: {type(ai_message)}[/yellow]"
                            )
                    else:
                        console.log(
                            "[yellow]⚠️ Event messages list is empty[/yellow]"
                        )
                else:
                    console.log(
                        "[yellow]⚠️ Event doesn't contain messages key or is not dict[/yellow]"
                    )

            progress.update(task, description="Completed", completed=True)

        console.log(
            f"[yellow]⚠️ Stream completed but no AI response found. Processed {event_count} events[/yellow]"
        )
        logger.warning(f"No AI response in stream: events={event_count}, user={user_id}")
        return "عذرخواهی، پاسخی دریافت نشد. لطفاً دوباره تلاش کنید."

    except Exception as e:
        duration = time.time() - start_time

        # Error table
        console.print(create_error_table(e, duration, user_id))

        logger.error(f"Chat error for user {user_id}: {e}", exc_info=True)
        return f"متأسفانه خطایی رخ داد: {str(e)}"


# =============================================================================
# 🏁 CLI Entrypoint (Example Usage)
# =============================================================================
if __name__ == "__main__":
    memory = get_memory()
    agent = get_chat_agent(memory)
    user_id = "example_user"

    print("Chatbot started. Type 'exit' to end.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        response = chat(agent, user_id, user_input)
        print(f"AI: {response}")

    # Demonstrate memory by printing conversation history
    history_state = agent.get_state({"configurable": {"thread_id": user_id}})
    print("\n--- Conversation History ---")
    for msg in history_state.values.get("messages", []):
        role = getattr(msg, "type", msg.__class__.__name__)
        print(f"{role.capitalize()}: {getattr(msg, 'content', '')}")
