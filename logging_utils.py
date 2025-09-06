import json
import time
import os
import logging
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from logging.handlers import RotatingFileHandler

# Initialize console and logging
console = Console()
log = logging.getLogger("blue-ai")

# Ensure logs directory exists
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
JSONL_PATH = os.path.join(LOG_DIR, "blue_ai_logs.jsonl")

# Configure logging
class JSONLineFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "ts": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }
        if hasattr(record, "meta"):
            data.update(record.meta)
        return json.dumps(data, ensure_ascii=False)

def setup_logging():
    """Initialize logging with both console and file handlers"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)]
    )
    
    # Add JSON file handler
    json_handler = RotatingFileHandler(
        JSONL_PATH, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    json_handler.setFormatter(JSONLineFormatter())
    log.addHandler(json_handler)

def display_llm_interaction(
    system_instruction: str,
    user_input: str,
    ai_response: str,
    history: List[Dict[str, Any]],
    conversation_summary: Optional[str] = None,
    llm_calls: int = 1,
    status_updates: Optional[List[str]] = None
) -> None:
    """Display a standardized table for LLM interactions"""
    table = Table(
        title="🤖 LLM Interaction Details",
        show_lines=True,
        title_style="bold cyan",
        expand=True
    )
    
    table.add_column("Component", style="cyan", width=20)
    table.add_column("Content", style="white", ratio=1)

    # Core components
    table.add_row(
        "System Instruction",
        Text(system_instruction[:1000] + "..." if len(system_instruction) > 1000 else system_instruction)
    )
    table.add_row(
        "User Input",
        Text(user_input[:1000] + "..." if len(user_input) > 1000 else user_input)
    )
    table.add_row(
        "AI Response",
        Text(ai_response[:2000] + "..." if len(ai_response) > 2000 else ai_response)
    )

    # History summary
    history_text = (
        f"Total messages: {len(history)}\n"
        f"Latest 3 turns:\n" +
        "\n".join(
            f"[{msg['role']}] {msg['content'][:100]}..."
            for msg in history[-3:]
        )
    )
    table.add_row("History", Text(history_text))

    if conversation_summary:
        table.add_row(
            "Conversation Summary",
            Text(conversation_summary[:500] + "..." if len(conversation_summary) > 500 else conversation_summary)
        )

    # Stats & Status
    stats_text = f"LLM calls in this turn: {llm_calls}"
    table.add_row("Stats", Text(stats_text))

    if status_updates:
        status_text = "\n".join(f"• {update}" for update in status_updates)
        table.add_row("Status Updates", Text(status_text))

    console.print(table)

def log_process_status(title: str, status_list: List[str]) -> None:
    """Display a simple status panel for process updates"""
    status_text = "\n".join(f"{'✅' if i < len(status_list)-1 else '⏳'} {s}" 
                           for i, s in enumerate(status_list))
    console.print(Panel(
        status_text,
        title=f"[cyan]{title}[/cyan]",
        border_style="bright_blue"
    ))

def write_event(event_type: str, data: Dict[str, Any]) -> None:
    """Write a structured event to the JSONL log file"""
    try:
        event = {
            "type": event_type,
            "ts": time.time(),
            **data
        }
        with open(JSONL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        log.error(f"Failed to write event: {e}")

# Initialize logging on module import
setup_logging()
