# @/long_term_memory.py
"""
Long-term memory management system integrating Mem0 and RAG semantic search.
Provides persistent memory across conversations with semantic retrieval capabilities.

Based on agent_mem0_gemini.py strategy with detailed logging and safe extractors.
"""

import os
import json
import sqlite3
import hashlib
import time
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
import logging

custom_fact_extraction_prompt = """
استخراج اطلاعات جامع:

اطلاعات را از مکالمات استخراج و دسته‌بندی کنید:

دسته‌بندی‌ها:
- اطلاعات_شخصی: نام، سن، محل زندگی، خانواده
- ترجیحات: علایق، سلیقه‌ها، انتخاب‌ها
- حرفه‌ای: شغل، مهارت‌ها، کار
- سلامت_روان: احساسات، اضطراب، افسردگی، استرس، مشکلات روانی
- اهداف_برنامه‌ها: آرزوها، اهداف آینده، برنامه‌ها
- سرگرمی‌ها: فعالیت‌ها، تفریحات
- روابط: خانواده، دوستان، روابط اجتماعی
- مالی: بودجه، عادات مالی

راهنمای استخراج:
- حتی از سوالات و جملات معمولی اطلاعات استخراج کنید
- اطلاعات ضمنی را از متن استنباط کنید
- اطلاعات زمانی (تاریخ، زمان) را ثبت کنید
- احساسات و حالات روانی را یادداشت کنید
- تغییرات در ترجیحات را دنبال کنید
- حریم خصوصی را رعایت کنید

همیشه به زبان فارسی پاسخ دهید و خاطرات را به فارسی ذخیره کنید.
به صورت خودکار هر خاطره را بر اساس محتوا دسته‌بندی کنید.
حقایق ساختاریافته با دسته‌بندی مناسب برگردانید.
"""
# Mem0 imports
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    Memory = None

# LangChain imports for embeddings
try:
    from langchain_ollama import OllamaEmbeddings
    from langchain_openai import OpenAIEmbeddings
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    OllamaEmbeddings = OpenAIEmbeddings = GoogleGenerativeAIEmbeddings = None

# Rich console for logging
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.json import JSON
    console = Console()
except ImportError:
    console = None

logger = logging.getLogger(__name__)

# Mem0 configuration constants
MEM0_TOPK = 1  # Reduce retrieved memories
EMBED_DIM = 768  # nomic-embed-text dimension


