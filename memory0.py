# agent_mem0_gemini.py
"""
LangGraph + Gemini (LangChain) + Mem0 (OSS) long-term memory with local Qdrant.

New in this version:
- Detailed Mem0 logging:
  • Logs Mem0.search() results (IDs, text, scores/metadata) before the LLM call
  • Logs FULL memory list (get_all) after each turn
- Safe extractors so logs won't crash if Mem0 returns slightly different shapes
- Collection/dimension name aligned with EMBED_DIM to avoid Qdrant mismatches
"""

import os
import time
import json
import logging
from typing import Annotated, List, Optional, Any, Dict

# LangGraph / LangChain
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.pregel import Pregel
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage

# Gemini (Google Generative AI) via LangChain
from langchain_google_genai import ChatGoogleGenerativeAI  # pip: langchain-google-genai

# Local embeddings via Ollama
from langchain_ollama import OllamaEmbeddings  # pip: langchain-ollama

# Mem0 open-source SDK
from mem0 import Memory  # pip: mem0ai

# Optional: richer terminal output
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

console = Console()
logger = logging.getLogger(__name__)

# ==========================
# Tunables / policy
# ==========================
SUMMARY_TRIGGER_MESSAGES = 24
RECENT_MESSAGES_KEEP = 8
MAX_WORKING_CHARS = 12_000
MEM0_TOPK = 3              # keep memory block tiny

# ==========================
# LLM: Gemini via LangChain
# ==========================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY_NEURON")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY_NEURON not set in .env file")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    google_api_key=GOOGLE_API_KEY,
)

# ==========================
# Embeddings: Ollama nomic-embed-text (local)
# ==========================
embedder = OllamaEmbeddings(model="nomic-embed-text")

# Confirm/declare the expected embedding dimension.
# nomic-embed-text commonly emits 768 dims; change if you probed a different size.
EMBED_DIM = 768

# ==========================
# Mem0 (OSS) client config
# ==========================
# NOTE: collection_name updated to match the dimension for clarity.
mem0_config = {
    "llm": {
        "provider": "langchain",
        "config": {
            "model": llm,
        }
    },
    "embedder": {
        "provider": "langchain",
        "config": {
            "model": embedder,
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": "localhost",
            "port": 6333,
            "collection_name": "mem0_nomic_768",
            "embedding_model_dims": EMBED_DIM
        }
    },
}
mem0_client = Memory.from_config(mem0_config)

# ==========================
# Prompts
# ==========================
NEURON = (
    "You are a helpful, concise assistant. "
    "Use the [Conversation Summary] and the recent messages to reason. "
    "If a [Mem0 Memory] block is present, treat it as reliable facts/preferences about the user."
)

HISTORY_SUMMARY_PROMPT = (
    "You are a high-precision summarizer. Merge the conversation below into a compact rolling summary "
    "that preserves user goals, constraints, decisions, preferences, and action items.\n\n"
    "=== CONVERSATION ===\n{conversation}\n\n"
    "=== PRIOR SUMMARY ===\n{prior_summary}\n\n"
    "Return ONLY the updated summary."
)

# ==========================
# Utilities
# ==========================
def _total_chars(msgs: List[AnyMessage]) -> int:
    return sum(len(getattr(m, "content", "") or "") for m in msgs)

def _need_summarize(history: List[AnyMessage]) -> bool:
    return len(history) > SUMMARY_TRIGGER_MESSAGES

