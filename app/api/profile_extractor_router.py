from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import tempfile
import os
import json
import time

from app.services.profile_extract_agent_json import process_input, UserProfile
from logging_utils import log, write_event

router = APIRouter(prefix="/profile", tags=["profile-extraction"])


class ProfileInput(BaseModel):
    user_id: Optional[str] = None
    user_profile: Optional[dict] = None
    text_messages: List[str] = []
    conversation_history: Optional[List[dict]] = None


@router.post("/extract")
async def extract_profile(
    user_id: Optional[str] = Form(None),
    user_profile: Optional[str] = Form(None),
    text_messages: Optional[str] = Form(None),
    images: Optional[List[UploadFile]] = File(None),
    audios: Optional[List[UploadFile]] = File(None)
):
    """
    Generate/update user profile from unified multimodal inputs.
    
    Uses a simplified unified approach that always regenerates the complete profile by:
    - Reading existing profile data (if provided)
    - Analyzing new inputs (text, images, audio, test results)
    - Merging intelligently: preserve valid existing data, add new discoveries, update contradictions
    
    All inputs (text + images + audio) are processed together as a single
    multimodal message to the AI for comprehensive analysis.
    
    Args:
        user_id: User identifier (optional, auto-generated if not provided)
        user_profile: JSON string of existing profile to merge with (optional)
        text_messages: JSON array of text messages or single text (test results, conversations, etc.)
        images: Multiple image files (analyzed for physical attributes, visible text, context)
        audios: Multiple audio files (analyzed for transcription, voice characteristics, personal info)
    
    Returns:
        Complete regenerated user profile JSON with merged data from all sources
        
    Note:
        This endpoint always returns a complete profile, whether updating existing or creating new.
        The agent intelligently merges existing data with new inputs.
    """
    temp_files = []
    
    try:
        # Generate user_id if not provided
        if not user_id:
            import hashlib
            user_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        
        # Parse provided existing profile JSON text (no persistence)
        profile_data = None
        saved_profile_source = None
        if user_profile:
            try:
                # Handle both JSON string and already-parsed dict
                if isinstance(user_profile, str):
                    profile_data = json.loads(user_profile)
                elif isinstance(user_profile, dict):
                    profile_data = user_profile
                saved_profile_source = "string"
                log.info(f"Parsed profile data: {type(profile_data)}")
            except Exception as e:
                log.warning(f"Could not parse provided profile JSON text: {e}")
                log.warning(f"Profile preview: {str(user_profile)[:200]}")
        
        # Parse text messages
        combined_text = ""
        if text_messages:
            try:
                # Handle both JSON string and already-parsed list
                if isinstance(text_messages, str):
                    msgs = json.loads(text_messages)
                    combined_text = "\n".join(msgs) if isinstance(msgs, list) else str(msgs)
                elif isinstance(text_messages, list):
                    combined_text = "\n".join(text_messages)
                else:
                    combined_text = str(text_messages)
            except Exception as e:
                log.warning(f"Could not parse text_messages: {e}")
                combined_text = str(text_messages)
        
        if not combined_text.strip():
            combined_text = "Extract comprehensive profile information from all provided media inputs."
        
        # Handle media files - these will be processed together with text as unified multimodal input
        media_inputs = []
        
        if images:
            for img in images:
                temp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                temp.write(await img.read())
                temp.close()
                media_inputs.append({"type": "image", "path": temp.name})
                temp_files.append(temp.name)
        
        if audios:
            for aud in audios:
                temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
                temp.write(await aud.read())
                temp.close()
                media_inputs.append({"type": "audio", "path": temp.name})
                temp_files.append(temp.name)
        
        # Log request details
        write_event("profile_regenerate_request", {
            "user_id": user_id,
            "has_existing_profile": bool(profile_data),
            "profile_source": saved_profile_source,
            "text_length": len(combined_text or ""),
            "images_count": len(images or []),
            "audios_count": len(audios or []),
            "has_media": bool(media_inputs)
        })
        
        log.info(f"Processing profile for user {user_id}: "
                f"existing={'yes' if profile_data else 'no'}, "
                f"text={len(combined_text)} chars, "
                f"media={len(media_inputs)} files")

        # Process with unified agent - always regenerates complete profile
        # Merges existing profile (if provided) with new inputs intelligently
        result = process_input(
            user_id=user_id,
            message=combined_text,
            media=media_inputs,
            existing_profile=profile_data,
            persist=False  # Stateless: do not save to disk
        )

        # Log successful response
        write_event("profile_regenerate_response", {
            "user_id": result["user_id"],
            "confidence": result.get("confidence"),
            "action": result.get("action"),  # Always "MERGE" now
            "last_updated": result.get("last_updated"),
            "operations": result.get("operations")
        })
        
        log.info(f"Profile regenerated for user {user_id}: "
                f"confidence={result.get('confidence'):.2f}, "
                f"ops={result.get('operations')}")
        
        # Return the profile dict directly (FastAPI will serialize to JSON)
        return result["profile"]
    
    except json.JSONDecodeError as e:
        log.exception("/profile/extract JSON decode failed")
        raise HTTPException(status_code=500, detail=f"JSON parsing error: {str(e)}")
    except Exception as e:
        log.exception("/profile/extract failed")
        import traceback
        error_detail = f"{type(e).__name__}: {str(e)}"
        log.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_detail)
    
    finally:
        # Cleanup temp files
        for f in temp_files:
            try:
                os.remove(f)
            except:
                pass


