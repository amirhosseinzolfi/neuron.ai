import json
import logging
from typing import Any, Dict, Optional

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from app.api.memory_router import router as memory_router
from app.services.memory_service import MemoryService, get_memory_service


LOGGER = logging.getLogger("tests.memory_router")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)


def _log_exchange(
    *,
    phase: str,
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]],
    response,
):
    pretty_payload = json.dumps(payload, ensure_ascii=False) if payload else "{}"
    try:
        body = json.dumps(response.json(), ensure_ascii=False, indent=2)
    except Exception:
        body = response.text

    LOGGER.info(
        "[%s] %s %s payload=%s => status=%s\nresponse=%s",
        phase,
        method,
        path,
        pretty_payload,
        response.status_code,
        body,
    )


def _request(
    client: TestClient,
    method: str,
    path: str,
    *,
    json_body: Optional[Dict[str, Any]] = None,
    phase: str,
):
    LOGGER.info("Requesting %s %s (%s)", method, path, phase)
    response = client.request(method, path, json=json_body)
    _log_exchange(
        phase=phase,
        method=method,
        path=path,
        payload=json_body,
        response=response,
    )
    return response


@pytest.fixture
def mock_service():
    return MagicMock(spec=MemoryService)


@pytest.fixture
def client(mock_service):
    test_app = FastAPI(title="Memory Router Test App")
    test_app.include_router(memory_router)

    test_app.dependency_overrides[get_memory_service] = lambda: mock_service

    with TestClient(test_app) as test_client:
        yield test_client
    test_app.dependency_overrides.clear()


def test_list_user_memories(client, mock_service):
    mock_service.list_memories.return_value = [
        {"id": "m1", "memory": "Loves hiking", "score": 0.9},
        {"id": "m2", "memory": "Prefers Persian responses", "score": 0.8},
    ]

    response = _request(
        client,
        "GET",
        "/memory/u123?limit=2",
        phase="list_user_memories",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["count"] == 2
    mock_service.list_memories.assert_called_once_with("u123", limit=2)


def test_memory_stats(client, mock_service):
    mock_service.stats.return_value = {"mem0_memories": 5, "local_chunks": 3}

    response = _request(
        client,
        "GET",
        "/memory/u123/stats",
        phase="memory_stats",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["stats"] == {"mem0_memories": 5, "local_chunks": 3}
    mock_service.stats.assert_called_once_with("u123")


def test_search_user_memories(client, mock_service):
    mock_service.search_memories.return_value = [
        {"content": "User likes jazz", "score": 0.77}
    ]

    response = _request(
        client,
        "POST",
        "/memory/u123/search",
        json_body={"query": "likes", "limit": 3},
        phase="search_user_memories",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    mock_service.search_memories.assert_called_once_with("u123", query="likes", limit=3)


def test_store_conversation_turn(client, mock_service):
    mock_service.store_conversation_turn.return_value = True

    response = _request(
        client,
        "POST",
        "/memory/u123/store",
        json_body={
            "user_text": "I enjoy meditation",
            "assistant_text": "Noted, I'll remember that",
            "metadata": {"topic": "wellness"},
        },
        phase="store_conversation_turn",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    mock_service.store_conversation_turn.assert_called_once()


def test_store_conversation_turn_validation_error(client, mock_service):
    mock_service.store_conversation_turn.side_effect = ValueError("missing text")

    response = _request(
        client,
        "POST",
        "/memory/u123/store",
        json_body={
            "user_text": "",
            "assistant_text": "ack",
            "metadata": None,
        },
        phase="store_conversation_turn_validation",
    )

    assert response.status_code == 422
    # Request body validation fails before hitting service, so no call should occur
    mock_service.store_conversation_turn.assert_not_called()


def test_add_manual_memory(client, mock_service):
    mock_service.add_manual_memory.return_value = True

    response = _request(
        client,
        "POST",
        "/memory/u123/notes",
        json_body={
            "content": "User has a dog",
            "memory_type": "profile",
            "metadata": {"pet_name": "Rex"},
        },
        phase="add_manual_memory",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    mock_service.add_manual_memory.assert_called_once_with(
        "u123",
        content="User has a dog",
        metadata={"pet_name": "Rex"},
        memory_type="profile",
    )
