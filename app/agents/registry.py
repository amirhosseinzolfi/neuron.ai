"""
Agent Registry
----------------------------------------------------------------------
Dynamic registry and auto-discovery engine for modular agents in Neuron.
"""

import os
import importlib
import inspect
import logging
from typing import Dict, List, Optional, Type, Union, Any

from app.agents.base import BaseAgent

logger = logging.getLogger("agent_registry")


class AgentRegistry:
    """
    Central registry that holds all loaded agents and automatically
    discovers agent definition files.
    """
    _agents: Dict[str, BaseAgent] = {}
    _discovered: bool = False

    @classmethod
    def register(cls, agent_item: Union[Type[BaseAgent], BaseAgent]) -> BaseAgent:
        """Register an agent class or instance."""
        if inspect.isclass(agent_item):
            instance = agent_item()
        else:
            instance = agent_item

        if not isinstance(instance, BaseAgent):
            raise TypeError(f"Registered item must be an instance of BaseAgent, got {type(instance)}")

        if not instance.name:
            raise ValueError(f"Agent class {agent_item.__name__ if inspect.isclass(agent_item) else type(instance).__name__} must define a 'name'")

        cls._agents[instance.name] = instance
        logger.info(f"Registered agent: '{instance.name}'")
        return instance

    @classmethod
    def get(cls, name: str) -> Optional[BaseAgent]:
        """Retrieve an agent by its unique identifier."""
        cls.ensure_discovered()
        return cls._agents.get(name)

    @classmethod
    def list_agents(cls) -> List[Dict[str, Any]]:
        """List metadata and capabilities of all registered agents."""
        cls.ensure_discovered()
        result = []
        for a in cls._agents.values():
            result.append({
                "name": a.name,
                "display_name": a.display_name,
                "description": a.description,
                "version": a.version,
                "tools": [
                    {
                        "name": getattr(t, "name", str(t)),
                        "description": getattr(t, "description", "")
                    }
                    for t in a.tools
                ],
                "skills": list(a.skills.keys())
            })
        return result

    @classmethod
    def ensure_discovered(cls):
        """Auto-discover all agents defined under app/agents/definitions/."""
        if cls._discovered:
            return

        definitions_dir = os.path.join(os.path.dirname(__file__), "definitions")
        if not os.path.exists(definitions_dir):
            os.makedirs(definitions_dir, exist_ok=True)
            cls._discovered = True
            return

        for fname in os.listdir(definitions_dir):
            if fname.endswith(".py") and not fname.startswith("__"):
                module_name = f"app.agents.definitions.{fname[:-3]}"
                try:
                    importlib.import_module(module_name)
                    logger.info(f"Loaded agent module: {module_name}")
                except Exception as e:
                    logger.error(f"Failed to import agent module {module_name}: {e}", exc_info=True)

        cls._discovered = True


def register_agent(cls_or_instance):
    """Decorator to register an agent class or instance."""
    return AgentRegistry.register(cls_or_instance)

