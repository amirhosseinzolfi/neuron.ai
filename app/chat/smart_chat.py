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
import sqlite3
import time
from functools import lru_cache
from typing import Annotated, Any, Dict, List, Optional, TypedDict

# =============================================================================
# 🧠 LangChain / LangGraph Imports
# =============================================================================
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.messages.utils import count_tokens_approximately
import base64
from langgraph.graph import StateGraph, END
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
    log_history_state,
    log_invocation_payload,
    log_summary_action,
    log_system_instructions,
    logger,
)

# =============================================================================
# 🔧 Project Utilities & Prompts
# =============================================================================
from ai_utils import get_neuron_llm
from telegram_text_optimizer import optimize_for_telegram
from db import get_user  # DB helper for user info (system prompt context)
from database.prompts import NEURON, HISTORY_SUMMARIZATION_PROMPT  # system instruction & history summarization prompt
from app.services.memory_api_client import MemoryApiClient
# =============================================================================
# 🌐 Memory API configuration
# =============================================================================
MEMORY_API_BASE_URL = (
    os.getenv("MEMORY_API_BASE_URL")
    or os.getenv("MEMORY_API_BASE")
    or os.getenv("MEMORY_API_URL")
    or "http://localhost:15800"
)
MEMORY_API_TIMEOUT = float(os.getenv("MEMORY_API_TIMEOUT", "25.0"))
MEMORY_SEARCH_LIMIT = int(os.getenv("MEMORY_API_SEARCH_LIMIT", "5"))


@lru_cache(maxsize=1)
def get_memory_api_client() -> Optional[MemoryApiClient]:
    try:
        return MemoryApiClient(base_url=MEMORY_API_BASE_URL, timeout=MEMORY_API_TIMEOUT)
    except Exception as exc:
        console.log(f"[yellow]⚠️ Memory API client initialization failed: {exc}[/yellow]")
        return None

# =============================================================================
# ⚙️ Conversation History / Summarization Settings
# =============================================================================
# Approximate maximum token budget we want to send to the LLM for conversation history.
# (This is separate from the model's hard context limit; keep it conservative.)
TOKEN_BUDGET = 2800

# Always keep this many most recent messages verbatim in the state.
RECENT_MESSAGES_KEEP = 8

# Below this number of messages, we don't bother summarizing.
MIN_MESSAGES_TO_SUMMARIZE = 12

# Use centralized history summarization prompt.
SUMMARY_PROMPT_TEMPLATE = HISTORY_SUMMARIZATION_PROMPT


# =============================================================================
# 🧱 State Definition
# =============================================================================
class AgentState(TypedDict, total=False):
    """LangGraph state for the smart chat agent.

    - messages: full conversation turns (Human/AI); *no* system prompts stored here.
    - summary: running summary of older parts of the conversation.
    - summary_upto: index in `messages` up to which `summary` already covers.
    - user_profile: optional dict with user-specific info used for personalization.
    - user_id: platform-level identifier (Telegram chat_id) used to scope memories per user.
    """

    messages: Annotated[List[AnyMessage], add_messages]
    summary: Optional[str]
    summary_upto: Optional[int]
    user_profile: Optional[Dict[str, Any]]
    user_id: Optional[str]


# =============================================================================
# 🧩 Helper Functions (Media, Transcript, Summarization)
# =============================================================================

