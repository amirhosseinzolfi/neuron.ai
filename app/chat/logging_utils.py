"""
Smart Chat Logging Utilities
Centralized logging system for debugging and monitoring chat operations.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Sequence

from langchain_core.messages import AnyMessage, AIMessage, HumanMessage, SystemMessage
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.tree import Tree

# =============================================================================
# Console & Logger Setup
# =============================================================================
console = Console()
logger = logging.getLogger("smart_chat")
logger.setLevel(logging.INFO)

# File handler for persistent logs
if not logger.handlers:
    handler = logging.FileHandler("logs/smart_chat.log")
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)


# =============================================================================
# Text Utilities
# =============================================================================
def _preview_text(text: str, limit: int = 50) -> str:
    """Create shortened preview of text."""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def _sum_content_length(messages: Sequence[AnyMessage]) -> int:
    """Calculate total character count in messages."""
    return sum(len(getattr(m, "content", "") or "") for m in messages)


def _format_message_type(msg: AnyMessage) -> str:
    """Get formatted message type name."""
    return type(msg).__name__


# =============================================================================
# Session & Initialization Logging
# =============================================================================
def log_agent_initialization(status: str, details: Optional[str] = None) -> None:
    """Log agent initialization steps."""
    if status == "start":
        console.print(Panel.fit(
            "[bold blue]🤖 Initializing Smart Chat Agent[/bold blue]",
            border_style="blue"
        ))
        logger.info("Agent initialization started")
    elif status == "llm_ready":
        console.log("[green]✅ LLM instance retrieved[/green]")
        logger.info("LLM instance created successfully")
    elif status == "graph_built":
        console.log("[blue]🔧 State graph built[/blue]")
        logger.info("LangGraph state graph constructed")
    elif status == "compiled":
        console.log("[blue]🔗 Graph compiled with checkpointer[/blue]")
        logger.info("Graph compiled with memory checkpointer")
    elif status == "success":
        console.print(Panel.fit(
            "[bold green]✅ Smart Chat Agent Ready[/bold green]",
            border_style="green"
        ))
        logger.info("Agent initialization completed successfully")
    elif status == "error":
        console.log(f"[bold red]❌ Initialization failed: {details}[/bold red]")
        logger.error(f"Agent initialization error: {details}")


def log_memory_initialization(status: str, db_path: Optional[str] = None, error: Optional[str] = None) -> None:
    """Log memory/database initialization."""
    if status == "start":
        console.print(Panel.fit(
            "[bold blue]💾 Initializing Memory System[/bold blue]",
            border_style="blue"
        ))
        logger.info("Memory initialization started")
    elif status == "db_path":
        console.log(f"[dim]📂 Database: {db_path}[/dim]")
        logger.info(f"Database path: {db_path}")
    elif status == "connected":
        console.log("[green]✅ Database connection established[/green]")
        logger.info("Database connection successful")
    elif status == "saver_created":
        console.log("[green]✅ SqliteSaver instance created[/green]")
        logger.info("SqliteSaver initialized")
    elif status == "ready":
        console.log("[green]✅ Memory system ready[/green]")
        logger.info("Memory system fully initialized")
    elif status == "error":
        console.log(f"[bold red]❌ Memory initialization failed: {error}[/bold red]")
        logger.error(f"Memory initialization error: {error}")


def create_session_table(user_id: Any, message: str) -> Table:
    """Create session start summary table."""
    table = Table(
        title="🤖 Smart Chat Session",
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    table.add_row("User ID", str(user_id))
    table.add_row("Message Length", f"{len(message)} chars")
    table.add_row("Message Preview", _preview_text(message, 50))
    table.add_row("Timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))
    return table


# =============================================================================
# User Profile & Context Logging
# =============================================================================
def log_user_profile(user_id: str, profile: Optional[Dict[str, Any]]) -> None:
    """Log user profile loading."""
    if profile:
        console.log(f"[cyan]👤 User profile loaded for {user_id}[/cyan]")
        logger.info(f"User profile loaded: user_id={user_id}, keys={list(profile.keys())}")
    else:
        console.log(f"[yellow]⚠️ No profile found for {user_id}[/yellow]")
        logger.warning(f"User profile not found: user_id={user_id}")


def log_memory_user_resolution(state_user_id: str, resolved_id: str) -> None:
    """Log memory user ID resolution."""
    if state_user_id != resolved_id:
        console.log(f"[dim]🔄 Memory user ID: {state_user_id} → {resolved_id}[/dim]")
        logger.info(f"Memory user ID resolved: {state_user_id} -> {resolved_id}")


# =============================================================================
# Message Processing Logging
# =============================================================================
def log_message_conversion(original_type: str, has_media: bool) -> None:
    """Log message format conversion."""
    if has_media:
        console.log(f"[dim]🔄 Converting {original_type} with media content[/dim]")
        logger.debug(f"Message conversion: {original_type} with media")


def log_message_stats(messages: List[AnyMessage], stage: str) -> None:
    """Log message statistics at different stages."""
    type_counts = {}
    for msg in messages:
        msg_type = _format_message_type(msg)
        type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
    
    total_chars = _sum_content_length(messages)
    type_display = ", ".join(f"{t}:{c}" for t, c in sorted(type_counts.items()))
    
    console.log(f"[dim]📊 {stage}: {len(messages)} messages ({type_display}), {total_chars} chars[/dim]")
    logger.debug(f"{stage}: messages={len(messages)}, types={type_counts}, chars={total_chars}")


# =============================================================================
# History & Summarization Logging
# =============================================================================
def log_history_state(
    stage: str,
    messages: Sequence[AnyMessage],
    summary_version: Optional[int] = None,
    summary_text: Optional[str] = None,
    token_count: Optional[int] = None,
) -> None:
    """Log conversation history state."""
    total_chars = _sum_content_length(messages)
    approx_tokens = token_count if token_count is not None else total_chars // 4
    
    info = f"{stage.title()}: {len(messages)} msgs, {total_chars} chars (~{approx_tokens} tokens)"
    if summary_version is not None:
        info += f", summary_v{summary_version}"
    
    console.log(f"[dim]📚 {info}[/dim]")
    logger.debug(info)
    
    if summary_text:
        console.log(f"[magenta]📝 Summary: {_preview_text(summary_text, 160)}[/magenta]")


def log_summarization_trigger(
    total_messages: int,
    unsummarized_count: int,
    token_count: int,
    token_budget: int
) -> None:
    """Log why summarization was triggered."""
    console.log(f"[magenta]🧪 Summarization triggered[/magenta]")
    console.log(f"[dim]   Total messages: {total_messages}[/dim]")
    console.log(f"[dim]   Unsummarized: {unsummarized_count}[/dim]")
    console.log(f"[dim]   Tokens: {token_count} / {token_budget}[/dim]")
    logger.info(f"Summarization: total={total_messages}, unsummarized={unsummarized_count}, tokens={token_count}/{token_budget}")


def log_summary_action(action: str, summary_text: str, message_span: int) -> None:
    """Log summary creation/update."""
    console.log(f"[magenta]✅ Summary {action}: {message_span} messages[/magenta]")
    console.log(f"[dim]   Preview: {_preview_text(summary_text, 160)}[/dim]")
    logger.info(f"Summary {action}: messages={message_span}, length={len(summary_text)}")


def log_summarization_skip(reason: str) -> None:
    """Log why summarization was skipped."""
    console.log(f"[dim]⏭️ Summarization skipped: {reason}[/dim]")
    logger.debug(f"Summarization skipped: {reason}")


# =============================================================================
# Memory (Mem0) Logging
# =============================================================================
def log_memory_search(user_id: str, query: str, limit: int) -> None:
    """Log memory search initiation."""
    console.log(f"[blue]🔍 Searching memories for {user_id}[/blue]")
    console.log(f"[dim]   Query: {_preview_text(query, 80)}[/dim]")
    console.log(f"[dim]   Limit: {limit}[/dim]")
    logger.info(f"Memory search: user={user_id}, query_len={len(query)}, limit={limit}")


def log_memory_results(user_id: str, count: int, memories: List[Dict[str, Any]]) -> None:
    """Log memory search results."""
    if count > 0:
        console.log(f"[blue]🧠 Found {count} memories for {user_id}[/blue]")
        for i, mem in enumerate(memories[:3], 1):
            console.log(f"[dim]   {i}. {_preview_text(mem.get('content', ''), 60)}[/dim]")
        logger.info(f"Memory results: user={user_id}, count={count}")
    else:
        console.log(f"[dim]🧠 No memories found for {user_id}[/dim]")
        logger.debug(f"No memories found: user={user_id}")


def log_memory_search_error(user_id: str, error: Exception) -> None:
    """Log memory search failure."""
    console.log(f"[yellow]⚠️ Memory search failed for {user_id}: {error}[/yellow]")
    logger.warning(f"Memory search error: user={user_id}, error={error}")


def log_memory_storage(user_id: str, status: str = "initiated") -> None:
    """Log memory storage operation."""
    if status == "initiated":
        console.log(f"[dim]💾 Storing memory for {user_id}...[/dim]")
        logger.debug(f"Memory storage initiated: user={user_id}")
    elif status == "success":
        console.log(f"[dim]✅ Memory stored for {user_id}[/dim]")
        logger.info(f"Memory stored successfully: user={user_id}")
    elif status == "error":
        console.log(f"[red]❌ Memory storage failed for {user_id}[/red]")
        logger.error(f"Memory storage failed: user={user_id}")


# =============================================================================
# System Prompt & Context Logging
# =============================================================================
def log_system_instructions(instructions: Sequence[str]) -> None:
    """Log system instructions being sent to LLM."""
    console.log(f"[bold blue]📋 System Instructions: {len(instructions)} components[/bold blue]")
    for idx, text in enumerate(instructions, 1):
        preview = _preview_text(text, 200)
        console.log(f"[dim]   {idx}. {preview}[/dim]")
    logger.debug(f"System instructions: count={len(instructions)}")


def log_context_building(
    has_profile: bool,
    has_summary: bool,
    has_memory: bool,
    active_messages: int
) -> None:
    """Log context assembly."""
    components = []
    if has_profile:
        components.append("profile")
    if has_summary:
        components.append("summary")
    if has_memory:
        components.append("memory")
    
    console.log(f"[cyan]🔧 Building context: {', '.join(components) if components else 'none'}[/cyan]")
    console.log(f"[dim]   Active messages: {active_messages}[/dim]")
    logger.debug(f"Context: profile={has_profile}, summary={has_summary}, memory={has_memory}, messages={active_messages}")


# =============================================================================
# LLM Invocation Logging
# =============================================================================
def log_invocation_payload(messages: Sequence[AnyMessage]) -> None:
    """Log LLM invocation payload details."""
    type_counts = {}
    for msg in messages:
        msg_type = _format_message_type(msg)
        type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
    
    type_display = ", ".join(f"{t}:{c}" for t, c in sorted(type_counts.items()))
    total_chars = _sum_content_length(messages)
    
    console.log(f"[yellow]🚀 LLM Invocation[/yellow]")
    console.log(f"[dim]   Messages: {len(messages)} ({type_display})[/dim]")
    console.log(f"[dim]   Total chars: {total_chars}[/dim]")
    logger.info(f"LLM invocation: messages={len(messages)}, types={type_counts}, chars={total_chars}")


def log_llm_response(response: AIMessage, duration: float) -> None:
    """Log LLM response received."""
    content_len = len(response.content) if response.content else 0
    console.log(f"[green]✅ Response received ({duration:.2f}s, {content_len} chars)[/green]")
    console.log(f"[dim]   Preview: {_preview_text(str(response.content), 100)}[/dim]")
    logger.info(f"LLM response: duration={duration:.2f}s, length={content_len}")


def log_llm_error(error: Exception, duration: float) -> None:
    """Log LLM invocation failure."""
    console.log(f"[red]❌ LLM invocation failed ({duration:.2f}s): {error}[/red]")
    logger.error(f"LLM error: {error}", exc_info=True)


# =============================================================================
# Stream Processing Logging
# =============================================================================
def log_stream_start() -> None:
    """Log stream processing start."""
    console.log("[yellow]🌊 Starting agent stream...[/yellow]")
    logger.info("Agent stream started")


def log_stream_event(event_num: int, event_data: Dict[str, Any]) -> None:
    """Log individual stream event."""
    console.log(f"[cyan]📨 Event {event_num}[/cyan]")
    
    if isinstance(event_data, dict):
        keys = list(event_data.keys())
        console.log(f"[dim]   Keys: {keys}[/dim]")
        
        if "messages" in event_data:
            msg_count = len(event_data["messages"])
            console.log(f"[dim]   Messages: {msg_count}[/dim]")
            logger.debug(f"Stream event {event_num}: messages={msg_count}")


def log_stream_completion(event_count: int, duration: float) -> None:
    """Log stream processing completion."""
    console.log(f"[green]✅ Stream completed: {event_count} events ({duration:.2f}s)[/green]")
    logger.info(f"Stream completed: events={event_count}, duration={duration:.2f}s")


# =============================================================================
# Response Processing Logging
# =============================================================================
def log_response_refinement(original_len: int, refined_len: int) -> None:
    """Log response optimization for Telegram."""
    console.log(f"[dim]🔧 Response refined: {original_len} → {refined_len} chars[/dim]")
    logger.debug(f"Response refinement: {original_len} -> {refined_len} chars")


def log_refinement_error(error: Exception) -> None:
    """Log response refinement failure."""
    console.log(f"[yellow]⚠️ Refinement failed: {error}[/yellow]")
    logger.warning(f"Response refinement error: {error}")


# =============================================================================
# Success & Error Tables
# =============================================================================
def create_success_table(duration: float, event_count: int, content: str) -> Table:
    """Create success summary table."""
    table = Table(
        title="✅ Chat Completed Successfully",
        show_header=True,
        header_style="bold green",
    )
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Duration", f"{duration:.2f}s")
    table.add_row("Events Processed", str(event_count))
    table.add_row("Response Length", f"{len(content)} chars")
    table.add_row("Response Preview", _preview_text(content, 100))
    return table


def create_error_table(exception: Exception, duration: float, user_id: Any) -> Table:
    """Create error summary table."""
    table = Table(
        title="❌ Chat Error",
        show_header=True,
        header_style="bold red"
    )
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Error Type", type(exception).__name__)
    table.add_row("Error Message", str(exception))
    table.add_row("Duration", f"{duration:.2f}s")
    table.add_row("User ID", str(user_id))
    return table


# =============================================================================
# Progress Indicator
# =============================================================================
def build_progress() -> Progress:
    """Create progress indicator for streaming."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )


# =============================================================================
# Configuration Logging
# =============================================================================
def log_config(config: Dict[str, Any]) -> None:
    """Log configuration details."""
    console.log(f"[blue]🔧 Config: {config}[/blue]")
    logger.debug(f"Configuration: {config}")


def log_empty_message() -> None:
    """Log empty message handling."""
    console.log("[yellow]⚠️ Empty message received, returning history[/yellow]")
    logger.debug("Empty message: returning history")


def log_history_retrieval(count: int) -> None:
    """Log history retrieval."""
    console.log(f"[green]📚 Retrieved {count} messages from history[/green]")
    logger.info(f"History retrieved: {count} messages")
