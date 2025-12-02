import os
import json
import base64
from pathlib import Path
from datetime import datetime
from typing import TypedDict, Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from logging_utils import write_event
from database.prompts import (
    PROFILE_EXTRACTOR_INSTRUCTION_TEMPLATE,
    PROFILE_EXTRACTOR_OUTPUT_SYSTEM,
)


import os
from dotenv import load_dotenv

load_dotenv()

PROFILE_API_KEY = os.getenv("GOOGLE_API_KEY_PROFILE")

if not PROFILE_API_KEY:
    raise RuntimeError(
        "Missing GOOGLE_API_KEY_PROFILE environment variable. Set it in your .env file."
    )

llm = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    api_key=PROFILE_API_KEY,
    temperature=0.7
)

# ===== NEW DATA MODELS =====

class CoreInfo(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    occupation: Optional[str] = None

class JobHistoryItem(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    duration: Optional[str] = None

class ProfessionalProfile(BaseModel):
    career_summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    job_history: List[JobHistoryItem] = Field(default_factory=list)

class Relation(BaseModel):
    name: Optional[str] = None
    relationship_type: Optional[str] = Field(default=None, description="e.g., Partner, Friend, Family")
    connected_user_id: Optional[str] = None

class SocialProfile(BaseModel):
    relationship_status: Optional[str] = Field(default=None, description="e.g., Single, In a relationship")
    relations: List[Relation] = Field(default_factory=list)

class Lifestyle(BaseModel):
    summary: Optional[str] = None
    routines: List[str] = Field(default_factory=list)

class PersonalOutlook(BaseModel):
    interests: List[str] = Field(default_factory=list)
    goals: List[str] = Field(default_factory=list)
    values: List[str] = Field(default_factory=list)

class PsychologicalTestResult(BaseModel):
    test_name: str
    date_taken: str = Field(default_factory=lambda: datetime.now().isoformat())
    summary: str
    full_results: Dict[str, Any] = Field(default_factory=dict)

class PersonalityTraits(BaseModel):
    openness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    conscientiousness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    extraversion: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    agreeableness: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    neuroticism: Optional[float] = Field(default=None, ge=0.0, le=1.0)

class PsychologicalProfile(BaseModel):
    summary: Optional[str] = Field(default=None, description="AI-generated summary of the user's psychological profile.")
    personality_traits: PersonalityTraits = Field(default_factory=PersonalityTraits)
    cognitive_biases: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    areas_for_development: List[str] = Field(default_factory=list)

class Metadata(BaseModel):
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    extracted_from: List[str] = Field(default_factory=list)

class UserProfile(BaseModel):
    user_id: Optional[str] = None
    core_info: CoreInfo = Field(default_factory=CoreInfo)
    professional_profile: ProfessionalProfile = Field(default_factory=ProfessionalProfile)
    social_profile: SocialProfile = Field(default_factory=SocialProfile)
    lifestyle: Lifestyle = Field(default_factory=Lifestyle)
    personal_outlook: PersonalOutlook = Field(default_factory=PersonalOutlook)
    psychological_profile: PsychologicalProfile = Field(default_factory=PsychologicalProfile)
    psychological_tests: List[PsychologicalTestResult] = Field(default_factory=list)
    additional_data: Dict[str, Any] = Field(default_factory=dict, description="For any extra data that doesn't fit the schema.")
    metadata: Metadata = Field(default_factory=Metadata)


class State(TypedDict):
    user_id: str
    message: str
    media: list[dict]
    profile: UserProfile
    existing_profile: Optional[UserProfile]
    existing_profile_json: Optional[str]
    history: list[dict]
    context: str
    operation: str
    profile_path: str
    persist: bool

# ===== PROFILE PERSISTENCE =====

def get_profile_path(user_id: str) -> str:
    """Get profile file path for user."""
    os.makedirs("database/user_profiles", exist_ok=True)
    return f"database/user_profiles/{user_id}_profile.json"

def load_existing_profile(user_id: str) -> Optional[UserProfile]:
    """Load existing profile from file if it exists."""
    profile_path = get_profile_path(user_id)
    
    if os.path.exists(profile_path):
        try:
            with open(profile_path, "r") as f:
                data = json.load(f)
            return UserProfile(**data)
        except Exception as e:
            print(f"Warning: Could not load existing profile - {e}")
            return None
    
    return None

def save_profile(user_id: str, profile: UserProfile) -> str:
    """Save profile to file and return path."""
    profile_path = get_profile_path(user_id)
    
    with open(profile_path, "w") as f:
        json.dump(profile.model_dump(), f, indent=2)
    
    print(f"✅ Profile saved: {profile_path}")
    return profile_path

def profile_exists(user_id: str) -> bool:
    """Check if profile file exists."""
    return os.path.exists(get_profile_path(user_id))

# ===== UTILITY FUNCTIONS =====

def encode_file(path: str) -> tuple[str, str]:
    """Encode file to base64 and determine MIME type."""
    with open(path, "rb") as f:
        encoded = base64.standard_b64encode(f.read()).decode("utf-8")
    
    mime_map = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".gif": "image/gif", ".webp": "image/webp", ".mp3": "audio/mp3",
        ".wav": "audio/wav", ".m4a": "audio/mp4", ".ogg": "audio/ogg"
    }
    
    ext = Path(path).suffix.lower()
    mime = mime_map.get(ext, "application/octet-stream")
    
    return encoded, mime

def build_multimodal_human_message(text: str, media_files: List[dict]) -> HumanMessage:
    """
    Build a single multimodal HumanMessage following smart_chat.py pattern.
    
    This uses the exact same structure as smart_chat.py's _convert_to_langchain_message:
    - Stores media metadata in additional_kwargs
    - Converts to proper LangChain multimodal format
    - Supports text, images, and audio in a unified message
    
    Args:
        text: User's text input
        media_files: List of dicts with 'type' and 'path' keys
    
    Returns:
        HumanMessage with multimodal content array
    """
    content_parts = []
    
    # Add text first if present
    if text and text.strip():
        content_parts.append({
            "type": "text",
            "text": text
        })
    
    # Process all media files and add to content
    for item in media_files:
        media_type = item.get("type", "").lower()
        path = item.get("path")
        
        if not path or not os.path.exists(path):
            continue
        
        try:
            base64_data, mime = encode_file(path)
            
            if media_type == "image":
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{base64_data}"}
                })
            
            elif media_type == "audio":
                content_parts.append({
                    "type": "media",
                    "mime_type": mime,
                    "data": base64_data
                })
            
            elif media_type == "text":
                with open(path, "r") as f:
                    text_content = f.read()
                content_parts.append({
                    "type": "text",
                    "text": f"\n[Additional text input]:\n{text_content}"
                })
        
        except Exception as e:
            print(f"Warning: Could not process {media_type} file {path} - {e}")
            continue
    
    # Return HumanMessage with multimodal content array (smart_chat.py pattern)
    return HumanMessage(content=content_parts)