def _encode_media_to_base64(file_path: str) -> str:
    """Encode media file to base64 string (utility kept for potential future use)."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _convert_to_langchain_message(msg: AnyMessage) -> AnyMessage:
    """Convert message with media metadata (e.g., from Telegram) to proper LangChain format.

    If a HumanMessage contains additional_kwargs["media"], we turn it into a
    multi-modal content block suitable for vision/audio models.
    """
    if isinstance(msg, HumanMessage) and hasattr(msg, "additional_kwargs"):
        media = msg.additional_kwargs.get("media")
        if media:
            content: List[Dict[str, Any]] = []

            # Add text part if present
            if isinstance(msg.content, str) and msg.content:
                content.append({"type": "text", "text": msg.content})

            # Add media part
            if media.get("type") == "image":
                content.append(
                    {
                        "type": "image_url",
                        "image_url": f"data:{media['mime_type']};base64,{media['data']}",
                    }
                )
            elif media.get("type") == "audio":
                content.append(
                    {
                        "type": "media",
                        "mime_type": media["mime_type"],
                        "data": media["data"],
                    }
                )

            return HumanMessage(content=content)

    # Fallback: return as-is
    return msg


def _build_transcript(messages: List[AnyMessage]) -> str:
    """Convert messages into a plain-text transcript `role: content` for summarization."""
    lines: List[str] = []
    for m in messages:
        role = getattr(m, "type", m.__class__.__name__)
        content = getattr(m, "content", "")
        if isinstance(content, str) and content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _extract_text_content(message: AnyMessage) -> str:
    """Return a plain-text view of a LangChain message (handles multimodal lists)."""
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


def _shorten(text: str, limit: int = 160) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _log_memory_hits(
    user_id: str,
    query: str,
    memories: List[Dict[str, Any]],
    formatted_context: str,
) -> None:
    if not memories:
        console.log(f"[dim]🧠 No Mem0 matches for user={user_id} query='{_shorten(query, 60)}'[/dim]")
        return

    console.log(
        f"[blue]🧠 Mem0 search for user={user_id} query='{_shorten(query, 60)}' returned {len(memories)} hit(s)[/blue]"
    )

    table = Table(title="Mem0 Memory Matches", show_lines=True)
    table.add_column("#", justify="right", style="cyan", width=3)
    table.add_column("Score", justify="right", style="magenta", width=7)
    table.add_column("Source", style="green", no_wrap=True)
    table.add_column("Content", style="white")
    table.add_column("Metadata Keys", style="yellow")

    for idx, mem in enumerate(memories, start=1):
        score_val = mem.get("score")
        score = f"{score_val:.3f}" if isinstance(score_val, (int, float)) else "-"
        metadata = mem.get("metadata") or {}
        source = mem.get("source") or metadata.get("source") or "-"
        content = mem.get("content") or mem.get("memory") or ""
        content_preview = _shorten(str(content).strip(), 80)
        metadata_keys = ", ".join(sorted(metadata.keys())) if metadata else "-"

        table.add_row(str(idx), score, source, content_preview, metadata_keys)

    if formatted_context:
        console.print(Panel.fit(formatted_context, title="Formatted Context", border_style="blue"))

    console.print(table)

    try:
        raw_json = json.dumps(memories, ensure_ascii=False, indent=2)
        console.print(Panel(raw_json, title="Raw Mem0 Documents", border_style="dim"))
    except Exception as exc:
        console.log(f"[yellow]⚠️ Failed to serialize memories for logging: {exc}[/yellow]")


def _ai_decides_memory_worthy(llm, user_text: str, ai_text: str) -> bool:
    """Let AI decide if conversation is worth storing in long-term memory."""
    if not user_text or len(user_text.strip()) < 5:
        return False
    
    memory_decision_prompt = f"""Analyze this conversation and decide if it contains important information worth storing in long-term memory.

User: {user_text}
Assistant: {ai_text}

Should this conversation be stored in long-term memory? Consider:
- Personal information (name, age, job, interests, goals)
- Important preferences or characteristics
- Meaningful psychological insights
- Significant life events or decisions
- Skip: greetings, random text, simple questions, errors

