"""
Agents Router
----------------------------------------------------------------------
Unified FastAPI router for listing, invoking, streaming, and inspecting
modular agents in Neuron.
Prefix: /agents
"""

import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.registry import AgentRegistry
from app.services.brain_service import get_brain_service
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

router = APIRouter(prefix="/agents", tags=["Agents"])

# Async checkpointer singleton
CHECKPOINT_DB_PATH = "database/psychology_bot.db"
_async_checkpointer: Optional[AsyncSqliteSaver] = None
_conn: Optional[aiosqlite.Connection] = None

async def get_async_checkpointer() -> AsyncSqliteSaver:
    global _async_checkpointer, _conn
    if _async_checkpointer is None:
        _conn = await aiosqlite.connect(CHECKPOINT_DB_PATH)
        _async_checkpointer = AsyncSqliteSaver(conn=_conn)
        await _async_checkpointer.setup()
    return _async_checkpointer


# ── Pydantic Request Models ──────────────────────────────────────────

class AgentChatRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    chat_id: str = Field(..., description="Conversation thread identifier")
    message: str = Field(..., description="User message to the agent")


class SkillExecutionRequest(BaseModel):
    user_id: str = Field(..., description="Unique user identifier")
    input_text: str = Field(..., description="Input text to process with skill")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Optional extra parameters")


# ── Endpoints ─────────────────────────────────────────────────────────

@router.get("", summary="List All Agents")
@router.get("/", include_in_schema=False)
async def list_agents():
    """
    List all available agents registered in Neuron with their tools and skills.
    """
    agents = AgentRegistry.list_agents()
    return {
        "success": True,
        "count": len(agents),
        "agents": agents
    }


@router.get("/{agent_name}", summary="Get Agent Details")
async def get_agent_details(agent_name: str):
    """
    Get detailed capabilities, tools, and description of a specific agent.
    """
    agent = AgentRegistry.get(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found.")

    return {
        "success": True,
        "agent": {
            "name": agent.name,
            "display_name": agent.display_name,
            "description": agent.description,
            "version": agent.version,
            "tools": [
                {
                    "name": getattr(t, "name", str(t)),
                    "description": getattr(t, "description", "")
                }
                for t in agent.tools
            ],
            "skills": list(agent.skills.keys())
        }
    }


@router.post("/{agent_name}/chat", summary="Chat with Agent")
async def chat_with_agent(agent_name: str, request: AgentChatRequest):
    """
    Interact with an agent. Automatically injects user brain state
    (profile, test history, Mem0 vector memories) and records the turn.
    """
    agent = AgentRegistry.get(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found.")

    try:
        brain_service = get_brain_service()
        brain_snapshot = brain_service.get_user_brain_snapshot(
            user_id=request.user_id,
            query=request.message,
            memory_limit=5
        )

        checkpointer = await get_async_checkpointer()
        result = await agent.ainvoke(
            user_id=request.user_id,
            chat_id=request.chat_id,
            message=request.message,
            brain_snapshot=brain_snapshot,
            checkpointer=checkpointer
        )

        return {
            "success": True,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing agent '{agent_name}': {str(e)}")


@router.post("/{agent_name}/stream", summary="Stream Chat with Agent (SSE)")
async def stream_agent(agent_name: str, request: AgentChatRequest):
    """
    Stream token and tool execution events from the agent in real-time
    using Server-Sent Events (SSE).
    """
    agent = AgentRegistry.get(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found.")

    brain_service = get_brain_service()
    brain_snapshot = brain_service.get_user_brain_snapshot(
        user_id=request.user_id,
        query=request.message,
        memory_limit=5
    )

    checkpointer = await get_async_checkpointer()

    async def event_generator():
        try:
            async for event in agent.astream(
                user_id=request.user_id,
                chat_id=request.chat_id,
                message=request.message,
                brain_snapshot=brain_snapshot,
                checkpointer=checkpointer
            ):
                payload = json.dumps(event, ensure_ascii=False)
                yield f"data: {payload}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as err:
            err_payload = json.dumps({"type": "error", "error": str(err)}, ensure_ascii=False)
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{agent_name}/history/{user_id}", summary="Get Agent Conversation History")
async def get_agent_history(
    agent_name: str,
    user_id: str,
    chat_id: Optional[str] = Query(None, description="Optional thread id, defaults to user_id")
):
    """
    Retrieve checkpointed message history for a specific agent and user thread.
    """
    agent = AgentRegistry.get(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found.")

    try:
        checkpointer = await get_async_checkpointer()
        graph = agent.get_graph(checkpointer=checkpointer)
        thread_id = f"{user_id}:{agent_name}:{chat_id or user_id}"
        config = {"configurable": {"thread_id": thread_id}}

        state = await graph.aget_state(config)
        messages = state.values.get("messages", [])

        formatted_messages = []
        for m in messages:
            formatted_messages.append({
                "role": getattr(m, "type", m.__class__.__name__),
                "content": getattr(m, "content", str(m))
            })

        return {
            "success": True,
            "agent": agent_name,
            "user_id": user_id,
            "message_count": len(formatted_messages),
            "history": formatted_messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving history: {str(e)}")


@router.post("/{agent_name}/skills/{skill_name}", summary="Execute Agent Skill Directly")
async def execute_agent_skill(
    agent_name: str,
    skill_name: str,
    request: SkillExecutionRequest
):
    """
    Directly execute one of the agent's specialized AI skills with user context.
    """
    agent = AgentRegistry.get(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found.")

    skill_func = agent.skills.get(skill_name)
    if not skill_func or not callable(skill_func):
        raise HTTPException(
            status_code=404,
            detail=f"Skill '{skill_name}' not found for agent '{agent_name}'. Available skills: {list(agent.skills.keys())}"
        )

    try:
        brain_service = get_brain_service()
        snapshot = brain_service.get_user_brain_snapshot(user_id=request.user_id, memory_limit=1)
        user_profile = snapshot.get("profile", {})

        # Invoke skill
        result = skill_func(request.input_text, user_profile=user_profile)
        return {
            "success": True,
            "agent": agent_name,
            "skill": skill_name,
            "user_id": request.user_id,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing skill '{skill_name}': {str(e)}")

