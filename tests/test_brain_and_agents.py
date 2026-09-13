"""
End-to-End Test Suite for Brain Service & Modular Agents Framework
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.brain_service import get_brain_service
from app.agents.registry import AgentRegistry

client = TestClient(app)


def test_brain_service_snapshot():
    """Verify BrainService can build a user cognitive snapshot without error."""
    service = get_brain_service()
    snapshot = service.get_user_brain_snapshot(user_id="999999", query="تست اضطراب")
    
    assert snapshot is not None
    assert "profile" in snapshot
    assert "psychology_tests" in snapshot
    assert "long_term_memories" in snapshot
    assert "tasks" in snapshot
    assert "reminders" in snapshot

    # Verify context prompt generation
    prompt = service.build_brain_context_prompt(snapshot)
    assert isinstance(prompt, str)
    assert "مشخصات و پروفایل کاربر" in prompt


def test_agent_registry_discovery():
    """Verify agents are dynamically discovered from app/agents/definitions/."""
    agents = AgentRegistry.list_agents()
    agent_names = [a["name"] for a in agents]
    
    assert "therapist" in agent_names
    assert "life_coach" in agent_names

    therapist = AgentRegistry.get("therapist")
    assert therapist is not None
    assert therapist.name == "therapist"
    assert len(therapist.tools) >= 1
    assert "cognitive_pattern_analysis" in therapist.skills


def test_fastapi_brain_endpoints():
    """Verify /brain endpoints respond with expected structure."""
    # 1. Full snapshot
    response = client.get("/brain/999999")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data

    # 2. Context prompt
    response = client.get("/brain/999999/context-prompt")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "context_prompt" in data


def test_fastapi_agents_endpoints():
    """Verify /agents endpoints list, detail, and skill execution."""
    # 1. List agents
    response = client.get("/agents")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["count"] >= 2

    # 2. Get specific agent detail
    response = client.get("/agents/therapist")
    assert response.status_code == 200
    data = response.json()
    assert data["agent"]["name"] == "therapist"
    assert len(data["agent"]["tools"]) >= 1

    # 3. 404 for non-existent agent
    response = client.get("/agents/non_existent_agent_xyz")
    assert response.status_code == 404