# ===== EXTRACTION & REFINEMENT =====

def regenerate_profile_json(text: str, media_files: List[dict], existing_profile: Optional[Dict[str, Any]] = None) -> str:
    """
    Generate complete profile JSON from all inputs (text + media + existing profile).
    
    Always regenerates the full profile by:
    1. Reading existing profile data (if provided)
    2. Analyzing new inputs (text, images, audio, test results)
    3. Merging intelligently: preserve valid existing data, update with new discoveries
    4. Returning complete structured JSON
    
    This is a unified approach - no separate extract/refine logic.
    """
    
    # Build instruction - use .replace() instead of .format() to avoid KeyError from JSON braces
    existing_profile_block = ""
    if existing_profile:
        existing_profile_block = f"""
### EXISTING PROFILE DATA (to be updated):
```json
{json.dumps(existing_profile, ensure_ascii=False, indent=2)}
```
"""

    # Use .replace() to avoid KeyError from JSON braces in existing_profile_block
    instruction_text = PROFILE_EXTRACTOR_INSTRUCTION_TEMPLATE.replace(
        "{existing_profile_block}", existing_profile_block
    ).replace(
        "{new_text}", text
    )
    
    # Build a single multimodal message with all content
    # The main text is now the detailed instruction prompt
    final_message = build_multimodal_human_message(instruction_text, media_files)
    
    # System message emphasizing the desired output format and behavior
    system_message = SystemMessage(content=PROFILE_EXTRACTOR_OUTPUT_SYSTEM)
    
    # Invoke LLM
    messages = [system_message, final_message]
    response = llm.invoke(messages).content
    
    print(f"\n🤖 LLM Raw Response (first 500 chars):\n{response[:500]}")
    print(f"\n🤖 LLM Raw Response (last 300 chars):\n...{response[-300:]}")
    
    # Clean up response (remove markdown wrapping and extract JSON)
    cleaned = response.strip()
    
    # Remove markdown code blocks
    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned:
        parts = cleaned.split("```")
        # Find the part that looks like JSON (starts with {)
        for part in parts:
            part = part.strip()
            if part.startswith('{'):
                cleaned = part
                break
    
    # Extract JSON object if embedded in text
    start_idx = cleaned.find('{')
    end_idx = cleaned.rfind('}')
    
    if start_idx >= 0 and end_idx > start_idx:
        cleaned = cleaned[start_idx:end_idx+1]
    
    # Validate it's parseable JSON before returning
    try:
        json.loads(cleaned)  # Test parse
        return cleaned
    except json.JSONDecodeError as e:
        print(f"Warning: LLM response is not valid JSON: {e}")
        print(f"Response preview: {cleaned[:300]}...")
        # Return as-is and let caller handle the error
        return cleaned

