from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.memory_service import MemoryService, get_memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    limit: int = Field(3, ge=1, le=20, description="Maximum number of hits")


class StoreTurnRequest(BaseModel):
    user_text: str = Field(..., min_length=1, description="User message content")
    assistant_text: str = Field(..., min_length=1, description="Assistant reply content")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata to persist")


class ManualMemoryRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Fact or note to store")
    memory_type: str = Field(default="note", max_length=32, description="Categorization label")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata payload")


@router.get("/{user_id}")
async def list_user_memories(
    user_id: str,
    limit: int = Query(50, ge=1, le=500, description="Maximum rows to return"),
    service: MemoryService = Depends(get_memory_service),
):
    """Return normalized memories for a specific user."""
    try:
        memories = service.list_memories(user_id, limit=limit)
        return {
            "success": True,
            "user_id": user_id,
            "count": len(memories),
            "memories": memories,
        }
    except Exception as exc:  # pragma: no cover - surfaced via HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to fetch memories: {exc}") from exc


@router.get("/{user_id}/stats")
async def memory_stats(
    user_id: str,
    service: MemoryService = Depends(get_memory_service),
):
    """Return storage statistics for the user's memories."""
    try:
        return {
            "success": True,
            "user_id": user_id,
            "stats": service.stats(user_id),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {exc}") from exc


@router.post("/{user_id}/search")
async def search_user_memories(
    user_id: str,
    request: SearchRequest,
    service: MemoryService = Depends(get_memory_service),
):
    """Semantic search over a user's long-term memories."""
    try:
        memories = service.search_memories(user_id, query=request.query, limit=request.limit)
        return {
            "success": True,
            "user_id": user_id,
            "count": len(memories),
            "memories": memories,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc


@router.post("/{user_id}/store")
async def store_conversation_turn(
    user_id: str,
    request: StoreTurnRequest,
    service: MemoryService = Depends(get_memory_service),
):
    """Manually persist a conversation turn (user + assistant)."""
    try:
        stored = service.store_conversation_turn(
            user_id,
            request.user_text,
            request.assistant_text,
            metadata=request.metadata,
        )
        return {"success": stored, "user_id": user_id}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {exc}") from exc


@router.post("/{user_id}/notes")
async def add_manual_memory(
    user_id: str,
    request: ManualMemoryRequest,
    service: MemoryService = Depends(get_memory_service),
):
    """Persist a free-form note/fact for the user."""
    try:
        stored = service.add_manual_memory(
            user_id,
            content=request.content,
            metadata=request.metadata,
            memory_type=request.memory_type,
        )
        if not stored:
            raise HTTPException(status_code=500, detail="Memory could not be stored")
        return {"success": True, "user_id": user_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to store note: {exc}") from exc
