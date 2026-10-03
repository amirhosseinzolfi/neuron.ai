"""
Base Agent Module
----------------------------------------------------------------------
Defines the foundational schema, state, and abstract interface for all
modular agents within Neuron.
"""

from abc import ABC, abstractmethod
from typing import Annotated, Any, Dict, List, Optional, AsyncIterator
from typing_extensions import TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState
from langgraph.pregel import Pregel
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.agents.session_handler import SessionMessageHandler
from app.services.brain_service import get_brain_service


class AgentState(MessagesState, total=False):
    """
    Standard state schema for all Neuron agents.
    Inherits from LangGraph MessagesState, providing 'messages: Annotated[list[AnyMessage], add_messages]'.
    """
    user_id: str
    chat_id: str
    brain_context: Dict[str, Any]
    brain_prompt: str
    summary: Optional[str]
    metadata: Dict[str, Any]


class BaseAgent(ABC):
    """
    Abstract Base Agent.
    Every agent in app/agents/definitions/ must inherit from this class.
    """
    name: str
    display_name: str
    description: str
    version: str = "1.0.0"

    def __init__(self):
        self._compiled_graph: Optional[Pregel] = None

    @property
    @abstractmethod
    def system_instruction(self) -> str:
        """The persona, core rules, and system prompt for the agent."""
        pass

    @property
    @abstractmethod
    def tools(self) -> List[BaseTool]:
        """List of tools specific to this agent."""
        pass

    @property
    def skills(self) -> Dict[str, Any]:
        """
        Specialized AI skills/routines associated with this agent.
        Key: skill_name, Value: callable skill function or workflow.
        """
        return {}

    @abstractmethod
    def build_graph(self, checkpointer: Optional[BaseCheckpointSaver] = None) -> Pregel:
        """
        Construct and compile the agent's LangGraph workflow.
        Must return a compiled Pregel instance.
        """
        pass

    def get_graph(self, checkpointer: Optional[BaseCheckpointSaver] = None) -> Pregel:
        """Get or lazily compile the agent graph."""
        if self._compiled_graph is None or (checkpointer is not None and getattr(self._compiled_graph, "checkpointer", None) != checkpointer):
            self._compiled_graph = self.build_graph(checkpointer=checkpointer)
        return self._compiled_graph

    async def ainvoke(
        self,
        user_id: str,
        chat_id: str,
        message: str,
        brain_snapshot: Dict[str, Any],
        checkpointer: Optional[BaseCheckpointSaver] = None
    ) -> Dict[str, Any]:
        """
        Execute agent with unified brain context and auto-persist to Mem0 memory.
        Uses standard SessionMessageHandler for message formatting and thread config.
        """
        brain_service = get_brain_service()
        brain_prompt = brain_service.build_brain_context_prompt(brain_snapshot)

        graph = self.get_graph(checkpointer=checkpointer)
        config = SessionMessageHandler.build_session_config(user_id, self.name, chat_id)
        human_msg = SessionMessageHandler.to_human_message(message)

        initial_state: AgentState = {
            "messages": [human_msg],
            "user_id": str(user_id),
            "chat_id": str(chat_id),
            "brain_context": brain_snapshot,
            "brain_prompt": brain_prompt,
            "metadata": {"agent": self.name, "thread_id": config["configurable"]["thread_id"]}
        }

        # Run graph
        result = await graph.ainvoke(initial_state, config=config)

        # Extract last AI message content via standard helper
        messages = result.get("messages", [])
        last_ai_content = SessionMessageHandler.extract_last_ai_content(messages)

        # Automatically synchronize interaction with the user's brain memory in background
        if message and last_ai_content:
            brain_service.sync_memory(
                user_id=user_id,
                user_text=message,
                assistant_text=last_ai_content,
                source=f"agent:{self.name}"
            )

        return {
            "agent": self.name,
            "display_name": self.display_name,
            "user_id": user_id,
            "chat_id": chat_id,
            "response": last_ai_content,
            "messages_count": len(messages)
        }

    async def astream(
        self,
        user_id: str,
        chat_id: str,
        message: str,
        brain_snapshot: Dict[str, Any],
        checkpointer: Optional[BaseCheckpointSaver] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Stream events and tokens from the agent's LangGraph execution.
        """
        brain_service = get_brain_service()
        brain_prompt = brain_service.build_brain_context_prompt(brain_snapshot)

        graph = self.get_graph(checkpointer=checkpointer)
        config = SessionMessageHandler.build_session_config(user_id, self.name, chat_id)
        human_msg = SessionMessageHandler.to_human_message(message)

        initial_state: AgentState = {
            "messages": [human_msg],
            "user_id": str(user_id),
            "chat_id": str(chat_id),
            "brain_context": brain_snapshot,
            "brain_prompt": brain_prompt,
            "metadata": {"agent": self.name, "thread_id": config["configurable"]["thread_id"]}
        }

        accumulated_ai_response = ""

        async for event in graph.astream_events(initial_state, config=config, version="v2"):
            event_type = event.get("event")
            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    accumulated_ai_response += str(chunk.content)
                    yield {
                        "type": "token",
                        "token": chunk.content
                    }
            elif event_type == "on_tool_start":
                yield {
                    "type": "tool_start",
                    "tool": event.get("name"),
                    "input": event.get("data", {}).get("input")
                }
            elif event_type == "on_tool_end":
                yield {
                    "type": "tool_end",
                    "tool": event.get("name"),
                    "output": event.get("data", {}).get("output")
                }

        # Sync final result to brain memory
        if message and accumulated_ai_response:
            brain_service.sync_memory(
                user_id=user_id,
                user_text=message,
                assistant_text=accumulated_ai_response,
                source=f"agent:{self.name}"
            )

