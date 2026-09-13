"""
Test Telegram Agent Chat Routing & State Transitions
"""

import pytest
from unittest.mock import MagicMock
from telegram import Update, Message, User, Chat, CallbackQuery
from telegram.ext import CallbackContext

import telegram_handlers as handlers
import telegram_ui as ui


def test_telegram_ui_html_formatting():
    """Verify UI templates use valid HTML tags and no raw markdown asterisks."""
    assert "<b>" in ui.AGENTS_MENU_INTRO
    assert "<b>" in ui.AGENT_DETAILS_TEMPLATE
    assert "<code>" in ui.AGENT_DETAILS_TEMPLATE
    assert "**" not in ui.AGENT_DETAILS_TEMPLATE
    assert "**" not in ui.AGENT_CHAT_START_TEMPLATE
    assert "**" not in ui.BRAIN_MENU_TEMPLATE


def test_agent_chat_session_lifecycle():
    """Test starting, routing, and ending an agent chat session."""
    # Mock update & context
    update = MagicMock(spec=Update)
    context = MagicMock(spec=CallbackContext)
    context.user_data = {}

    # Mock effective chat and user
    chat = MagicMock(spec=Chat)
    chat.id = 12345
    update.effective_chat = chat
    update.message = MagicMock(spec=Message)
    update.message.chat_id = 12345
    update.message.text = "سلام هدف من چیه؟"

    # Mock callback query for start_agent_chat
    query = MagicMock(spec=CallbackQuery)
    query.data = "start_agent_chat_life_coach"
    update.callback_query = query

    # 1. Start agent chat
    handlers.start_agent_chat_callback(update, context)
    assert context.user_data["agent_chat_active"] is True
    assert context.user_data["active_agent_name"] == "life_coach"
    assert context.user_data["smart_chat_active"] is False

    # 2. End agent chat
    update.callback_query = None
    update.message.text = "/end_agent"
    handlers.end_agent_chat(update, context)
    assert context.user_data["agent_chat_active"] is False
    assert "active_agent_name" not in context.user_data


def test_stop_command_handler():
    """Test universal stop command handler."""
    update = MagicMock(spec=Update)
    context = MagicMock(spec=CallbackContext)
    update.effective_chat = MagicMock()
    update.message = MagicMock()

    # Agent active
    context.user_data = {"agent_chat_active": True, "active_agent_name": "therapist"}
    handlers.stop_command_handler(update, context)
    assert context.user_data["agent_chat_active"] is False

    # Smart chat active
    context.user_data = {"smart_chat_active": True}
    handlers.stop_command_handler(update, context)
    assert context.user_data["smart_chat_active"] is False
