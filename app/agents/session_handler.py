"""
Standard Session Message Handler
----------------------------------------------------------------------
Canonical, structured, and efficient handlers for LangGraph and LangChain:
- Human message formatting and validation (HumanMessage)
- Session conversation history management with trim_messages
- System instruction & dynamic Brain Context injection (SystemMessage)
- Standard tool routing with tools_condition
- Session configuration with thread_id
"""

from typing import Any, Dict, List, Optional, Union
import logging

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
    trim_messages
)
from langgraph.prebuilt import ToolNode, tools_condition

logger = logging.getLogger("session_handler")


class SessionMessageHandler:
    """
    Standard utility class for managing LangChain/LangGraph session messages:
    1. Inbound human message creation & validation
    2. Dynamic system instruction & brain context injection
    3. Bounded conversation history trimming (trim_messages)
    4. Outbound AI response text extraction
    5. Standard thread_id session configuration
    """

    DEFAULT_MAX_HISTORY: int = 20

    @classmethod
    def to_human_message(
        cls,
        content: Union[str, HumanMessage],
        name: Optional[str] = None
    ) -> HumanMessage:
        """
        Convert a raw user input string into a standard LangChain HumanMessage.
        Ensures valid content and attaches optional metadata.
        """
        if isinstance(content, HumanMessage):
            return content

        text = str(content).strip() if content is not None else ""
        if not text:
            text = "..."

        kwargs: Dict[str, Any] = {"content": text}
        if name:
            kwargs["name"] = name
        return HumanMessage(**kwargs)

    @classmethod
    def build_system_message(
        cls,
        system_instruction: str,
        brain_prompt: Optional[str] = None
    ) -> SystemMessage:
        """
        Build a canonical LangChain SystemMessage combining the agent persona
        and any injected dynamic user brain context (profile, test results, Mem0 facts).
        """
        full_content = system_instruction.strip()
        if brain_prompt and brain_prompt.strip():
            full_content = f"{full_content}\n\n=== اطلاعات مغز و سوابق کاربر (User Brain Context) ===\n{brain_prompt.strip()}"

        return SystemMessage(content=full_content)

    @classmethod
    def trim_history(
        cls,
        messages: List[BaseMessage],
        max_messages: int = DEFAULT_MAX_HISTORY
    ) -> List[BaseMessage]:
        """
        Trim conversation history using LangChain's official trim_messages function.
        Guarantees that:
        - The conversation starts with a HumanMessage
        - Tool call and tool response pairings are preserved without orphans
        - The history is bounded to max_messages turns to prevent context blowup
        """
        if not messages:
            return []

        try:
            return trim_messages(
                messages,
                max_tokens=max_messages,
                strategy="last",
                token_counter=len,
                start_on="human",
                end_on=("human", "tool"),
                include_system=False
            )
        except Exception as e:
            logger.warning(f"trim_messages failed, using fallback slice: {e}")
            return messages[-max_messages:]

    @classmethod
    def prepare_session_messages(
        cls,
        messages: List[BaseMessage],
        system_instruction: str,
        brain_prompt: Optional[str] = None,
        max_history: int = DEFAULT_MAX_HISTORY
    ) -> List[BaseMessage]:
        """
        Standard pipeline to prepare messages for LLM invocation:
        1. Formulates the SystemMessage with brain context.
        2. Trims session history safely with trim_messages.
        3. Prepends SystemMessage to trimmed history.
        """
        system_msg = cls.build_system_message(system_instruction, brain_prompt)
        trimmed_history = cls.trim_history(messages, max_messages=max_history)
        return [system_msg] + trimmed_history

    @classmethod
    def extract_last_ai_content(cls, messages: List[BaseMessage]) -> str:
        """
        Extract clean text content from the last AIMessage in the session state.
        Gracefully handles both plain strings and multipart structured content blocks.
        """
        for m in reversed(messages):
            if isinstance(m, AIMessage):
                content = m.content
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and "text" in block:
                            parts.append(block["text"])
                        elif isinstance(block, str):
                            parts.append(block)
                    return "\n".join(parts) if parts else str(content)
                return str(content)
        return ""

    @classmethod
    def build_session_config(
        cls,
        user_id: Union[str, int],
        agent_name: str,
        chat_id: Union[str, int]
    ) -> Dict[str, Any]:
        """
        Construct standard LangGraph execution configuration with thread_id.
        This enables persistent conversation checkpointing per user and agent.
        """
        thread_id = f"{user_id}:{agent_name}:{chat_id}"
        return {"configurable": {"thread_id": thread_id}}
