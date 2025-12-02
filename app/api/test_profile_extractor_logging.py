import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
import os
import tempfile
from datetime import datetime

# Define a dummy profile for testing
DUMMY_PROFILE = {
    "user_id": "testuser123",
    "core_info": {"name": "John Doe", "age": 30, "occupation": "Software Engineer"},
    "professional_profile": {"skills": ["Python", "FastAPI"]},
    "psychological_profile": {"summary": "Initial summary."},
    "metadata": {"last_updated": "2023-01-01T00:00:00", "confidence": 0.5}
}

# Define a psychology test result for testing
PSYCH_TEST_RESULT = {
    "test_name": "Big Five Personality Test",
    "date_taken": "2023-10-26T10:00:00",
    "summary": "User shows high openness and conscientiousness.",
    "full_results": {
        "openness": 0.85,
        "conscientiousness": 0.90,
        "extraversion": 0.60,
        "agreeableness": 0.70,
        "neuroticism": 0.30
    }
}

# Mock the process_input function from profile_extract_agent_json
# This allows us to control the agent's output without actually running the LLM
@pytest.fixture
def mock_process_input():
    # Patch process_input where it's used in the router
    with patch("app.api.profile_extractor_router.process_input") as mock_pi:
        yield mock_pi

@pytest.fixture
def client(mock_process_input): # Add mock_process_input as a dependency
    # Import app here to ensure it's loaded after the patch is active
    from app.main import app
    return TestClient(app)

def test_extract_profile_no_input(client: TestClient, mock_process_input: MagicMock):
    """Test profile extraction with no text or media inputs."""
    mock_process_input.return_value = {
        "user_id": "mockuser123",
        "profile": {
            "core_info": {"name": "Mock User"},
            "metadata": {"last_updated": datetime.now().isoformat(), "confidence": 0.9}
        },
        "profile_json": json.dumps({"core_info": {"name": "Mock User"}}),
        "profile_path": "/mock/path/mockuser123_profile.json",
        "action": "extract",
        "confidence": 0.9,
        "operations": 1,
        "history": [],
        "last_updated": datetime.now().isoformat()
    }
    response = client.post("/profile/extract")
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "profile" in data
    assert data["action"] == "extract"
    mock_process_input.assert_called_once()
    args, kwargs = mock_process_input.call_args
    assert args[1] == "Extract comprehensive profile information from all provided media inputs."
    assert args[2] == [] # No media inputs

def test_extract_profile_with_text(client: TestClient, mock_process_input: MagicMock):
    """Test profile extraction with text messages."""
    test_text = ["Hello, my name is Jane.", "I work as a data scientist."]
    mock_process_input.return_value = {
        "user_id": "mockuser123",
        "profile": {
            "core_info": {"name": "Mock User"},
            "metadata": {"last_updated": datetime.now().isoformat(), "confidence": 0.9}
        },
        "profile_json": json.dumps({"core_info": {"name": "Mock User"}}),
        "profile_path": "/mock/path/mockuser123_profile.json",
        "action": "extract",
        "confidence": 0.9,
        "operations": 1,
        "history": [],
        "last_updated": datetime.now().isoformat()
    }
    response = client.post(
        "/profile/extract",
        data={"text_messages": json.dumps(test_text)}
    )
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "profile" in data
    mock_process_input.assert_called_once()
    args, kwargs = mock_process_input.call_args
    assert args[1] == "Hello, my name is Jane.\nI work as a data scientist."
    assert args[2] == []

