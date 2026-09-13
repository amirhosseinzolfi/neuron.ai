"""
Brain Router
----------------------------------------------------------------------
FastAPI router for user brain inspection, memory retrieval, and synchronization.
Prefix: /brain
"""

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

from app.services.brain_service import get_brain_service

router = APIRouter(prefix="/brain", tags=["User Brain"])


class SyncMemoryRequest(BaseModel):
    user_text: str = Field(..., description="User's input text")
    assistant_text: str = Field(..., description="Assistant's response text")
    source: str = Field(default="api", description="Source or agent identifier")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional extra metadata")


@router.get("/{user_id}", summary="Get Full Brain Snapshot")
async def get_user_brain(
    user_id: str,
    query: Optional[str] = Query(None, description="Optional semantic query for vector memory retrieval"),
    memory_limit: int = Query(5, ge=1, le=50, description="Max number of memories to fetch")
):
    """
    Retrieve the consolidated brain snapshot of a user:
    - Demographic and psychological profile
    - Psychological test history and results
    - Vector episodic/semantic memories (Mem0)
    - Tasks and reminders
    """
    try:
        service = get_brain_service()
        snapshot = service.get_user_brain_snapshot(user_id=user_id, query=query, memory_limit=memory_limit)
        return {
            "success": True,
            "user_id": user_id,
            "data": snapshot
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving brain snapshot: {str(e)}")


@router.get("/{user_id}/profile", summary="Get User Profile & Psychometrics")
async def get_user_profile(user_id: str):
    """
    Retrieve only profile and psychological metadata of a user.
    """
    try:
        service = get_brain_service()
        snapshot = service.get_user_brain_snapshot(user_id=user_id, memory_limit=1)
        return {
            "success": True,
            "user_id": user_id,
            "profile": snapshot.get("profile", {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user profile: {str(e)}")


@router.get("/{user_id}/memories", summary="Get Long-Term Vector Memories")
async def get_user_memories(
    user_id: str,
    query: Optional[str] = Query(None, description="Semantic search query"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Retrieve or search episodic/semantic long-term memories for a user.
    """
    try:
        service = get_brain_service()
        snapshot = service.get_user_brain_snapshot(user_id=user_id, query=query, memory_limit=limit)
        return {
            "success": True,
            "user_id": user_id,
            "query": query,
            "memories": snapshot.get("long_term_memories", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving memories: {str(e)}")


@router.get("/{user_id}/tests", summary="Get Psychology Test History")
async def get_user_tests(user_id: str):
    """
    Retrieve psychological test results and analyses for a user.
    """
    try:
        service = get_brain_service()
        snapshot = service.get_user_brain_snapshot(user_id=user_id, memory_limit=1)
        return {
            "success": True,
            "user_id": user_id,
            "tests": snapshot.get("psychology_tests", []),
            "packages": snapshot.get("packages", [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tests: {str(e)}")


@router.get("/{user_id}/context-prompt", summary="Get Brain Context Prompt")
async def get_brain_context_prompt(
    user_id: str,
    query: Optional[str] = Query(None, description="Optional query for memory context")
):
    """
    Get the formatted Markdown prompt representation of the user's brain state,
    used for LLM and Agent prompt injection.
    """
    try:
        service = get_brain_service()
        snapshot = service.get_user_brain_snapshot(user_id=user_id, query=query)
        prompt_text = service.build_brain_context_prompt(snapshot)
        return {
            "success": True,
            "user_id": user_id,
            "context_prompt": prompt_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building brain prompt: {str(e)}")


@router.post("/{user_id}/sync-memory", summary="Sync Conversation to Brain Memory")
async def sync_brain_memory(user_id: str, request: SyncMemoryRequest):
    """
    Ingest an interaction into the user's long-term memory in background.
    """
    try:
        service = get_brain_service()
        service.sync_memory(
            user_id=user_id,
            user_text=request.user_text,
            assistant_text=request.assistant_text,
            source=request.source,
            metadata=request.metadata
        )
        return {
            "success": True,
            "message": f"Memory synchronization initiated for user {user_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating memory sync: {str(e)}")