# Old extract/refine logic removed - now using unified regenerate_profile_json()

# ===== LANGGRAPH NODES =====

def load_profile_node(state: State) -> State:
    """Load existing profile if available (for merging)."""
    # If profile provided upstream, use it (stateless mode)
    if state.get("existing_profile") or state.get("existing_profile_json"):
        print(f"🧾 Using provided existing profile for {state['user_id']}")
    elif state.get("persist"):
        # Load from disk if persistence enabled
        existing = load_existing_profile(state["user_id"])
        state["existing_profile"] = existing
        if existing:
            print(f"📂 Loaded existing profile for {state['user_id']}")
        else:
            print(f"📝 No existing profile for {state['user_id']}")
    else:
        print(f"📝 No existing profile for {state['user_id']}")
    
    state["operation"] = "update"  # Always use unified update approach
    return state

def update_profile_node(state: State) -> State:
    """
    Generate/update profile using unified approach.
    
    Always regenerates complete profile by merging:
    - Existing profile data (if any)
    - New input message
    - Media files
    """
    
    print("🤖 Regenerating complete user profile...")
    
    # Get existing profile dict (if available)
    existing_profile_dict = None
    if state.get("existing_profile_json"):
        try:
            existing_profile_dict = json.loads(state["existing_profile_json"])
        except:
            pass
    elif state.get("existing_profile"):
        existing_profile_dict = state["existing_profile"].model_dump()
    
    # Generate complete profile
    json_str = regenerate_profile_json(
        text=state["message"],
        media_files=state["media"],
        existing_profile=existing_profile_dict
    )
    
    # Parse and validate with better error handling
    try:
        # Try to extract JSON if wrapped in text
        json_str_clean = json_str.strip()
        
        # Find JSON object boundaries
        start_idx = json_str_clean.find('{')
        end_idx = json_str_clean.rfind('}')
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str_clean = json_str_clean[start_idx:end_idx+1]
        
        profile_data = json.loads(json_str_clean)
        profile_data["user_id"] = state["user_id"]
        profile = UserProfile(**profile_data)
        print(f"   ✅ Profile regenerated successfully")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"   ⚠️ JSON parsing error - {e}")
        print(f"   Raw response (first 500 chars): {json_str[:500]}...")
        print(f"   Raw response (last 200 chars): ...{json_str[-200:]}")
        # Fallback to existing or empty profile
        if state.get("existing_profile"):
            profile = state["existing_profile"]
            print(f"   Using existing profile as fallback")
        else:
            profile = UserProfile(user_id=state["user_id"])
            print(f"   Using empty profile as fallback")
    
    state["profile"] = profile
    state["history"].append({
        "timestamp": datetime.now().isoformat(),
        "operation": "regenerate",
        "action": "MERGE",
        "media_types": [m.get("type") for m in state["media"] if m.get("type")]
    })
    
    write_event("profile_regenerated", {
        "user_id": state.get("user_id"),
        "had_existing": bool(existing_profile_dict),
        "confidence": profile.metadata.confidence
    })
    
    return state

def cleanup_node(state: State) -> State:
    """Remove low-confidence or stale data."""
    profile = state["profile"]
    
    if profile.metadata.confidence < 0.7:
        # Example cleanup: clear inferred traits if confidence is low
        profile.psychological_profile = PsychologicalProfile()
        print("   Cleaned low-confidence psychological data")
    
    state["history"].append({
        "timestamp": datetime.now().isoformat(),
        "operation": "cleanup"
    })
    
    return state

def save_profile_node(state: State) -> State:
    """Save profile to file."""
    # No-op when persistence is disabled
    if state.get("persist"):
        save_profile(state["user_id"], state["profile"])
        state["profile_path"] = get_profile_path(state["user_id"])
        write_event("profile_saved", {
            "user_id": state.get("user_id"),
            "profile_path": state["profile_path"],
            "confidence": state["profile"].metadata.confidence
        })
    else:
        state["profile_path"] = ""
    
    state["history"].append({
        "timestamp": datetime.now().isoformat(),
        "operation": "save",
        "file_path": state["profile_path"]
    })
    
    return state

# ===== GRAPH CONSTRUCTION =====

def build_agent():
    """Build and compile LangGraph workflow - simplified unified approach."""
    graph = StateGraph(State)
    
    # Add nodes - simplified to single update path
    graph.add_node("load_profile", load_profile_node)
    graph.add_node("update", update_profile_node)
    graph.add_node("cleanup", cleanup_node)
    graph.add_node("save", save_profile_node)
    
    # Add edges - linear flow (no routing)
    graph.add_edge(START, "load_profile")
    graph.add_edge("load_profile", "update")
    graph.add_edge("update", "cleanup")
    graph.add_edge("cleanup", "save")
    graph.add_edge("save", END)
    
    return graph.compile()

