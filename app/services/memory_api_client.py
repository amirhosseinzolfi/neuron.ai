"""HTTP client wrapper for the centralized FastAPI memory endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx


class MemoryApiClient:
    """Minimal REST client for `/memory` endpoints."""

    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        if not base_url:
            raise ValueError("base_url is required for MemoryApiClient")
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    def search(self, user_id: str, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Return semantic memory hits for a user."""
        response = self._client.post(
            f"{self.base_url}/memory/{user_id}/search",
            json={"query": query, "limit": limit},
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("memories", [])

    def store_turn(
        self,
        user_id: str,
        user_text: str,
        assistant_text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Persist a conversation turn (user + assistant)."""
        response = self._client.post(
            f"{self.base_url}/memory/{user_id}/store",
            json={
                "user_text": user_text,
                "assistant_text": assistant_text,
                "metadata": metadata or {},
            },
        )
        response.raise_for_status()
        payload = response.json()
        return bool(payload.get("success"))

    def get_context_with_details(
        self,
        user_id: str,
        query: str,
        limit: int = 3,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Return a formatted context string and the raw memory documents."""
        memories = self.search(user_id, query, limit)
        context = self._format(memories)
        return context, memories

    def get_formatted_context(self, user_id: str, query: str, limit: int = 3) -> str:
        context, _ = self.get_context_with_details(user_id, query, limit)
        return context

    @staticmethod
    def _format(memories: List[Dict[str, Any]]) -> str:
        if not memories:
            return ""

        bullets: List[str] = []
        for mem in memories:
            content = (mem.get("content") or mem.get("memory") or "").strip()
            if content:
                bullets.append(f"- {content}")

        if bullets:
            return "[Mem0 Memory]\nUse if relevant:\n" + "\n".join(bullets)
        return ""