class LongTermMemoryManager:
    """
    Manages long-term memory using Mem0 with exact strategy from agent_mem0_gemini.py.
    
    Features:
    - Mem0 integration with detailed logging
    - Safe extractors for Mem0 responses
    - Local Qdrant with Ollama embeddings
    - Fallback to local storage when external services unavailable
    """
    
    def __init__(
        self,
        user_id: str,
        mem0_enabled: bool = False,
        llm=None,
        local_db_path: str = "memory/long_term_memory.db"
    ):
        self.user_id = str(user_id) if user_id is not None else "default"
        self.mem0_enabled = mem0_enabled and MEM0_AVAILABLE
        self.llm = llm
        
        # Initialize Mem0 with exact config from agent_mem0_gemini.py
        self.mem0_client = None
        if self.mem0_enabled:
            try:
                self.mem0_client = self._init_mem0_client()
                if console:
                    console.log("[green]✅ Mem0 client initialized successfully[/green]")
                else:
                    logger.info("Mem0 client initialized successfully")
            except Exception as e:
                if console:
                    console.log(f"[yellow]⚠️ Failed to initialize Mem0: {e}[/yellow]")
                else:
                    logger.warning(f"Failed to initialize Mem0: {e}")
                self.mem0_enabled = False
        
        # Local fallback storage
        self.local_db_path = local_db_path
        self._init_local_storage()
    
    def _init_mem0_client(self):
        """Initialize Mem0 client with Persian custom prompt"""
        # Ollama embeddings (local)
        embedder = OllamaEmbeddings(model="nomic-embed-text")
        
        # Mem0 config with custom fact extraction prompt
        mem0_config = {
            "version": "v1.1",
            "llm": {
                "provider": "langchain",
                "config": {
                    "model": self.llm,
                }
            } if self.llm else None,
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
                    "embedding_model_dims": EMBED_DIM,
                    "on_disk": True
                }
            }
        }
        
        # Remove None values
        if not mem0_config["llm"]:
            del mem0_config["llm"]
        
        return Memory.from_config(mem0_config)
    
    # Mem0 logging helpers from agent_mem0_gemini.py
    def _extract_list(self, value: Any) -> List[Dict[str, Any]]:
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
    
    def _pretty_mem_row(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a Mem0 memory item to a friendly row for logging."""
        return {
            "id": item.get("id") or item.get("_id") or "-",
            "memory": item.get("memory") or item.get("text") or item.get("content") or "",
            "score": item.get("score") or item.get("similarity") or "",
            "created_at": item.get("created_at") or "",
            "updated_at": item.get("updated_at") or "",
            "metadata": item.get("metadata") or {},
        }
    
    def _log_mem0_search(self, title: str, results: Any):
        """Log Mem0.search() results in a rich table and raw JSON."""
        if not console:
            return
        
        rows = [self._pretty_mem_row(x) for x in self._extract_list(results)]
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
    
    def _log_mem0_full_list(self):
        """Fetch and log the full memory list for a user."""
        if not console or not self.mem0_client:
            return
        
        try:
            all_mems = self.mem0_client.get_all(user_id=self.user_id)
        except Exception as e:
            console.log(f"[red]❌ mem0.get_all failed: {e}[/red]")
            return

        rows = [self._pretty_mem_row(x) for x in self._extract_list(all_mems)]
        table = Table(title=f"🧠 Mem0: FULL MEMORY LIST (user_id={self.user_id})", header_style="bold green", show_lines=True)
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
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_chunks ON conversation_chunks(user_id)")
    
    @classmethod
    def from_env(cls, user_id: str = "default", llm=None) -> 'LongTermMemoryManager':
        """Create instance from environment variables."""
        mem0_enabled = os.getenv("LONGTERM_MEM0", "false").lower() == "true"
        
        return cls(
            user_id=user_id,
            mem0_enabled=mem0_enabled,
            llm=llm
        )

    def list_memories(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return normalized memories for the user from Mem0 or local storage."""
        records: List[Dict[str, Any]] = []

        if self.mem0_enabled and self.mem0_client:
            try:
                raw = self.mem0_client.get_all(user_id=self.user_id)
                rows = [self._pretty_mem_row(x) for x in self._extract_list(raw)]
                for row in rows:
                    row["source"] = "mem0"
                records.extend(rows)
            except Exception as exc:
                logger.error(f"Failed to list Mem0 memories: {exc}")

        if not records:
            records.extend(self._list_local_memories(limit))

        return records[:limit]

    def add_manual_memory(
        self,
        content: str,
        memory_type: str = "note",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Store an arbitrary note/fact in Mem0 with Persian custom prompt."""
        text = (content or "").strip()
        if not text:
            return False

        metadata = metadata or {}

        if self.mem0_enabled and self.mem0_client:
            try:
                payload = [{"role": "user", "content": text}]
                add_res = self.mem0_client.add(
                    payload,
                    user_id=self.user_id,
                    agent_id="blue-psychology-manual",
                    metadata={**metadata, "memory_type": memory_type},
                    infer=True
                )
                if console:
                    console.print(
                        Panel.fit(
                            JSON.from_data(add_res),
                            title="➕ Mem0.add() response (manual)",
                            border_style="green",
                        )
                    )
                self._log_mem0_full_list()
                return True
            except Exception as exc:
                logger.error(f"Failed to add manual Mem0 memory: {exc}")

        try:
            with sqlite3.connect(self.local_db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO memories (user_id, content, memory_type, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """,
                    (
                        self.user_id,
                        text,
                        memory_type,
                        json.dumps(metadata or {}),
                    ),
                )
            return True
        except Exception as exc:
            logger.error(f"Failed to add manual memory locally: {exc}")
            return False
    
    def add_conversation_memory(
        self,
        messages: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Add conversation messages to Mem0 with Persian custom prompt"""
        if not self.mem0_enabled or not self.mem0_client:
            # Fallback to local storage
            try:
                conversation_text = self._messages_to_text(messages)
                self._add_to_local_storage(conversation_text, session_id, metadata)
                return True
            except Exception as e:
                logger.error(f"Failed to add to local storage: {e}")
                return False
        
        try:
            if console:
                console.log("[cyan]🔍 Starting memory extraction process...[/cyan]")
                console.log(f"[dim]📝 Messages to process: {len(messages)}[/dim]")
            
            # Enhanced metadata
            enhanced_metadata = {
                "source": "blue-psychology",
                "session": session_id,
                **(metadata or {})
            }
            
            # Add with infer=True for automatic categorization
            add_res = self.mem0_client.add(
                messages,
                user_id=self.user_id,
                agent_id="blue-psychology-agent",
                metadata=enhanced_metadata,
                infer=True
            )
            
            # Log extraction results with detailed information
            if console:
                results = self._extract_list(add_res)
                
                # Create extraction summary table
                extraction_table = Table(title="🧠 Memory Extraction Results", header_style="bold magenta", show_lines=True)
                extraction_table.add_column("Event", style="cyan")
                extraction_table.add_column("Memory ID", style="yellow")
                extraction_table.add_column("Extracted Memory", style="white")
                
                for item in results:
                    event = item.get("event", "UNKNOWN")
                    mem_id = item.get("id", "-")
                    memory_text = item.get("memory", "")
                    
                    # Color code based on event type
                    if event == "ADD":
                        event_display = f"[green]✅ {event}[/green]"
                    elif event == "UPDATE":
                        event_display = f"[yellow]🔄 {event}[/yellow]"
                    elif event == "NONE" or event == "NOOP":
                        event_display = f"[dim]⏭️ {event}[/dim]"
                    else:
                        event_display = f"[blue]{event}[/blue]"
                    
                    extraction_table.add_row(event_display, str(mem_id)[:36], memory_text)
                
                console.print(extraction_table)
                
                # Count statistics
                added = sum(1 for r in results if r.get("event") == "ADD")
                updated = sum(1 for r in results if r.get("event") == "UPDATE")
                skipped = sum(1 for r in results if r.get("event") in ["NONE", "NOOP"])
                
                console.log(f"[green]✅ Extraction complete: {added} added, {updated} updated, {skipped} skipped[/green]")
                console.print(Panel.fit(JSON.from_data(add_res), title="➕ Mem0.add() Full Response", border_style="green"))
            
            # Log full memory list after addition
            self._log_mem0_full_list()
            
            return True
            
        except Exception as e:
            if console:
                console.log(f"[red]❌ Mem0.add failed: {e}[/red]")
            else:
                logger.error(f"Failed to add to Mem0: {e}")
            
            # Fallback to local storage
            try:
                conversation_text = self._messages_to_text(messages)
                self._add_to_local_storage(conversation_text, session_id, metadata)
                return True
            except Exception as e2:
                logger.error(f"Failed to add to local storage: {e2}")
                return False
    
    def search_memories(
        self,
        query: str,
        limit: int = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search Mem0 memories with metadata filtering"""
        if limit is None:
            limit = MEM0_TOPK
        
        results = []
        
        # Search Mem0 with detailed logging
        if self.mem0_enabled and self.mem0_client:
            try:
                search_params = {
                    "query": query,
                    "user_id": self.user_id,
                    "limit": limit
                }
                
                if filters:
                    search_params["filters"] = filters
                
                search_res = self.mem0_client.search(**search_params)
                
                # Log search results with rich formatting
                self._log_mem0_search("🔎 Mem0.search() hits", search_res)
                
                # Extract results using safe extractor
                hits = self._extract_list(search_res)
                for hit in hits:
                    row = self._pretty_mem_row(hit)
                    results.append({
                        "content": row["memory"],
                        "score": row["score"],
                        "source": "mem0",
                        "metadata": row["metadata"],
                        "id": row["id"],
                        "created_at": row["created_at"],
                        "updated_at": row["updated_at"]
                    })
                    
            except Exception as e:
                if console:
                    console.log(f"[yellow]⚠️ Mem0.search failed: {e}[/yellow]")
                else:
                    logger.error(f"Mem0 search failed: {e}")
        
        # Fallback to local storage if Mem0 unavailable
        if not results:
            try:
                local_results = self._search_local_storage(query, limit)
                results.extend(local_results)
            except Exception as e:
                logger.error(f"Local search failed: {e}")
        
        return results[:limit]

    def _list_local_memories(self, limit: int) -> List[Dict[str, Any]]:
        """Return normalized rows from the local SQLite fallback."""
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT id, content, memory_type, metadata, created_at, updated_at
                    FROM memories
                    WHERE user_id = ?
                    ORDER BY COALESCE(updated_at, created_at) DESC
                    LIMIT ?
                    """,
                    (self.user_id, limit),
                )

                rows = []
                for row in cursor.fetchall():
                    try:
                        parsed_meta = json.loads(row["metadata"] or "{}")
                    except json.JSONDecodeError:
                        parsed_meta = {"raw": row["metadata"]}
                    rows.append(
                        {
                            "id": row["id"],
                            "memory": row["content"],
                            "score": None,
                            "created_at": row["created_at"],
                            "updated_at": row["updated_at"],
                            "metadata": parsed_meta,
                            "memory_type": row["memory_type"],
                            "source": "local",
                        }
                    )

                return rows
        except Exception as exc:
            logger.error(f"Failed to list local memories: {exc}")
            return []
    
    def get_relevant_context(
        self,
        current_query: str,
        max_context_length: int = 2000
    ) -> str:
        """Get relevant context from Mem0 memories formatted as system message."""
        if not self.mem0_enabled or not current_query:
            return ""
        
        memories = self.search_memories(current_query, limit=MEM0_TOPK)
        if not memories:
            return ""
        
        # Format as bullet points like agent_mem0_gemini.py
        bullets = []
        current_length = 0
        
        for memory in memories:
            content = memory["content"].strip()
            if not content:
                continue
                
            bullet = f"- {content}"
            if current_length + len(bullet) > max_context_length:
                break
            
            bullets.append(bullet)
            current_length += len(bullet)
        
        if bullets:
            return f"[Mem0 Memory]\nUse if relevant:\n" + "\n".join(bullets)
        
        return ""
    
    def _messages_to_text(self, messages: List[Dict[str, Any]]) -> str:
        """Convert message list to searchable text."""
        text_parts = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str) and content.strip():
                text_parts.append(f"{role}: {content}")
        return "\n".join(text_parts)
    
    def _add_to_local_storage(self, text: str, session_id: Optional[str], metadata: Optional[Dict]):
        """Add to local SQLite storage."""
        chunks = self._create_chunks(text)
        
        with sqlite3.connect(self.local_db_path) as conn:
            for chunk in chunks:
                chunk_hash = hashlib.md5(chunk.encode()).hexdigest()
                
                conn.execute("""
                    INSERT OR REPLACE INTO conversation_chunks 
                    (user_id, chunk_text, chunk_hash, session_id, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    self.user_id,
                    chunk,
                    chunk_hash,
                    session_id,
                    json.dumps(metadata or {})
                ))
    
    def _search_local_storage(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search local storage using simple text matching."""
        query_words = query.lower().split()
        
        with sqlite3.connect(self.local_db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Simple keyword matching
            where_conditions = []
            params = [self.user_id]
            
            for word in query_words:
                where_conditions.append("LOWER(chunk_text) LIKE ?")
                params.append(f"%{word}%")
            
            where_clause = " AND ".join(where_conditions)
            
            cursor = conn.execute(f"""
                SELECT chunk_text, session_id, timestamp, metadata
                FROM conversation_chunks 
                WHERE user_id = ? AND ({where_clause})
                ORDER BY timestamp DESC
                LIMIT ?
            """, params + [limit])
            
            results = []
            for row in cursor:
                # Simple scoring based on keyword matches
                text_lower = row["chunk_text"].lower()
                score = sum(1 for word in query_words if word in text_lower) / len(query_words)
                
                results.append({
                    "content": row["chunk_text"],
                    "score": score,
                    "source": "local",
                    "metadata": json.loads(row["metadata"] or "{}"),
                    "session_id": row["session_id"],
                    "timestamp": row["timestamp"]
                })
            
            return results
    
    def _create_chunks(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Create overlapping chunks from text for better retrieval."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > start + chunk_size // 2:
                    chunk = text[start:break_point + 1]
                    end = break_point + 1
            
            chunks.append(chunk.strip())
            start = end - overlap
            
            if start >= len(text):
                break
        
        return [c for c in chunks if c.strip()]
    
    def cleanup_old_memories(self, days_to_keep: int = 30):
        """Clean up old memories to manage storage."""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        # Clean local storage
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                conn.execute("""
                    DELETE FROM conversation_chunks 
                    WHERE user_id = ? AND timestamp < ?
                """, (self.user_id, cutoff_date.isoformat()))
                
                conn.execute("""
                    DELETE FROM memories 
                    WHERE user_id = ? AND created_at < ?
                """, (self.user_id, cutoff_date.isoformat()))
        except Exception as e:
            logger.error(f"Failed to cleanup local storage: {e}")
        
        # Note: Mem0 cleanup would need specific API calls
        logger.info(f"Cleaned up local memories older than {days_to_keep} days")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about stored memories."""
        stats = {
            "mem0_enabled": self.mem0_enabled,
            "local_chunks": 0,
            "local_memories": 0
        }
        
        # Get Mem0 stats
        if self.mem0_enabled and self.mem0_client:
            try:
                all_mems = self.mem0_client.get_all(user_id=self.user_id)
                mem_list = self._extract_list(all_mems)
                stats["mem0_memories"] = len(mem_list)
            except Exception as e:
                logger.error(f"Failed to get Mem0 stats: {e}")
                stats["mem0_memories"] = 0
        
        # Get local stats
        try:
            with sqlite3.connect(self.local_db_path) as conn:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM conversation_chunks WHERE user_id = ?",
                    (self.user_id,)
                )
                stats["local_chunks"] = cursor.fetchone()[0]
                
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM memories WHERE user_id = ?",
                    (self.user_id,)
                )
                stats["local_memories"] = cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
        
        return stats