def test_extract_profile_with_image(client: TestClient, mock_process_input: MagicMock):
    """Test profile extraction with an image file."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_img:
        temp_img.write(b"fake image content")
        temp_img_path = temp_img.name
    
    try:
        mock_process_input.return_value = {
            "user_id": "mockuser123",
            "profile": {
                "core_info": {"name": "Mock User"},
                "metadata": {"last_updated": datetime.now().isoformat(), "confidence": 0.9}
            },
            "profile_json": json.dumps({"core_info": {"name": "Mock User"}}),
            "profile_path": "/mock/path/mockuser123_profile.json",
            "action": "extract",
            "confidence": 0.9,
            "operations": 1,
            "history": [],
            "last_updated": datetime.now().isoformat()
        }
        response = client.post(
            "/profile/extract",
            files={"images": ("test_image.jpg", open(temp_img_path, "rb"), "image/jpeg")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "profile" in data
        mock_process_input.assert_called_once()
        args, kwargs = mock_process_input.call_args
        assert args[1] == "Analyze the provided media inputs to extract and refine the user profile."
        assert len(args[2]) == 1
        assert args[2][0]["type"] == "image"
        assert os.path.exists(args[2][0]["path"]) # Temp file should exist before agent call
    finally:
        os.remove(temp_img_path)

def test_extract_profile_with_audio(client: TestClient, mock_process_input: MagicMock):
    """Test profile extraction with an audio file."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
        temp_audio.write(b"fake audio content")
        temp_audio_path = temp_audio.name
    
    try:
        mock_process_input.return_value = {
            "user_id": "mockuser123",
            "profile": {
                "core_info": {"name": "Mock User"},
                "metadata": {"last_updated": datetime.now().isoformat(), "confidence": 0.9}
            },
            "profile_json": json.dumps({"core_info": {"name": "Mock User"}}),
            "profile_path": "/mock/path/mockuser123_profile.json",
            "action": "extract",
            "confidence": 0.9,
            "operations": 1,
            "history": [],
            "last_updated": datetime.now().isoformat()
        }
        response = client.post(
            "/profile/extract",
            files={"audios": ("test_audio.mp3", open(temp_audio_path, "rb"), "audio/mp3")}
        )
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "profile" in data
        mock_process_input.assert_called_once()
        args, kwargs = mock_process_input.call_args
        assert args[1] == "Analyze the provided media inputs to extract and refine the user profile."
        assert len(args[2]) == 1
        assert args[2][0]["type"] == "audio"
        assert os.path.exists(args[2][0]["path"]) # Temp file should exist before agent call
    finally:
        os.remove(temp_audio_path)

