"""High-level memory service that exposes Mem0/SQLite functionality to FastAPI routers.

The service wraps :class:`LongTermMemoryManager` to provide a thread-safe, reusable
interface for listing, searching, and storing long-term memories per user.
"""

from __future__ import annotations

from threading import Lock
from typing import Any, Dict, List, Optional

from ai_utils import get_neuron_llm
from app.chat.long_term_memory import LongTermMemoryManager


class MemoryService:
    """Stateful helper that caches a memory manager per user."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._llm = None
        self._managers: Dict[str, LongTermMemoryManager] = {}

    def _get_llm(self):
        if self._llm is None:
            self._llm = get_neuron_llm()
        return self._llm

    def _get_manager(self, user_id: str) -> LongTermMemoryManager:
        safe_user_id = str(user_id or "anonymous")
        with self._lock:
            manager = self._managers.get(safe_user_id)
            if manager is None:
                manager = LongTermMemoryManager.from_env(
                    user_id=safe_user_id,
                    llm=self._get_llm(),
                )
                self._managers[safe_user_id] = manager
            return manager

    def list_memories(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self._get_manager(user_id).list_memories(limit=limit)

    def search_memories(self, user_id: str, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []
        return self._get_manager(user_id).search_memories(query=query, limit=limit)

    def store_conversation_turn(
        self,
        user_id: str,
        user_text: str,
        assistant_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        user_text = (user_text or "").strip()
        assistant_text = (assistant_text or "").strip()
        if not user_text or not assistant_text:
            raise ValueError("Both user_text and assistant_text are required.")

        interaction = [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": assistant_text},
        ]

        return self._get_manager(user_id).add_conversation_memory(
            messages=interaction,
            session_id=str(user_id or "anonymous"),
            metadata=metadata,
        )

    def add_manual_memory(
        self,
        user_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        memory_type: str = "note",
    ) -> bool:
        return self._get_manager(user_id).add_manual_memory(
            content=content,
            memory_type=memory_type,
            metadata=metadata,
        )

    def stats(self, user_id: str) -> Dict[str, Any]:
        return self._get_manager(user_id).get_memory_stats()


_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """Singleton accessor used by FastAPI dependency injection."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