Respond with only: YES or NO"""
    
    try:
        decision = llm.invoke([
            SystemMessage(content="You are a memory curator. Decide what conversations are worth remembering."),
            HumanMessage(content=memory_decision_prompt)
        ])
        
        response = decision.content.strip().upper()
        return "YES" in response
        
    except Exception as e:
        console.log(f"[yellow]⚠️ AI memory decision failed: {e}[/yellow]")
        return False


def _resolve_memory_user_id(state: AgentState) -> str:
    """Return the canonical user ID (Telegram chat_id) used for Mem0 partitioning."""
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
            # state_user_id is non-numeric (e.g., custom thread id); fall back to string form
            pass

    return str(state_user_id or "anonymous")


def build_user_profile_system_text(user_profile: Optional[Dict[str, Any]]) -> Optional[str]:
    """Build a system message containing the user's full profile as a JSON string."""
    if not user_profile:
        return None

    try:
        # Serialize the user_profile dictionary to a JSON string for the AI.
        # Using ensure_ascii=False to correctly handle non-ASCII characters (like Persian).
        profile_json = json.dumps(user_profile, indent=2, ensure_ascii=False)
        return (
            "This is the user's full profile data from the database in JSON format. "
            "Use this for personalization and context:\n"
            f"```json\n{profile_json}\n```"
        )
    except (TypeError, ValueError) as e:
        console.log(f"[yellow]⚠️ Could not serialize user profile to JSON: {e}[/yellow]")
        # Fallback to a simple text representation if JSON fails
        return f"User Profile (serialization failed): {str(user_profile)}"


def maybe_summarize_history(llm, state: AgentState) -> AgentState:
    """Summarize *new* parts of history when token budget is exceeded.

    Incremental strategy:
    - We keep the full `messages` list in state for archival purposes.
    - `summary` + `summary_upto` tell us which prefix of `messages` is already summarized.
    - On each call we only consider the *unsummarized* suffix `messages[summary_upto:]`.
    - If that suffix is small / cheap → do nothing.
    - If it exceeds TOKEN_BUDGET → summarize all but a small recent tail and
      update `summary` and `summary_upto`.

    This avoids re-summarizing the whole conversation on every turn and keeps
    the LLM prompt small while preserving a full archive in the checkpointer.
    """

    messages = state.get("messages", []) or []
    n = len(messages)
    if n <= MIN_MESSAGES_TO_SUMMARIZE:
        return state

    # Index up to which history has already been summarized
    last_upto = state.get("summary_upto") or 0
    if last_upto < 0 or last_upto > n:
        # Safety: clamp to valid range
        last_upto = 0

    unsummarized = messages[last_upto:]
    if len(unsummarized) <= MIN_MESSAGES_TO_SUMMARIZE:
        return state

    try:
        unsummarized_tokens = count_tokens_approximately(unsummarized)
    except Exception as e:
        console.log(f"[yellow]⚠️ Token counting failed, skipping summarization: {e}[/yellow]")
        return state

    if unsummarized_tokens <= TOKEN_BUDGET:
        return state

    # We need to summarize part of the unsummarized suffix.
    if len(unsummarized) <= RECENT_MESSAGES_KEEP:
        # Not enough to split; wait for more turns.
        return state

    # Keep a small recent tail of unsummarized messages
    to_summarize = unsummarized[:-RECENT_MESSAGES_KEEP]
    remaining_tail = unsummarized[-RECENT_MESSAGES_KEEP:]

    console.log("[magenta]🧪 Summarizing new portion of messages to control context size...[/magenta]")

    transcript = _build_transcript(to_summarize)[:8000]
    existing_summary = state.get("summary") or ""

    # Allow the prompt template to optionally use previous_summary if defined
    try:
        prompt_text = SUMMARY_PROMPT_TEMPLATE.format(
            conversation=transcript,
            previous_summary=existing_summary,
        )
    except KeyError:
        # Backwards compatibility if template expects only {conversation}
        prompt_text = SUMMARY_PROMPT_TEMPLATE.format(conversation=transcript)

    try:
        summary_msg = llm.invoke(
            [
                SystemMessage(content="You summarize chats."),
                HumanMessage(content=prompt_text),
            ]
        )
        new_summary = summary_msg.content.strip()
    except Exception as e:
        console.log(f"[yellow]⚠️ Summarization failed: {e}[/yellow]")
        return state

    # Combine with existing summary if any
    if existing_summary:
        combined_summary = existing_summary + new_summary
        action = "updated"
    else:
        combined_summary = new_summary
        action = "created"

    state["summary"] = combined_summary
    # Update summary_upto to reflect that everything up to this index is summarized
    new_upto = n - len(remaining_tail)
    state["summary_upto"] = new_upto

    log_summary_action(action, combined_summary, len(to_summarize))
    console.log(
        f"[green]🧹 History summarized incrementally. "
        f"New summarized messages: {len(to_summarize)}, "
        f"summary length={len(combined_summary)} chars[/green]"
    )

    # For visibility in logs (we still log the whole messages list but mark summary)
    log_history_state(
        "post-summarize",
        state["messages"],
        summary_version=1,
        summary_text=combined_summary,
    )

    return state

    try:
        total_tokens = count_tokens_approximately(messages)
    except Exception as e:
        console.log(f"[yellow]⚠️ Token counting failed, skipping summarization: {e}[/yellow]")
        return state

    if total_tokens <= TOKEN_BUDGET:
        return state

    # We need to summarize older messages.
    if len(messages) <= RECENT_MESSAGES_KEEP:
        # Not enough messages to split; skip.
        return state

    older_portion = messages[:-RECENT_MESSAGES_KEEP]
    recent_portion = messages[-RECENT_MESSAGES_KEEP:]

    console.log("[magenta]🧪 Summarizing older messages to control context size...[/magenta]")

    transcript = _build_transcript(older_portion)[:8000]
    existing_summary = state.get("summary") or ""

    # Allow the prompt template to optionally use previous_summary if defined
    try:
        prompt_text = SUMMARY_PROMPT_TEMPLATE.format(
            conversation=transcript,
            previous_summary=existing_summary,
        )
    except KeyError:
        # Backwards compatibility if template expects only {conversation}
        prompt_text = SUMMARY_PROMPT_TEMPLATE.format(conversation=transcript)

    try:
        summary_msg = llm.invoke(
            [
                SystemMessage(content="You summarize chats."),
                HumanMessage(content=prompt_text),
            ]
        )
        new_summary = summary_msg.content.strip()
    except Exception as e:
        console.log(f"[yellow]⚠️ Summarization failed: {e}[/yellow]")
        return state

    # Combine with existing summary if any
    if existing_summary:
        combined_summary = existing_summary + "\n\n[NEW]\n" + new_summary
        action = "updated"
    else:
        combined_summary = new_summary
        action = "created"

    state["summary"] = combined_summary
    state["messages"] = recent_portion

    log_summary_action(action, combined_summary, len(older_portion))
    console.log(
        f"[green]🧹 History summarized. Kept {len(recent_portion)} recent messages; "
        f"summary length={len(combined_summary)} chars[/green]"
    )

    # For visibility in logs
    log_history_state(
        "post-summarize",
        state["messages"],
        summary_version=1,
        summary_text=combined_summary,
    )

    return state