def test_extract_profile_with_initial_profile_file(client: TestClient, mock_process_input: MagicMock):
    """Test profile extraction with an initial profile JSON file."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_profile_file:
        temp_profile_file.write(json.dumps(DUMMY_PROFILE).encode())
        temp_profile_path = temp_profile_file.name
    
    try:
        mock_process_input.return_value = {
            "user_id": "testuser123",
            "profile": {
                "core_info": {"name": "Mock User"},
                "metadata": {"last_updated": datetime.now().isoformat(), "confidence": 0.9}
            },
            "profile_json": json.dumps({"core_info": {"name": "Mock User"}}),
            "profile_path": "/mock/path/testuser123_profile.json",
            "action": "refine", # Should be refine if initial profile is provided
            "confidence": 0.9,
            "operations": 1,
            "history": [],
            "last_updated": datetime.now().isoformat()
        }
        response = client.post(
            "/profile/extract",
            files={"user_profile_file": ("profile.json", open(temp_profile_path, "rb"), "application/json")},
            data={"user_id": "testuser123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "testuser123"
        assert "profile" in data
        mock_process_input.assert_called_once()
        args, kwargs = mock_process_input.call_args
        assert kwargs["initial_profile_data"] == DUMMY_PROFILE
    finally:
        os.remove(temp_profile_path)

def test_extract_profile_with_psych_test_results(client: TestClient, mock_process_input: MagicMock):
    """Test profile extraction with psychology test results in text."""
    psych_text = f"Here are my psychology test results: {json.dumps(PSYCH_TEST_RESULT)}"
    
    # Mock the agent to return an updated profile with psych test results
    mock_process_input.return_value = {
        "user_id": "mockuser123",
        "profile": {
            "core_info": {"name": "Mock User"},
            "psychological_profile": {
                "summary": PSYCH_TEST_RESULT["summary"],
                "personality_traits": {
                    "openness": PSYCH_TEST_RESULT["full_results"]["openness"],
                    "conscientiousness": PSYCH_TEST_RESULT["full_results"]["conscientiousness"],
                    "extraversion": PSYCH_TEST_RESULT["full_results"]["extraversion"],
                    "agreeableness": PSYCH_TEST_RESULT["full_results"]["agreeableness"],
                    "neuroticism": PSYCH_TEST_RESULT["full_results"]["neuroticism"],
                }
            },
            "metadata": {"last_updated": datetime.now().isoformat(), "confidence": 0.95}
        },
        "profile_json": json.dumps({"core_info": {"name": "Mock User"}}),
        "profile_path": "/mock/path/mockuser123_profile.json",
        "action": "MERGE", # Set action to MERGE for this specific test
        "confidence": 0.95,
        "operations": 1,
        "history": [],
        "last_updated": datetime.now().isoformat()
    }

    response = client.post(
        "/profile/extract",
        data={"text_messages": json.dumps([psych_text])}
    )
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert "profile" in data
    assert data["action"] == "MERGE"
    assert data["profile"]["psychological_profile"]["summary"] == PSYCH_TEST_RESULT["summary"]
    assert data["profile"]["psychological_profile"]["personality_traits"]["openness"] == PSYCH_TEST_RESULT["full_results"]["openness"]
    mock_process_input.assert_called_once()
    args, kwargs = mock_process_input.call_args
    assert args[1] == psych_text

def test_extract_profile_json_with_profile_data(client: TestClient, mock_process_input: MagicMock):
    """Test profile extraction from JSON input with existing profile data."""
    input_data = {
        "user_id": "jsonuser456",
        "user_profile": DUMMY_PROFILE,
        "text_messages": ["I like hiking and reading."],
        "conversation_history": [{"role": "user", "content": "What are your hobbies?"}]
    }
    # Mock the agent to return an updated profile with the correct user_id for this test
    mock_process_input.return_value = {
        "user_id": input_data["user_id"], # Set user_id to match input
        "profile": {
            "core_info": {"name": "Mock User"},
            "metadata": {"last_updated": datetime.now().isoformat(), "confidence": 0.9}
        },
        "profile_json": json.dumps({"core_info": {"name": "Mock User"}}),
        "profile_path": f"/mock/path/{input_data['user_id']}_profile.json",
        "action": "refine", # Should be refine if initial profile is provided
        "confidence": 0.9,
        "operations": 1,
        "history": [],
        "last_updated": datetime.now().isoformat()
    }

    response = client.post(
        "/profile/extract-json",
        json=input_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "jsonuser456"
    assert "profile" in data
    mock_process_input.assert_called_once()
    args, kwargs = mock_process_input.call_args
    expected_text = "I like hiking and reading.\n\nConversation:\nuser: What are your hobbies?"
    assert args[1] == expected_text
    assert args[2] == [] # No media inputs for extract-json endpoint

def test_extract_profile_json_no_messages(client: TestClient):
    """Test profile extraction from JSON input with no messages."""
    input_data = {
        "user_id": "jsonuser789",
        "user_profile": DUMMY_PROFILE,
        "text_messages": [],
        "conversation_history": []
    }
    response = client.post(
        "/profile/extract-json",
        json=input_data
    )
    assert response.status_code == 400
    assert "No input messages provided" in response.json()["detail"]

def test_extract_profile_json_agent_failure(client: TestClient, mock_process_input: MagicMock):
    """Test error handling when agent fails."""
    mock_process_input.side_effect = Exception("Agent internal error")
    input_data = {
        "user_id": "jsonuserfail",
        "text_messages": ["Some text."]
    }
    response = client.post(
        "/profile/extract-json",
        json=input_data
    )
    assert response.status_code == 500
    assert "Agent internal error" in response.json()["detail"]

def test_extract_profile_agent_failure(client: TestClient, mock_process_input: MagicMock):
    """Test error handling when agent fails for multimodal endpoint."""
    mock_process_input.side_effect = Exception("Multimodal agent internal error")
    response = client.post(
        "/profile/extract",
        data={"text_messages": "Some text."}
    )
    assert response.status_code == 500
    assert "Multimodal agent internal error" in response.json()["detail"]