def _build_transcript(messages: List[AnyMessage]) -> str:
    lines = []
    for m in messages:
        role = getattr(m, "type", m.__class__.__name__)
        content = getattr(m, "content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)

def _summarize_chunk(prior_summary: str, chunk_messages: List[AnyMessage]) -> str:
    transcript = _build_transcript(chunk_messages)[:8000]
    prompt = HISTORY_SUMMARY_PROMPT.format(
        conversation=transcript,
        prior_summary=prior_summary or "",
    )
    msg = llm.invoke([SystemMessage(content="You summarize chats."), HumanMessage(content=prompt)])
    return (msg.content or "").strip()

def _tail(history: List[AnyMessage], k: int) -> List[AnyMessage]:
    start = max(0, len(history) - k)
    return history[start:]

# -------- Mem0 logging helpers --------
def _extract_list(value: Any) -> List[Dict[str, Any]]:
    """Return a list from Mem0 responses that may be dicts with 'results' or already lists."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if "results" in value and isinstance(value["results"], list):
            return value["results"]
        # Sometimes Mem0 returns {"data": [...]} or similar; try common fallbacks:
        if "data" in value and isinstance(value["data"], list):
            return value["data"]
        # Single item dict; wrap it:
        return [value]
    # Unknown shape: just wrap for safe logging
    return [value]

def _pretty_mem_row(item: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a Mem0 memory item to a friendly row for logging."""
    return {
        "id": item.get("id") or item.get("_id") or "-",
        "memory": item.get("memory") or item.get("text") or item.get("content") or "",
        "score": item.get("score") or item.get("similarity") or "",
        "created_at": item.get("created_at") or "",
        "updated_at": item.get("updated_at") or "",
        "metadata": item.get("metadata") or {},
    }

def _log_mem0_search(title: str, results: Any):
    """Log Mem0.search() results in a rich table and raw JSON."""
    rows = [_pretty_mem_row(x) for x in _extract_list(results)]
    table = Table(title=title, header_style="bold cyan", show_lines=True)
    table.add_column("ID", style="magenta", overflow="fold")
    table.add_column("Score", style="yellow", overflow="fold")
    table.add_column("Memory", style="white", overflow="fold")
    table.add_column("Metadata", style="dim", overflow="fold")
    for r in rows:
        meta_str = json.dumps(r["metadata"], ensure_ascii=False)
        table.add_row(str(r["id"]), str(r["score"]), str(r["memory"]), meta_str)
    console.print(table)
    console.print(Panel.fit(JSON.from_data(results), title=f"{title} - Raw JSON", border_style="dim"))

def _log_mem0_full_list(user_id: str):
    """Fetch and log the full memory list for a user."""
    try:
        all_mems = mem0_client.get_all(user_id=user_id)
    except Exception as e:
        console.log(f"[red]❌ mem0.get_all failed: {e}[/red]")
        return

    rows = [_pretty_mem_row(x) for x in _extract_list(all_mems)]
    table = Table(title=f"🧠 Mem0: FULL MEMORY LIST (user_id={user_id})", header_style="bold green", show_lines=True)
    table.add_column("ID", style="magenta", overflow="fold")
    table.add_column("Memory", style="white", overflow="fold")
    table.add_column("Created", style="cyan", overflow="fold")
    table.add_column("Updated", style="cyan", overflow="fold")
    table.add_column("Metadata", style="dim", overflow="fold")
    for r in rows:
        meta_str = json.dumps(r["metadata"], ensure_ascii=False)
        table.add_row(str(r["id"]), str(r["memory"]), str(r["created_at"]), str(r["updated_at"]), meta_str)

    console.print(table)
    console.print(Panel.fit(JSON.from_data(all_mems), title="FULL MEMORY LIST - Raw JSON", border_style="dim"))

# ==========================
# LangGraph state (two streams)
# ==========================
class AgentState(dict):
    """
    - history: append-only (persisted between turns)
    - messages: compact working prompt (rebuilt each turn)
    - summary: rolling textual summary
    - user_id: stable identifier to scope Mem0 memories per user
    """
    history: Annotated[list[AnyMessage], add_messages]
    messages: list[AnyMessage]
    summary: Optional[str] = ""
    user_id: Optional[str] = None

# ==========================
# Nodes
# ==========================
def router(state: AgentState) -> dict:
    """Prepare the working prompt, then decide whether to summarize."""
    console.log("[blue]🧭 Router preparing prompt...[/blue]")
    history = state.get("history", []) or []
    summary = state.get("summary") or ""

    # compact working prompt
    working: List[AnyMessage] = [SystemMessage(content=NEURON)]
    if summary:
        working.append(SystemMessage(content=f"[Conversation Summary]\n{summary}"))

    # latest user message appended
    if history:
        working.append(history[-1])

    console.log(f"[dim]📊 Initial working_count={len(working)} chars={_total_chars(working)}")
    return {"messages": working}

def summarize_node():
    def _summarize(state: AgentState):
        history = state.get("history", []) or []
        if not history:
            return {}

        cut = max(0, len(history) - RECENT_MESSAGES_KEEP)
        older, tail = history[:cut], history[cut:]

        new_summary = state.get("summary") or ""
        if older:
            console.log("[magenta]🧪 Summarizing older history...[/magenta]")
            new_summary = _summarize_chunk(new_summary, older)

        working: List[AnyMessage] = [SystemMessage(content=NEURON)]
        if new_summary:
            working.append(SystemMessage(content=f"[Conversation Summary]\n{new_summary}"))
        working.extend(tail)

        while len(working) > 1 and _total_chars(working) > MAX_WORKING_CHARS:
            console.log("[yellow]⚠️ Safety trim: dropping oldest retained message from working prompt[/yellow]")
            del working[2 if len(working) > 2 else 1]

        console.log(f"[dim]📊 After summarize: working_count={len(working)} chars={_total_chars(working)}")
        return {"summary": new_summary, "messages": working}
    return _summarize

def chatbot_node():
    def _chatbot(state: AgentState):
        working = state.get("messages", []) or []
        console.log(f"[dim]📝 Working prompt size: {len(working)} msgs, chars={_total_chars(working)}")

        # === Mem0: retrieve top-K memories for last user text ===
        uid = state.get("user_id") or "default_user"
        last_user_text = None
        for m in reversed(working):
            if isinstance(m, HumanMessage):
                last_user_text = m.content
                break

        memory_msg = None
        if last_user_text:
            try:
                search_res = mem0_client.search(query=last_user_text, user_id=uid, limit=MEM0_TOPK)
                _log_mem0_search("🔎 Mem0.search() hits", search_res)  # <— detailed log

                hits = _extract_list(search_res)
                if hits:
                    bullets = "\n".join(f"- {(_pretty_mem_row(h)['memory'] or '').strip()}" for h in hits)
                    memory_msg = SystemMessage(content=f"[Mem0 Memory]\nUse if relevant:\n{bullets}")
            except Exception as e:
                console.log(f"[yellow]⚠️ Mem0.search failed: {e}[/yellow]")

        prompt_messages = ([memory_msg] + working) if memory_msg else working

        # === Gemini call via LangChain ===
        start = time.time()
        response = llm.invoke(prompt_messages)
        console.log(f"[green]✅ LLM response in {time.time() - start:.2f}s")

        # === Mem0: add this interaction ===
        try:
            if last_user_text:
                add_res = mem0_client.add(
                    [
                        {"role": "user", "content": last_user_text},
                        {"role": "assistant", "content": getattr(response, "content", "")},
                    ],
                    user_id=uid,
                    agent_id="langgraph-gemini-agent",
                    metadata={"source": "langgraph"},
                )
                console.print(Panel.fit(JSON.from_data(add_res), title="➕ Mem0.add() response", border_style="green"))
        except Exception as e:
            console.log(f"[yellow]⚠️ Mem0.add failed: {e}[/yellow]")

        # === Mem0: full list after this turn ===
        _log_mem0_full_list(uid)

        return {"messages": [response]}
    return _chatbot

# ==========================
# Build/compile the agent
# ==========================
def build_agent() -> Pregel:
    graph = StateGraph(AgentState)
    graph.add_node("router", router)
    graph.add_node("summarize", summarize_node())
    graph.add_node("chatbot", chatbot_node())

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        lambda s: "summarize" if _need_summarize((s.get("history") or [])) else "chatbot",
        {"summarize": "summarize", "chatbot": "chatbot"},
    )
    graph.add_edge("summarize", "chatbot")
    graph.add_edge("chatbot", END)

    return graph.compile()

# ==========================
# Simple REPL / demo
# ==========================
if __name__ == "__main__":
    agent = build_agent()
    user_id = os.getenv("DEMO_USER_ID", "demo-user-123")

    print("Agent ready. Type 'exit' to stop.")
    while True:
        text = input("You: ").strip()
        if text.lower() == "exit":
            break

        out = agent.invoke({"history": [HumanMessage(content=text)], "user_id": user_id})
        msgs = out.get("messages", [])
        if msgs and isinstance(msgs[-1], AIMessage):
            print("AI:", msgs[-1].content)
        else:
            print("AI: (no response)")

        # Also dump FULL memory list at the very end of each turn from the REPL-side (extra guarantee)
        _log_mem0_full_list(user_id)
