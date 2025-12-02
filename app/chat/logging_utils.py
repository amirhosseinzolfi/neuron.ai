"""Logging helpers centralized for the smart chat agent."""

import logging
import time
from typing import Any, Optional, Sequence

from langchain_core.messages import AnyMessage
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

console = Console()
logger = logging.getLogger("smart_chat")


def _preview_text(text: str, limit: int = 50) -> str:
    """Helper for creating shortened previews of longer text."""
    if len(text) <= limit:
        return text
    return f"{text[:limit]}..."


def _sum_content_length(messages: Sequence[AnyMessage]) -> int:
    return sum(len(getattr(m, "content", "") or "") for m in messages)


def log_system_instructions(instructions: Sequence[str]) -> None:
    """Emit the system role instructions that will be sent to the LLM."""
    console.log(f"[bold blue]System instructions ({len(instructions)}):[/bold blue]")
    for idx, text in enumerate(instructions, 1):
        console.log(f"[dim]Instruction {idx}: {_preview_text(text, 200)}[/dim]")


def log_history_state(
    stage: str,
    messages: Sequence[AnyMessage],
    summary_version: Optional[int] = None,
    summary_text: Optional[str] = None,
    token_count: Optional[int] = None,
) -> None:
    """Log contextual stats for a given slice of history."""
    total_chars = _sum_content_length(messages)
    approx_tokens = token_count if token_count is not None else total_chars // 4
    console.log(
        f"[dim]{stage.title()} history -> {len(messages)} messages, {total_chars} chars (~{approx_tokens} tokens)"
        + (f", summary_version={summary_version}" if summary_version is not None else "")
        + ".[/dim]"
    )
    if summary_text:
        console.log(f"[magenta]Summary preview: {_preview_text(summary_text, 160)}[/magenta]")


def log_summary_action(action: str, summary_text: str, message_span: int) -> None:
    console.log(
        f"[magenta]Summary {action} for {message_span} message(s). Preview: {_preview_text(summary_text, 160)}[/magenta]"
    )


def log_summary_report(
    trigger: str,
    message_span: int,
    tokens_before: int,
    tokens_after: int,
    summary_text: str,
) -> None:
    """Render structured output for summary operations."""
    table = Table(title="🧮 Conversation Summary", show_header=True, header_style="magenta")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    table.add_row("Trigger", trigger)
    table.add_row("Messages Condensed", str(message_span))
    table.add_row("Tokens Before", str(tokens_before))
    table.add_row("Tokens After", str(tokens_after))
    table.add_row("Summary Preview", _preview_text(summary_text, 160))
    console.print(table)


def log_trim_report(
    reason: str,
    before_tokens: int,
    after_tokens: int,
    before_len: int,
    after_len: int,
) -> None:
    """Render structured output for trim_messages usage."""
    table = Table(title="✂️ LangChain trim_messages", show_header=True, header_style="yellow")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    table.add_row("Reason", reason)
    table.add_row("Messages", f"{before_len} ➜ {after_len}")
    table.add_row("Tokens", f"{before_tokens} ➜ {after_tokens}")
    table.add_row("Tokens Reclaimed", str(max(0, before_tokens - after_tokens)))
    console.print(table)


def log_invocation_payload(messages: Sequence[AnyMessage]) -> None:
    """Log the payload that will be passed directly to the LLM."""
    type_counts = {}
    for msg in messages:
        type_counts[type(msg).__name__] = type_counts.get(type(msg).__name__, 0) + 1
    type_display = ", ".join(f"{t}:{c}" for t, c in sorted(type_counts.items()))
    console.log(
        f"[dim]LLM invocation payload -> {len(messages)} messages ({type_display})[/dim]"
    )


def create_session_table(user_id: Any, message: str) -> Table:
    """Builds a summary table for each session start."""
    table = Table(title="🤖 Smart Chat Session", show_header=True, header_style="bold magenta")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    table.add_row("User ID", str(user_id))
    table.add_row("Message Length", f"{len(message)} chars")
    table.add_row("Message Preview", _preview_text(message, 50))
    table.add_row("Timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))
    return table


def create_success_table(duration: float, event_count: int, content: str) -> Table:
    """Builds a table summarizing a successful chat response."""
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
    """Builds a table that surfaces exception details for the UI."""
    table = Table(title="❌ Chat Error", show_header=True, header_style="bold red")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Error Type", type(exception).__name__)
    table.add_row("Error Message", str(exception))
    table.add_row("Duration", f"{duration:.2f}s")
    table.add_row("User ID", str(user_id))
    return table


def build_progress() -> Progress:
    """Returns a ready-made progress context for streaming events."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )
