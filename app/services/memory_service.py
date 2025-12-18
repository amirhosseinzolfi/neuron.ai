"""
Memory Service
----------------------------------------------------------------------
Unified memory management service combining Mem0 AI client and local fallback.
Implements standard Mem0 integration with LangGraph strategy.
"""

import os
import json
import sqlite3
import logging
import hashlib
from typing import List, Dict, Any, Optional
from threading import Lock

from dotenv import load_dotenv
from langchain_ollama import OllamaEmbeddings
from mem0 import Memory

from ai_utils import get_memory_llm

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger("memory_service")
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.json import JSON
    console = Console()
except ImportError:
    console = None

# Constants
EMBED_DIM = 768
COLLECTION_NAME = "mem0_nomic_768"
LOCAL_DB_PATH = "memory/long_term_memory.db"

class MemoryService:
    """
    Unified Memory Service handling both Mem0 AI memory and local SQLite fallback.
    Singleton pattern ensures single connection management.
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MemoryService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.mem0_client = None
        self.mem0_enabled = os.getenv("LONGTERM_MEM0", "true").lower() == "true"
        self.local_db_path = LOCAL_DB_PATH
        
        # Initialize systems
        self._init_local_storage()
        if self.mem0_enabled:
            self._init_mem0()
            
        self._initialized = True

    def _init_mem0(self):
        """Initialize Mem0 with specific configuration."""
        try:
            # 1. Configure Mem0 with all options
            config = {
                "version": "v1.1",
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "collection_name": COLLECTION_NAME,
                        "host": "localhost",
                        "port": 6333,
                        "embedding_model_dims": EMBED_DIM,
                    }
                },
                "llm": {
                    "provider": "langchain",
                    "config": {
                        "model": get_memory_llm()
                    }
                },
                "embedder": {
                    "provider": "langchain",
                    "config": {
                        "model": OllamaEmbeddings(model="nomic-embed-text")
                    }
                }
            }
            
            self.mem0_client = Memory.from_config(config)
            if console:
                console.log("[green]✅ Mem0 client initialized successfully[/green]")
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            if console:
                console.log(f"[red]❌ Failed to initialize Mem0: {e}[/red]")
            self.mem0_enabled = False

    def _init_local_storage(self):
        """Initialize local SQLite storage for fallback."""
        os.makedirs(os.path.dirname(self.local_db_path), exist_ok=True)
        with sqlite3.connect(self.local_db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    memory_type TEXT DEFAULT 'conversation',
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    chunk_text TEXT NOT NULL,
                    chunk_hash TEXT UNIQUE,
                    session_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_memories ON memories(user_id)")

    # ============================================
    # Public API Methods
    # ============================================

    def search_memories(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search relevant memories from Mem0 or fallback."""
        results = []
        
        # Try Mem0 first
        if self.mem0_enabled and self.mem0_client:
            try:
                mem_results = self.mem0_client.search(
                    query=query,
                    user_id=str(user_id),
                    limit=limit
                )
                
                # Normalize results
                hits = self._extract_list(mem_results)
                for hit in hits:
                    results.append({
                        "content": hit.get("memory", ""),
                        "score": hit.get("score", 0),
                        "source": "mem0",
                        "metadata": hit.get("metadata", {}),
                        "id": hit.get("id"),
                        "created_at": hit.get("created_at")
                    })
                    
                if console and results:
                    self._log_mem0_search(f"🔎 Mem0 Search: {query}", mem_results)
                    
            except Exception as e:
                logger.error(f"Mem0 search failed: {e}")
                if console:
                    console.log(f"[yellow]⚠️ Mem0 search failed: {e}[/yellow]")

        # Fallback to local if empty
        if not results:
            results = self._search_local_storage(user_id, query, limit)

        return results[:limit]

    def add_memory(self, user_id: str, messages: List[Dict[str, Any]], metadata: Optional[Dict] = None) -> bool:
        """Add conversation to memory."""
        if not messages:
            return False

        success = False
        
        # 1. Try Mem0
        if self.mem0_enabled and self.mem0_client:
            try:
                self.mem0_client.add(
                    messages=messages,
                    user_id=str(user_id),
                    metadata=metadata or {},
                    infer=True  # Auto-extract facts
                )
                success = True
                if console:
                    console.log(f"[green]✅ Memory stored in Mem0 for user {user_id}[/green]")
            except Exception as e:
                logger.error(f"Mem0 add failed: {e}")
                if console:
                    console.log(f"[red]❌ Mem0 add failed: {e}[/red]")

        # 2. Always backup to local storage
        try:
            text = "\n".join([f"{m.get('role')}: {m.get('content')}" for m in messages])
            self._add_to_local_storage(str(user_id), text, metadata)
            if not success: # If Mem0 failed, at least we have local
                success = True
        except Exception as e:
            logger.error(f"Local storage failed: {e}")

        return success

    def list_memories(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """List all memories for a user."""
        if self.mem0_enabled and self.mem0_client:
            try:
                raw = self.mem0_client.get_all(user_id=str(user_id))
                return [self._pretty_mem_row(x) for x in self._extract_list(raw)][:limit]
            except Exception as e:
                logger.error(f"Mem0 list failed: {e}")
        
        return self._list_local_memories(user_id, limit)

    def add_manual_memory(self, user_id: str, content: str, memory_type: str = "note", metadata: Optional[Dict] = None) -> bool:
        """Add a manual note/fact."""
        meta = metadata or {}
        meta["memory_type"] = memory_type
        
        # Try Mem0
        if self.mem0_enabled and self.mem0_client:
            try:
                self.mem0_client.add(
                    [{"role": "user", "content": content}],
                    user_id=str(user_id),
                    metadata=meta
                )
                return True
            except Exception as e:
                logger.error(f"Mem0 manual add failed: {e}")

        # Fallback
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                conn.execute(
                    "INSERT INTO memories (user_id, content, memory_type, metadata) VALUES (?, ?, ?, ?)",
                    (str(user_id), content, memory_type, json.dumps(meta))
                )
            return True
        except Exception as e:
            logger.error(f"Local manual add failed: {e}")
            return False

    def stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics."""
        stats = {"mem0_enabled": self.mem0_enabled}
        
        if self.mem0_enabled and self.mem0_client:
            try:
                mems = self.mem0_client.get_all(user_id=str(user_id))
                stats["mem0_count"] = len(self._extract_list(mems))
            except:
                stats["mem0_count"] = -1
                
        with sqlite3.connect(self.local_db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM memories WHERE user_id = ?", (str(user_id),))
            stats["local_count"] = cursor.fetchone()[0]
            
        return stats

    # ============================================
    # Helper Methods
    # ============================================

    def _extract_list(self, value: Any) -> List[Dict[str, Any]]:
        if value is None: return []
        if isinstance(value, list): return value
        if isinstance(value, dict):
            return value.get("results", value.get("data", [value]))
        return [value]

    def _pretty_mem_row(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": item.get("id") or item.get("_id"),
            "memory": item.get("memory") or item.get("text") or item.get("content"),
            "created_at": item.get("created_at"),
            "metadata": item.get("metadata", {})
        }

    def _log_mem0_search(self, title: str, results: Any):
        if not console: return
        rows = [self._pretty_mem_row(x) for x in self._extract_list(results)]
        console.print(Panel(JSON.from_data(rows), title=title))

    def _add_to_local_storage(self, user_id: str, text: str, metadata: Optional[Dict]):
        with sqlite3.connect(self.local_db_path) as conn:
            chunk_hash = hashlib.md5(text.encode()).hexdigest()
            conn.execute("""
                INSERT OR REPLACE INTO conversation_chunks 
                (user_id, chunk_text, chunk_hash, metadata)
                VALUES (?, ?, ?, ?)
            """, (user_id, text, chunk_hash, json.dumps(metadata or {})))

    def _search_local_storage(self, user_id: str, query: str, limit: int) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.local_db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT chunk_text, metadata FROM conversation_chunks WHERE user_id = ? AND chunk_text LIKE ? LIMIT ?",
                (user_id, f"%{query}%", limit)
            )
            return [{
                "content": row["chunk_text"],
                "source": "local",
                "metadata": json.loads(row["metadata"] or "{}")
            } for row in cursor]

    def _list_local_memories(self, user_id: str, limit: int) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.local_db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM memories WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            )
            return [dict(row) for row in cursor]

    # Compatibility methods for router
    def store_conversation_turn(self, user_id: str, user_text: str, assistant_text: str, metadata: Optional[Dict] = None) -> bool:
        return self.add_memory(
            user_id, 
            [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": assistant_text}
            ],
            metadata
        )

# Singleton accessor
def get_memory_service() -> MemoryService:
    return MemoryService()
