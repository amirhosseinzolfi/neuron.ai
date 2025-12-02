# agent_terminal.py
# ──────────────────────────────────────────────────────────────────────────────
# Terminal Conversation Agent — ONE LLM CALL PER TURN
# - Persistent MCP Memory Server (stdio via npx)
# - LangGraph: LoadMemory → ChatAndMemory (one LLM call) → UpdateMemory(opt)
# - The LLM returns JSON: { reply, memory: { should_write, observations[] } }
# - Commands: /memory, /forget <obs>, /exit
# - Structured, colorful logging
# ──────────────────────────────────────────────────────────────────────────────

import asyncio
import os
import json
import re
import logging
from logging import Logger
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict
from contextlib import asynccontextmanager

from colorama import init as color_init, Fore, Style

# MCP SDK (modern)
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# LangGraph / LangChain Core
from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

# LLM: Gemini via LangChain
from langchain_google_genai import ChatGoogleGenerativeAI

# ──────────────────────────────────────────────────────────────────────────────
# Logging

color_init(autoreset=True)

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Fore.BLUE,
        logging.INFO: Fore.CYAN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA + Style.BRIGHT,
    }
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        level = f"{color}{record.levelname}{Style.RESET_ALL}"
        return f"{Fore.WHITE}[{self.formatTime(record, '%H:%M:%S')}] {level} {Fore.GREEN}»{Style.RESET_ALL} {record.getMessage()}"

def get_logger(name: str = "agent") -> Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
        ch = logging.StreamHandler()
        ch.setFormatter(ColorFormatter())
        logger.addHandler(ch)
        # optional file log
        log_dir = Path("logs"); log_dir.mkdir(exist_ok=True)
        fh = logging.FileHandler(log_dir / "agent.log", encoding="utf-8")
        fh.setFormatter(ColorFormatter())
        logger.addHandler(fh)
    return logger

log = get_logger()

def section(title: str):
    line = f"{'-'*12} {title} {'-'*12}"
    log.info(Fore.MAGENTA + line + Style.RESET_ALL)

# ──────────────────────────────────────────────────────────────────────────────
# Memory config

PROJECT_ROOT = Path(__file__).resolve().parent
MEM_DIR = PROJECT_ROOT / "memory"
MEM_DIR.mkdir(parents=True, exist_ok=True)
MEM_FILE = str(MEM_DIR / "memory.json")
if not Path(MEM_FILE).exists():
    Path(MEM_FILE).write_text(json.dumps({"entities": [], "relations": []}, ensure_ascii=False))
    log.info(f"Created new memory file at: {MEM_FILE}")

DEFAULT_USER_ENTITY = "default_user"

# ──────────────────────────────────────────────────────────────────────────────
# LLM config
GEMINI_MODEL = "gemini-2.0-flash"
GOOGLE_API_KEY = "AIzaSyBAHu5yR3ooMkyVyBmdFxw-8lWyaExLjjE"

def get_llm() -> ChatGoogleGenerativeAI:
    # single LLM used for both chat and memory extraction (one call)
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.3,
    )

# ──────────────────────────────────────────────────────────────────────────────
# Tool result → JSON (for MCP CallToolResult parsing if needed later)

def tool_result_to_json(result: Any, *, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    default = default or {}
    try:
        content = getattr(result, "content", None)
        if not content:
            return default
        for block in content:
            btype = getattr(block, "type", None) or getattr(block, "mimeType", None)
            if btype in ("json", "application/json"):
                data = getattr(block, "data", None)
                if isinstance(data, (dict, list)):
                    return {"data": data} if isinstance(data, list) else data
                if isinstance(data, str):
                    try: return json.loads(data)
                    except Exception: pass
            if btype in ("text", "string", None):
                text = getattr(block, "text", None) or getattr(block, "data", None)
                if isinstance(text, str):
                    try: return json.loads(text)
                    except Exception: return {"text": text}
        try:
            return {"raw": [getattr(b, "model_dump", lambda: str(b))() for b in content]}
        except Exception:
            return default
    except Exception as e:
        log.warning(f"Failed to parse tool result as JSON: {e}")
        return default

# ──────────────────────────────────────────────────────────────────────────────
# Persistent MCP runtime

class MemoryRuntime:
    def __init__(self, mem_file: str):
        self.mem_file = mem_file
        self._ctx = None
        self._streams = None
        self.session: Optional[ClientSession] = None

    async def start(self):
        env = os.environ.copy()
        env["MEMORY_FILE_PATH"] = self.mem_file
        params = StdioServerParameters(
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"],
            env=env,
        )
        section("Start MCP Memory Server (persistent)")
        self._ctx = stdio_client(params)
        self._streams = await self._ctx.__aenter__()
        self.session = ClientSession(*self._streams)
        await self.session.__aenter__()
        await self.session.initialize()
        tools = await self.session.list_tools()
        log.info("TOOLS: " + ", ".join(t.name for t in tools.tools))
        await ensure_entity(self.session, DEFAULT_USER_ENTITY, "person")

    async def stop(self):
        section("Stop MCP Memory Server")
        if self.session:
            await self.session.__aexit__(None, None, None)
            self.session = None
        if self._ctx:
            await self._ctx.__aexit__(None, None, None)
            self._ctx = None

# ──────────────────────────────────────────────────────────────────────────────
# MCP helpers

async def ensure_entity(session: ClientSession, name: str, etype: str):
    await session.call_tool("create_entities", arguments={
        "entities": [{"name": name, "entityType": etype, "observations": []}]
    })

async def add_observations(session: ClientSession, entity: str, contents: List[str]):
    if not contents:
        return
    await session.call_tool("add_observations", arguments={
        "observations": [{"entityName": entity, "contents": contents}]
    })

async def open_nodes(session: ClientSession, names: List[str]) -> Dict[str, Any]:
    res = await session.call_tool("open_nodes", arguments={"names": names})
    return tool_result_to_json(res, default={"entities": [], "relations": []})

async def read_graph(session: ClientSession) -> Dict[str, Any]:
    res = await session.call_tool("read_graph", arguments={})
    return tool_result_to_json(res, default={"entities": [], "relations": []})

async def delete_observations(session: ClientSession, entity: str, observations: List[str]):
    if not observations:
        return
    await session.call_tool("delete_observations", arguments={
        "deletions": [{"entityName": entity, "observations": observations}]
    })

# ──────────────────────────────────────────────────────────────────────────────
# Memory summarization for System prompt

def summarize_memory_for_system(opened: Dict[str, Any]) -> str:
    entities = opened.get("entities") or []
    rels = opened.get("relations") or []
    lines = [
        "You have a persistent memory (knowledge graph). Use it to personalize answers.",
        "Memory snapshot:"
    ]
    for e in entities:
        name = e.get("name")
        etype = e.get("entityType")
        obs = e.get("observations") or []
        lines.append(f"- {name} [{etype}]")
        for o in obs:
            lines.append(f"  • {o}")
    if rels:
        lines.append("Relations:")
        for r in rels:
            lines.append(f"  • {r.get('from')} --{r.get('relationType')}--> {r.get('to')}")
    return "\n".join(lines)

# ──────────────────────────────────────────────────────────────────────────────
# LangGraph state & nodes

class State(TypedDict, total=False):
    messages: List[BaseMessage]
    user_entity: str
    _mem_session: ClientSession
    pending_observations: List[str]
    should_write: bool

# ONE-CALL SYSTEM PROMPT for combined chat + memory
COMBINED_SYSTEM = """You are a helpful assistant with a long-term memory tool.
You MUST respond in pure JSON (no code fences, no extra text) with this schema:

{
  "reply": "<assistant message for the user, same language as the user>",
  "memory": {
    "should_write": true | false,
    "observations": ["<atomic key=value facts to store>", "..."]
  }
}

Rules for memory:
- Only store stable, personal facts about the user (identity, preferences, goals, relationships, skills).
- If the user asks you to remember something, set should_write=true and produce 1–5 atomic observations.
- Use English keys on the LEFT side (Name, Occupation, City, Prefers, Likes, Speaks, WorksAt, Birthday, Goal, etc.).
- Keep observations SHORT and unambiguous, e.g., "Occupation=Software developer", "Prefers=Persian responses".
- If nothing suitable, set should_write=false and observations=[].

Return VALID JSON ONLY.
"""

def parse_json_loose(text: str) -> Optional[Dict[str, Any]]:
    """
    Best-effort JSON parser:
    - tries json.loads directly
    - strips code fences if present
    - finds first '{' to last '}' slice
    """
    try:
        return json.loads(text)
    except Exception:
        pass
    # strip code fences
    m = re.search(r"\{.*\}", text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None

async def chat_and_memory(state: State) -> State:
    """ONE LLM CALL: produce the assistant reply + memory decision in one JSON."""
    section("Node: ChatAndMemory (one LLM call)")
    llm = get_llm()
    messages = state["messages"]

    # Ask for JSON output including reply + memory
    prompt = [SystemMessage(content=COMBINED_SYSTEM)] + messages
    result = await llm.ainvoke(prompt)
    raw = str(result.content).strip()
    log.info(f"Raw LLM JSON length: {len(raw)}")

    data = parse_json_loose(raw) or {"reply": raw, "memory": {"should_write": False, "observations": []}}
    reply = data.get("reply", raw)
    mem = data.get("memory", {}) or {}
    should_write = bool(mem.get("should_write", False))
    observations = mem.get("observations") or []
    if not isinstance(observations, list):
        observations = []

    # Build AI message for dialogue
    ai_msg = AIMessage(content=str(reply))

    log.info(f"Extractor(one-call) → should_write={should_write}, obs={observations}")
    return {
        "messages": messages + [ai_msg],
        "pending_observations": observations,
        "should_write": should_write,
    }

async def update_memory(state: State) -> State:
    section("Node: UpdateMemory")
    if not state.get("should_write"):
        log.info("Skip memory write (router decided False)")
        return {}
    s = state["_mem_session"]
    user_entity = state.get("user_entity", DEFAULT_USER_ENTITY)

    # Load existing observations for the user
    opened = await open_nodes(s, [user_entity])
    existing = []
    for e in opened.get("entities", []):
        if e.get("name") == user_entity:
            existing.extend(e.get("observations") or [])
    existing_set = set(existing)

    pending = [o for o in (state.get("pending_observations") or []) if o]
    if not pending:
        log.info("No pending observations to write")
        return {}

    # Helpers to parse and merge "Key=Value" observations
    def parse_obs(obs: str):
        if "=" in obs:
            k, v = obs.split("=", 1)
            return k.strip(), v.strip()
        return None, obs.strip()

    def split_values(val_str: str):
        return [p.strip() for p in val_str.split(",") if p.strip()]

    # Build map of existing observations by key -> list of obs strings
    existing_by_key = {}
    for obs in existing:
        k, _ = parse_obs(obs)
        if k:
            existing_by_key.setdefault(k, []).append(obs)

    to_delete: List[str] = []
    to_add: List[str] = []

    # Process pending observations: merge by key when needed
    for obs in pending:
        k, v = parse_obs(obs)
        if k:
            if k in existing_by_key:
                # Gather all current values for this key
                vals = []
                for ex in existing_by_key[k]:
                    _, exv = parse_obs(ex)
                    vals.extend(split_values(exv))
                # Add new values if not present
                new_vals = split_values(v)
                for nv in new_vals:
                    if nv not in vals:
                        vals.append(nv)
                merged = f"{k}=" + ", ".join(vals)
                # If merged differs from any existing exact observation, replace existing ones
                if merged not in existing_set:
                    # delete all old observations for this key
                    to_delete.extend(existing_by_key[k])
                    to_add.append(merged)
                    # reflect change in set to prevent duplicates in same run
                    existing_set.add(merged)
            else:
                # Key not present: add unless exact duplicate exists
                if obs not in existing_set:
                    to_add.append(obs)
                    existing_set.add(obs)
        else:
            # Not a Key=Value observation: dedupe exact strings
            if obs not in existing_set:
                to_add.append(obs)
                existing_set.add(obs)

    # Apply deletions then additions
    if to_delete:
        await delete_observations(s, user_entity, to_delete)
        log.info(f"Deleted observations for merging: {to_delete}")
    if to_add:
        await add_observations(s, user_entity, to_add)
        log.info(f"Saved observations to memory for '{user_entity}': {to_add}")
    else:
        log.info("No new observations to write")

    return {}

async def load_memory(state: State) -> State:
    section("Node: LoadMemory")
    s = state["_mem_session"]
    user_entity = state.get("user_entity", DEFAULT_USER_ENTITY)
    await ensure_entity(s, user_entity, "person")
    opened = await open_nodes(s, [user_entity])
    sys = SystemMessage(content=summarize_memory_for_system(opened))
    log.info("Injected memory snapshot into SystemMessage")
    return {"messages": [sys] + state.get("messages", [])}

def build_graph():
    g = StateGraph(State)
    g.add_node("load_memory", load_memory)
    g.add_node("chat_and_memory", chat_and_memory)
    g.add_node("update_memory", update_memory)

    g.set_entry_point("load_memory")
    g.add_edge("load_memory", "chat_and_memory")
    g.add_edge("chat_and_memory", "update_memory")
    g.add_edge("update_memory", END)
    return g.compile()

# ──────────────────────────────────────────────────────────────────────────────
# Terminal loop

async def ainput(prompt: str = "") -> str:
    return await asyncio.get_event_loop().run_in_executor(None, lambda: input(prompt))

def pretty_user(s: str) -> str:
    return f"{Fore.GREEN}You{Style.RESET_ALL}: {s}"

def pretty_ai(s: str) -> str:
    return f"{Fore.CYAN}Assistant{Style.RESET_ALL}: {s}"

def pretty_sys(s: str) -> str:
    return f"{Fore.MAGENTA}System{Style.RESET_ALL}: {s}"

async def run_terminal_agent():
    # Start persistent MCP
    rt = MemoryRuntime(MEM_FILE)
    await rt.start()
    try:
        app = build_graph()
        history: List[BaseMessage] = []   # store Human/AI messages only
        user_entity = DEFAULT_USER_ENTITY

        print(Fore.YELLOW + "Type /help for commands. Start chatting!\n" + Style.RESET_ALL)
        while True:
            user_in = await ainput(pretty_user(""))
            user_in = user_in.strip()
            if not user_in:
                continue

            # Commands
            if user_in.lower() in ("/exit", "/quit"):
                print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
                break
            if user_in.lower() == "/help":
                print(
                    Fore.YELLOW +
                    "Commands:\n"
                    "  /memory              Show memory for current user\n"
                    "  /forget <text>       Delete an exact observation\n"
                    "  /exit                Quit\n" + Style.RESET_ALL
                )
                continue
            if user_in.lower() == "/memory":
                opened = await open_nodes(rt.session, [user_entity])  # type: ignore
                print(pretty_sys(json.dumps(opened, ensure_ascii=False, indent=2)))
                continue
            if user_in.lower().startswith("/forget"):
                parts = user_in.split(" ", 1)
                if len(parts) == 2 and parts[1].strip():
                    obs = parts[1].strip()
                    await delete_observations(rt.session, user_entity, [obs])  # type: ignore
                    print(pretty_sys(f"Deleted observation: {obs}"))
                else:
                    print(pretty_sys("Usage: /forget <exact observation text>"))
                continue

            # Normal turn
            state: State = {
                "messages": history + [HumanMessage(content=user_in)],
                "user_entity": user_entity,
                "_mem_session": rt.session,  # type: ignore
            }

            section("Run Conversation Graph (ONE CALL)")
            final = await app.ainvoke(state)

            # Assistant reply (last AI)
            msgs = final["messages"]
            last_ai = None
            for m in reversed(msgs):
                if isinstance(m, AIMessage):
                    last_ai = m; break
            print(pretty_ai(str(last_ai.content) if last_ai else str(msgs[-1].content)))

            # update history (exclude system messages)
            history.append(HumanMessage(content=user_in))
            if last_ai:
                history.append(last_ai)

    finally:
        await rt.stop()

# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        asyncio.run(run_terminal_agent())
    except KeyboardInterrupt:
        log.warning("Interrupted by user (Ctrl+C)")
