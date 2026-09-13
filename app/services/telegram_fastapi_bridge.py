"""
Telegram - FastAPI Bridge
----------------------------------------------------------------------
Communicates between the Telegram bot and the FastAPI platform endpoints.
Connects Telegram UI to /agents and /brain.
Supports both HTTP network calls and seamless in-process FastAPI dispatch.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from fastapi.testclient import TestClient
from app.main import app

logger = logging.getLogger("telegram_fastapi_bridge")

FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:15800")
_in_process_client = TestClient(app)


class TelegramFastAPIBridge:
    """Client for Telegram bot handlers to communicate with FastAPI."""

    @classmethod
    def _request(cls, method: str, path: str, json_data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send request to FastAPI via HTTP, with in-process TestClient fallback."""
        url = f"{FASTAPI_BASE_URL}{path}"
        try:
            with httpx.Client(timeout=45.0) as client:
                if method.upper() == "GET":
                    resp = client.get(url, params=params)
                elif method.upper() == "POST":
                    resp = client.post(url, json=json_data, params=params)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"HTTP call to {url} returned status {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.info(f"HTTP call to {url} failed ({e}), falling back to in-process FastAPI TestClient...")

        # Fallback to in-process FastAPI application
        try:
            if method.upper() == "GET":
                resp = _in_process_client.get(path, params=params)
            else:
                resp = _in_process_client.post(path, json=json_data, params=params)
            if resp.status_code == 200:
                return resp.json()
            return {"success": False, "error": f"Status {resp.status_code}: {resp.text}"}
        except Exception as in_proc_err:
            logger.error(f"In-process FastAPI call to {path} failed: {in_proc_err}", exc_info=True)
            return {"success": False, "error": str(in_proc_err)}

    # ── Agents Endpoints ─────────────────────────────────────────────

    @classmethod
    def get_agents(cls) -> List[Dict[str, Any]]:
        """Retrieve list of registered agents from /agents."""
        res = cls._request("GET", "/agents")
        return res.get("agents", [])

    @classmethod
    def get_agent_details(cls, agent_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve agent details from /agents/{agent_name}."""
        res = cls._request("GET", f"/agents/{agent_name}")
        return res.get("agent")

    @classmethod
    def chat_with_agent(cls, agent_name: str, user_id: str, chat_id: str, message: str) -> Dict[str, Any]:
        """Send message to agent via POST /agents/{agent_name}/chat."""
        payload = {
            "user_id": str(user_id),
            "chat_id": str(chat_id),
            "message": message
        }
        return cls._request("POST", f"/agents/{agent_name}/chat", json_data=payload)

    # ── Brain Endpoints ──────────────────────────────────────────────

    @classmethod
    def get_user_brain(cls, user_id: str) -> Dict[str, Any]:
        """Retrieve full user brain snapshot from GET /brain/{user_id}."""
        res = cls._request("GET", f"/brain/{user_id}")
        return res.get("data", {})

    @classmethod
    def get_user_memories(cls, user_id: str, query: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve long term memories from GET /brain/{user_id}/memories."""
        params = {"limit": limit}
        if query:
            params["query"] = query
        res = cls._request("GET", f"/brain/{user_id}/memories", params=params)
        return res.get("memories", [])