# =============================================================================
# 🤖 Agent Graph Factory
# =============================================================================

def get_chat_agent(memory: SqliteSaver) -> Pregel:
    """Return a compiled chat agent graph with SQLite-backed memory."""
    console.log("[bold blue]🤖 Initializing Smart Chat Agent...[/bold blue]")

    try:
        llm = get_neuron_llm()
        console.log("[green]✅ LLM instance retrieved successfully[/green]")

        def chatbot(state: AgentState) -> AgentState:
            """Main chatbot node logic with history summarization and rich logging."""
            console.log("[cyan]🧠 Chatbot node processing...[/cyan]")

            messages = state.get("messages", []) or []
            console.log(f"[dim]📝 Processing {len(messages)} messages in state[/dim]")

            if messages:
                last_msg = messages[-1]
                console.log(f"[dim]📨 Last message type: {type(last_msg).__name__}[/dim]")
                if hasattr(last_msg, "content"):
                    if isinstance(last_msg.content, str):
                        preview = last_msg.content[:100] + (
                            "..." if len(last_msg.content) > 100 else ""
                        )
                    else:
                        preview = "[multimodal content]"
                    console.log(f"[dim]📝 Content preview: {preview}[/dim]")

            # 1) Summarize history if needed (token-budget based)
            try:
                state = maybe_summarize_history(llm, state)
                log_history_state(
                    "invocation",
                    state.get("messages", []),
                    summary_version=(1 if state.get("summary") else 0),
                    summary_text=state.get("summary"),
                )
            except Exception as e:
                console.log(f"[yellow]⚠️ History summarization step failed: {e}[/yellow]")

            try:
                start_time = time.time()

                # 2) Build system messages (NEURON + user profile + summary)
                user_profile = state.get("user_profile")

                system_messages: List[SystemMessage] = []
                # Core system instruction
                system_messages.append(SystemMessage(content=NEURON))

                # User profile personalization
                system_text = build_user_profile_system_text(user_profile)
                if system_text:
                    system_messages.append(SystemMessage(content=system_text))

                # Conversation summary if present
                if state.get("summary"):
                    system_messages.append(
                        SystemMessage(
                            content=f"[Conversation Summary]\n{state['summary']}"
                        )
                    )

                # 3) Initialize Memory API Client
                memory_user_id = _resolve_memory_user_id(state)
                console.log(f"[dim]🧾 Memory user ID resolved: {memory_user_id}[/dim]")

                memory_client = get_memory_api_client()
                if memory_client:
                    console.log(f"[blue]🧠 Memory API client ready ({MEMORY_API_BASE_URL})[/blue]")
                else:
                    console.log("[yellow]⚠️ Memory API client unavailable; skipping remote memory context[/yellow]")

                # 4) Conversation messages (human/ai) + multimodal conversion
                all_messages = state.get("messages", []) or []
                summary_upto = state.get("summary_upto") or 0
                if summary_upto < 0 or summary_upto > len(all_messages):
                    summary_upto = 0

                tail_messages = all_messages[summary_upto:]
                last_user_text: Optional[str] = None
                for msg in reversed(tail_messages):
                    if isinstance(msg, HumanMessage):
                        extracted = _extract_text_content(msg)
                        if extracted:
                            last_user_text = extracted
                            break

                # 5) Add Mem0 memory context if available via API
                if memory_client and last_user_text:
                    try:
                        memory_context_str, memory_hits = memory_client.get_context_with_details(
                            user_id=memory_user_id,
                            query=last_user_text,
                            limit=MEMORY_SEARCH_LIMIT,
                        )
                        _log_memory_hits(memory_user_id, last_user_text, memory_hits, memory_context_str)
                        if memory_context_str:
                            system_messages.append(SystemMessage(content=memory_context_str))
                            console.log("[blue]🧠 Added Mem0 context via API[/blue]")
                    except Exception as memory_exc:
                        console.log(f"[yellow]⚠️ Mem0 API retrieval failed: {memory_exc}[/yellow]")

                convo_messages = [
                    _convert_to_langchain_message(m) for m in tail_messages
                ]

                invocation_messages: List[AnyMessage] = system_messages + convo_messages

                # Logging
                log_system_instructions([m.content for m in system_messages])
                log_invocation_payload(invocation_messages)

                console.log("[yellow]🚀 Invoking LLM...[/yellow]")
                response = llm.invoke(invocation_messages)

                duration = time.time() - start_time
                console.log(f"[green]✅ LLM response received in {duration:.2f}s[/green]")

                if hasattr(response, "content"):
                    if isinstance(response.content, str):
                        response_preview = response.content[:100] + (
                            "..." if len(response.content) > 100 else ""
                        )
                    else:
                        response_preview = "[multimodal content]"
                    console.log(f"[green]💬 Response preview: {response_preview}[/green]")

                # 6) Append response to messages in state
                new_messages = (state.get("messages") or []) + [response]
                state["messages"] = new_messages

                # 7) Store conversation in Mem0 memory via API (AI decides if worth storing)
                if memory_client and last_user_text:
                    ai_response_text = _extract_text_content(response)
                    
                    console.log("[cyan]🤔 Evaluating if conversation is worth storing...[/cyan]")
                    console.log(f"[dim]User: {_shorten(last_user_text, 80)}[/dim]")
                    console.log(f"[dim]AI: {_shorten(ai_response_text, 80)}[/dim]")
                    
                    is_worthy = _ai_decides_memory_worthy(llm, last_user_text, ai_response_text)
                    
                    if is_worthy:
                        console.log("[green]✅ AI Decision: WORTH STORING[/green]")
                        try:
                            console.log("[cyan]🔍 Sending to Mem0 API for extraction...[/cyan]")
                            result = memory_client.store_turn(
                                user_id=memory_user_id,
                                user_text=last_user_text,
                                assistant_text=ai_response_text,
                                metadata={
                                    "timestamp": time.time(),
                                    "source": "smart_chat",
                                    "chat_id": memory_user_id,
                                },
                            )
                            
                            if result:
                                console.log(f"[green]🧠 ✅ Memory stored successfully via API[/green]")
                            else:
                                console.log(f"[yellow]⚠️ Mem0 API storage returned False[/yellow]")
                                
                        except Exception as memory_exc:
                            console.log(f"[red]❌ Mem0 API error: {memory_exc}[/red]")
                    else:
                        console.log("[dim]❌ AI Decision: NOT WORTH STORING (skipping)[/dim]")

                return state

            except Exception as e:
                console.log(f"[bold red]❌ Error in chatbot node: {e}[/bold red]")
                logger.error(f"Chatbot node error: {e}", exc_info=True)
                fallback_msg = AIMessage(
                    content="متأسفانه خطایی رخ داد. لطفاً دوباره تلاش کنید."
                )
                # Preserve summary and user_profile if present
                return {
                    "messages": [fallback_msg],
                    "summary": state.get("summary"),
                    "user_profile": state.get("user_profile"),
                    "user_id": state.get("user_id"),
                }

        console.log("[blue]🔧 Building state graph...[/blue]")
        graph = StateGraph(AgentState)
        graph.add_node("chatbot", chatbot)
        graph.set_entry_point("chatbot")
        graph.add_edge("chatbot", END)

        console.log("[blue]🔗 Compiling graph with checkpointer...[/blue]")
        compiled_agent: Pregel = graph.compile(checkpointer=memory)

        console.log("[bold green]✅ Smart Chat Agent initialized successfully![/bold green]")
        return compiled_agent

    except Exception as e:
        console.log(f"[bold red]❌ Failed to initialize Smart Chat Agent: {e}[/bold red]")
        logger.error(f"Agent initialization error: {e}", exc_info=True)
        raise


