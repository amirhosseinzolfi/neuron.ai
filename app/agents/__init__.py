"""
Agents Package
----------------------------------------------------------------------
Exports BaseAgent, AgentState, AgentRegistry, and @register_agent.
Auto-discovers definitions upon initialization.
"""

from app.agents.base import BaseAgent, AgentState
from app.agents.registry import AgentRegistry, register_agent

# Trigger auto-discovery
AgentRegistry.ensure_discovered()

__all__ = ["BaseAgent", "AgentState", "AgentRegistry", "register_agent"]

