"""
Unit and integration tests for SessionMessageHandler
----------------------------------------------------------------------
Validates:
- HumanMessage conversion and whitespace handling
- Dynamic SystemMessage generation with brain context
- trim_messages integration for conversation history
- Robust last AIMessage text extraction
- Standard LangGraph session thread configuration
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from app.agents.session_handler import SessionMessageHandler


def test_to_human_message():
    # 1. Plain string
    msg = SessionMessageHandler.to_human_message("سلام من علی هستم")
    assert isinstance(msg, HumanMessage)
    assert msg.content == "سلام من علی هستم"

    # 2. Existing HumanMessage instance
    existing = HumanMessage(content="تست پیام")
    res = SessionMessageHandler.to_human_message(existing)
    assert res is existing

    # 3. None or empty string
    empty = SessionMessageHandler.to_human_message("")
    assert empty.content == "..."


def test_build_system_message():
    # 1. Plain instruction
    sys_msg = SessionMessageHandler.build_system_message("شما یک مربی هستید.")
    assert isinstance(sys_msg, SystemMessage)
    assert sys_msg.content == "شما یک مربی هستید."

    # 2. With brain context injected
    sys_with_brain = SessionMessageHandler.build_system_message(
        system_instruction="شما یک مربی هستید.",
        brain_prompt="نام کاربر: سارا | سن: ۲۲"
    )
    assert "شما یک مربی هستید." in sys_with_brain.content
    assert "نام کاربر: سارا | سن: ۲۲" in sys_with_brain.content
    assert "User Brain Context" in sys_with_brain.content


def test_trim_history():
    messages = [
        HumanMessage(content="سلام"),
        AIMessage(content="درود، چطور می‌تونم کمکت کنم؟"),
        HumanMessage(content="برنامه روز ۱ چیست؟"),
        AIMessage(content="روز ۱ تمرکز روی پومودورو است."),
        HumanMessage(content="انجام دادم")
    ]
    # Trim to last 3 messages
    trimmed = SessionMessageHandler.trim_history(messages, max_messages=3)
    assert len(trimmed) <= 3
    # trim_messages with start_on="human" ensures the first message is a HumanMessage
    assert isinstance(trimmed[0], HumanMessage)
    assert trimmed[-1].content == "انجام دادم"


def test_prepare_session_messages():
    history = [
        HumanMessage(content="پیام ۱"),
        AIMessage(content="پاسخ ۱"),
        HumanMessage(content="پیام ۲")
    ]
    prepared = SessionMessageHandler.prepare_session_messages(
        messages=history,
        system_instruction="شما مربی تحصیلی هستید.",
        brain_prompt="مقطع: کنکور",
        max_history=10
    )
    # First message MUST be SystemMessage
    assert isinstance(prepared[0], SystemMessage)
    assert "شما مربی تحصیلی هستید." in prepared[0].content
    assert "مقطع: کنکور" in prepared[0].content

    # Following messages are the trimmed conversation
    assert isinstance(prepared[1], HumanMessage)
    assert prepared[-1].content == "پیام ۲"


def test_extract_last_ai_content():
    # 1. Plain string content
    msgs1 = [
        HumanMessage(content="سلام"),
        AIMessage(content="سلام دوست من!")
    ]
    assert SessionMessageHandler.extract_last_ai_content(msgs1) == "سلام دوست من!"

    # 2. Multipart list of content blocks (typical of Gemini/Claude)
    msgs2 = [
        HumanMessage(content="سلام"),
        AIMessage(content=[{"type": "text", "text": "بخش اول"}, {"type": "text", "text": "بخش دوم"}])
    ]
    assert SessionMessageHandler.extract_last_ai_content(msgs2) == "بخش اول\nبخش دوم"

    # 3. No AI message
    msgs3 = [HumanMessage(content="سلام")]
    assert SessionMessageHandler.extract_last_ai_content(msgs3) == ""


def test_build_session_config():
    config = SessionMessageHandler.build_session_config(
        user_id="12345",
        agent_name="school_assistant",
        chat_id="67890"
    )
    assert "configurable" in config
    assert config["configurable"]["thread_id"] == "12345:school_assistant:67890"