# =============================================================================
# 💾 Memory / Checkpointer Factory
# =============================================================================

def get_memory() -> SqliteSaver:
    """Return a SqliteSaver instance for use as LangGraph checkpointer."""
    console.log("[bold blue]💾 Initializing memory/database connection...[/bold blue]")

    try:
        db_path = "database/psychology_bot.db"
        console.log(f"[dim]📂 Database path: {db_path}[/dim]")

        # Test database connection first
        conn = sqlite3.connect(db_path, check_same_thread=False)
        console.log("[green]✅ Database connection successful[/green]")

        # Create SqliteSaver instance
        memory_saver = SqliteSaver(conn=conn)
        console.log("[green]✅ SqliteSaver instance created[/green]")

        # Simple sanity log (no-op read/write here; real tables are created lazily)
        try:
            test_config = {"configurable": {"thread_id": "test_connection"}}
            console.log("[dim]🔍 Testing memory saver functionality...[/dim]")
            # We don't actually need to call anything; this is mainly for logging clarity.
            console.log("[green]✅ Memory saver ready[/green]")
        except Exception as e:
            console.log(f"[yellow]⚠️ Memory saver test warning: {e}[/yellow]")
            logger.warning(f"Memory saver test issue: {e}")

        return memory_saver

    except Exception as e:
        console.log(f"[bold red]❌ Failed to initialize memory: {e}[/bold red]")
        logger.error(f"Memory initialization error: {e}", exc_info=True)
        raise