@router.post("/extract-json")
async def extract_profile_json(input_data: ProfileInput):
    """
    Generate/update user profile from JSON input (text-only, no media).
    
    Uses unified approach - always regenerates complete profile by intelligently
    merging existing profile data with new text inputs (messages, conversations).
    
    Args:
        input_data: {
            user_id: user identifier (optional, auto-generated if not provided),
            user_profile: existing profile dict to merge with (optional),
            text_messages: array of text messages (test results, user info, etc.),
            conversation_history: array of {role, content} for context (optional)
        }
    
    Returns:
        Complete regenerated user profile JSON with merged data from all text sources
        
    Note:
        This is the JSON-only version of /extract. For multimodal inputs (images, audio),
        use the /extract endpoint with form-data.
    """
    try:
        # Generate user_id if not provided
        user_id = input_data.user_id
        if not user_id:
            import hashlib
            user_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        
        # Stateless: do not save existing profile
        
        # Combine text inputs
        combined_text = ""
        
        if input_data.text_messages:
            combined_text += "\n".join(input_data.text_messages)
        
        if input_data.conversation_history:
            conv_text = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}" 
                for msg in input_data.conversation_history
            ])
            combined_text += f"\n\nConversation:\n{conv_text}"
        
        if not combined_text.strip():
            raise HTTPException(status_code=400, detail="No input messages provided")
        
        # Log request
        write_event("profile_regenerate_json_request", {
            "user_id": user_id,
            "has_existing_profile": bool(input_data.user_profile),
            "text_length": len(combined_text),
            "has_conversation": bool(input_data.conversation_history)
        })
        
        log.info(f"Processing profile (JSON) for user {user_id}: "
                f"existing={'yes' if input_data.user_profile else 'no'}, "
                f"text={len(combined_text)} chars")
        
        # Process with unified agent - always regenerates complete profile
        result = process_input(
            user_id=user_id,
            message=combined_text,
            media=[],  # No media for JSON endpoint
            existing_profile=input_data.user_profile,
            persist=False  # Stateless
        )
        
        # Log response
        write_event("profile_regenerate_json_response", {
            "user_id": result["user_id"],
            "confidence": result.get("confidence"),
            "action": result.get("action"),
            "operations": result.get("operations")
        })
        
        log.info(f"Profile regenerated (JSON) for user {user_id}: "
                f"confidence={result.get('confidence'):.2f}")

        # Return the profile dict directly (FastAPI will serialize to JSON)
        return result["profile"]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