# ===== PUBLIC API =====

def process_input(
    user_id: str,
    message: str,
    media: Optional[List[dict]] = None,
    existing_profile: Optional[dict] = None,
    persist: bool = False,
) -> dict:
    """
    Process user input and generate/update profile using unified approach.
    
    Always regenerates complete profile by intelligently merging:
    - Existing profile data (if provided)
    - New message content (text/multimodal)
    - Media files (images, audio)
    
    Args:
        user_id: Unique user identifier
        message: User message with new information
        media: List of media files [{"type": "image|audio|text", "path": "/path/to/file"}]
        existing_profile: Existing profile dict to merge with (optional)
        persist: Whether to save to disk (default: False for stateless operation)
    
    Returns:
        Dictionary containing:
        - user_id: Input user ID
        - profile: Profile as dictionary
        - profile_json: Profile as formatted JSON string
        - profile_path: Path to saved profile file (if persist=True)
        - action: Action performed (always "MERGE" now)
        - confidence: Extraction confidence score
        - operations: Number of operations performed
        - history: List of all operations
        - last_updated: ISO timestamp
    """
    
    agent = build_agent()
    
    # Prepare existing profile if provided
    existing_model: Optional[UserProfile] = None
    existing_json_str: Optional[str] = None
    if existing_profile:
        try:
            existing_model = UserProfile(**existing_profile)
        except Exception:
            existing_json_str = json.dumps(existing_profile)

    state = State(
        user_id=user_id,
        message=message,
        media=media or [],
        profile=UserProfile(user_id=user_id),
        existing_profile=existing_model,
        existing_profile_json=existing_json_str,
        history=[],
        context="",
        operation="update",
        profile_path="",
        persist=persist,
    )
    
    result = agent.invoke(state)
    
    # Extract action from history (always MERGE now)
    action = "MERGE"
    for entry in result["history"]:
        if entry.get("action"):
            action = entry["action"]
            break
    
    return {
        "user_id": result["user_id"],
        "profile": result["profile"].model_dump(),
        "profile_json": result["profile"].model_dump_json(indent=2),
        "profile_path": result["profile_path"],
        "action": action,
        "confidence": result["profile"].metadata.confidence,
        "operations": len([h for h in result["history"] if h["operation"] != "save"]),
        "history": result["history"],
        "last_updated": result["profile"].metadata.last_updated
    }

# ===== UTILITY FUNCTIONS FOR MANAGEMENT =====

def get_profile(user_id: str) -> Optional[UserProfile]:
    """Get profile for user without processing."""
    return load_existing_profile(user_id)

def delete_profile(user_id: str) -> bool:
    """Delete profile file for user."""
    profile_path = get_profile_path(user_id)
    if os.path.exists(profile_path):
        os.remove(profile_path)
        print(f"🗑️  Profile deleted: {profile_path}")
        return True
    return False

def list_profiles() -> List[str]:
    """List all user profiles."""
    profiles_dir = "database/user_profiles"
    if not os.path.exists(profiles_dir):
        return []
    
    profiles = [f.replace("_profile.json", "") for f in os.listdir(profiles_dir) if f.endswith("_profile.json")]
    return profiles

def get_profile_stats(user_id: str) -> Optional[dict]:
    """Get statistics about a user's profile."""
    profile = load_existing_profile(user_id)
    if not profile:
        return None
    
    # Calculate completeness score based on the new structure
    core_fields = profile.core_info
    prof_fields = profile.professional_profile
    social_fields = profile.social_profile
    lifestyle_fields = profile.lifestyle
    outlook_fields = profile.personal_outlook
    psych_fields = profile.psychological_profile
    
    completeness_score = sum([
        1 if core_fields.name else 0,
        1 if core_fields.age else 0,
        1 if prof_fields.skills else 0,
        1 if social_fields.relationship_status else 0,
        1 if lifestyle_fields.routines else 0,
        1 if outlook_fields.interests else 0,
        1 if outlook_fields.goals else 0,
        1 if outlook_fields.values else 0,
        1 if psych_fields.summary else 0,
    ]) / 9 * 100

    return {
        "user_id": user_id,
        "name": profile.core_info.name,
        "confidence": profile.metadata.confidence,
        "last_updated": profile.metadata.last_updated,
        "data_completeness": f"{completeness_score:.2f}%",
        "extracted_sources": profile.metadata.extracted_from,
        "skills_count": len(profile.professional_profile.skills),
        "interests_count": len(profile.personal_outlook.interests),
        "relations_count": len(profile.social_profile.relations),
        "file_path": get_profile_path(user_id)
    }