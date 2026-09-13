"""
Test Telegram FastAPI Bridge and Handlers Integration
"""

import pytest
from app.services.telegram_fastapi_bridge import TelegramFastAPIBridge
import telegram_handlers as handlers
import telegrambot as bot


def test_telegram_bridge_get_agents():
    """Verify Telegram bridge retrieves registered agents via FastAPI."""
    agents = TelegramFastAPIBridge.get_agents()
    assert isinstance(agents, list)
    assert len(agents) >= 2
    names = [a["name"] for a in agents]
    assert "therapist" in names
    assert "life_coach" in names


def test_telegram_bridge_agent_details():
    """Verify Telegram bridge retrieves single agent details."""
    agent = TelegramFastAPIBridge.get_agent_details("therapist")
    assert agent is not None
    assert agent["name"] == "therapist"
    assert "tools" in agent
    assert "skills" in agent


def test_telegram_bridge_get_brain():
    """Verify Telegram bridge retrieves user brain snapshot."""
    brain = TelegramFastAPIBridge.get_user_brain("12345")
    assert isinstance(brain, dict)
    assert "profile" in brain
    assert "long_term_memories" in brain


def test_telegram_bridge_chat_with_agent():
    """Verify Telegram bridge can execute an agent chat without SqliteSaver error."""
    res = TelegramFastAPIBridge.chat_with_agent(
        agent_name="life_coach",
        user_id="12345",
        chat_id="test_tg_chat",
        message="سلام، هدف امروز من چیست؟"
    )
    assert res is not None
    assert res.get("success") is True
    assert res.get("agent") == "life_coach"
    assert "response" in res
    assert len(res["response"]) > 0


def test_telegram_handlers_exist():
    """Verify all new Telegram handlers are callable."""
    assert callable(handlers.show_agents_menu)
    assert callable(handlers.select_agent_callback)
    assert callable(handlers.start_agent_chat_callback)
    assert callable(handlers.end_agent_chat)
    assert callable(handlers.show_user_brain)
    assert callable(handlers.show_brain_memories_callback)