# =============================================================================
# 💬 Chat API (entrypoint for a single turn)
# =============================================================================

def chat(agent: Pregel, user_id: str, message: str):
    """Interact with the chat agent with comprehensive logging.

    Returns either:
    - history (if message is empty), or
    - a dict: {"raw": str, "refined": str} for UI consumption.
    """
    start_time = time.time()

    # Session info table
    console.print(create_session_table(user_id, message))

    config = {"configurable": {"thread_id": user_id}}
    console.log(f"[blue]🔧 Config: {config}[/blue]")

    # Empty message → return history
    if not message.strip():
        console.log("[yellow]⚠️ Empty message received, returning history[/yellow]")
        try:
            state = agent.get_state(config)
            history = state.values.get("messages", [])
            console.log(
                f"[green]📚 Retrieved {len(history)} messages from history[/green]"
            )
            return history
        except Exception as e:
            console.log(f"[red]❌ Error getting history: {e}[/red]")
            return []

    console.log("[yellow]🚀 Starting chat stream...[/yellow]")

    # -------------------------------------------------------------------------
    # Build user profile (from DB) for personalization
    # -------------------------------------------------------------------------
    console.log("[dim]📥 Preparing input payload...[/dim]")
    user_profile = None
    try:
        try:
            uid: Any = int(user_id)
        except Exception:
            uid = user_id
        user_profile = get_user(uid)
        console.log(f"[dim]🔍 Loaded user profile: {bool(user_profile)}[/dim]")
    except Exception as e:
        console.log(f"[yellow]⚠️ Could not load user profile: {e}[/yellow]")

    # We only send the new human message + user_profile into the graph.
    # System prompts (NEURON, profile text, summary) are handled inside the node.
    input_data: AgentState = {
        "messages": [HumanMessage(content=message)],
        "user_profile": user_profile,
        "user_id": user_id,
    }

    console.log(f"[dim]📥 Input data structure: {type(input_data)}[/dim]")
    console.log(
        f"[dim]📥 Input message type: {type(input_data['messages'][0])}[/dim]"
    )

    try:
        # ---------------------------------------------------------------------
        # Stream processing with progress indicator
        # ---------------------------------------------------------------------
        with build_progress() as progress:
            task = progress.add_task("Processing message...", total=None)

            console.log("[blue]🌊 Calling agent.stream()...[/blue]")
            events = agent.stream(input_data, config, stream_mode="values")
            progress.update(task, description="Streaming events...")
            console.log("[green]✅ Stream created successfully[/green]")

            event_count = 0
            for event in events:
                event_count += 1
                progress.update(
                    task, description=f"Processing event {event_count}..."
                )

                console.log(f"[cyan]📨 Event {event_count} received[/cyan]")
                console.log(f"[dim]📊 Event type: {type(event)}[/dim]")
                console.log(
                    f"[dim]📊 Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}[/dim]"
                )

                if isinstance(event, dict) and "messages" in event:
                    messages = event["messages"]
                    console.log(
                        f"[cyan]📝 Event contains {len(messages)} messages[/cyan]"
                    )

                    if messages:
                        # The last message should be the AI's response
                        ai_message = messages[-1]
                        console.log(
                            f"[green]🤖 AI message type: {type(ai_message)}[/green]"
                        )

                        if isinstance(ai_message, AIMessage):
                            content = ai_message.content
                            duration = time.time() - start_time

                            # Telegram-optimized/refined version for UI display
                            try:
                                refined = optimize_for_telegram(content or "")
                                console.log(
                                    f"[dim]🔧 Refined response length: {len(refined)}[/dim]"
                                )
                            except Exception as e:
                                console.log(
                                    f"[yellow]⚠️ Refinement failed: {e}[/yellow]"
                                )
                                refined = content or ""

                            # Success table
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
