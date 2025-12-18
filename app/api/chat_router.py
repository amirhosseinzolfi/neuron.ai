from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import sys
import os

# Ensure root directory is in path for imports if needed
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from app.chat.smart_chat import get_memory, get_chat_agent, chat

router = APIRouter(prefix="/chat", tags=["smart-chat"])
logger = logging.getLogger(__name__)

# Initialize smart chat components (lazy loaded)
_memory = None
_agent = None

def get_smart_chat_agent():
    """Lazy initialization of smart chat agent"""
    global _memory, _agent
    if _memory is None:
        _memory = get_memory()
    if _agent is None:
        _agent = get_chat_agent(_memory)
    return _agent

class ChatMessage(BaseModel):
    """Smart chat message"""
    user_id: str = Field(..., description="Unique user identifier")
    chat_id: str = Field(..., description="Unique identifier for conversation thread")
    input_text: str = Field(..., description="User message text")

@router.post("/send")
async def send_chat_message(message: ChatMessage):
    """
    Send message to smart AI chat therapist
    """
    try:
        agent = get_smart_chat_agent()
        
        # Send message and get response
        response = chat(agent, message.user_id, message.input_text, thread_id=message.chat_id)
        
        # Handle different response types
        if isinstance(response, dict):
            # Response has both raw and refined versions
            return {
                "success": True,
                "user_id": message.user_id,
                "response": response.get("refined", response.get("raw", "")),
                "raw_response": response.get("raw", "")
            }
        elif isinstance(response, str):
            # Simple string response
            return {
                "success": True,
                "user_id": message.user_id,
                "response": response
            }
        elif isinstance(response, list):
            # Conversation history returned (empty message case)
            return {
                "success": True,
                "user_id": message.user_id,
                "history": [
                    {
                        "role": msg.type if hasattr(msg, "type") else "unknown",
                        "content": msg.content if hasattr(msg, "content") else str(msg)
                    }
                    for msg in response
                ]
            }
        else:
            return {
                "success": True,
                "user_id": message.user_id,
                "response": str(response)
            }
    except Exception as e:
        logger.error(f"Error in chat for user {message.user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{user_id}")
async def get_chat_history(user_id: str):
    """
    Get conversation history for a user
    """
    try:
        agent = get_smart_chat_agent()
        
        # Get history by sending empty message
        history = chat(agent, user_id, "")
        
        if isinstance(history, list):
            return {
                "success": True,
                "user_id": user_id,
                "message_count": len(history),
                "history": [
                    {
                        "role": msg.type if hasattr(msg, "type") else "unknown",
                        "content": msg.content if hasattr(msg, "content") else str(msg)
                    }
                    for msg in history
                ]
            }
        else:
            return {
                "success": True,
                "user_id": user_id,
                "message_count": 0,
                "history": []
            }
    except Exception as e:
        logger.error(f"Error getting chat history for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))