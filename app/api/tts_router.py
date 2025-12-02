from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from pathlib import Path
import os

from app.services.tts_service import TTSService

router = APIRouter(prefix="/tts", tags=["text-to-speech"])

# Storage directory
VOICE_STORAGE_DIR = Path("tools/voice")


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice_model: Optional[str] = Field(default="gemini-2.5-flash-preview-tts")
    output_format: Optional[str] = Field(default="wav")
    voice: Optional[str] = Field(default=None)


@router.post("/generate")
async def generate_speech(request: TTSRequest):
    """Convert text to speech and return audio file path."""
    try:
        service = TTSService()
        audio_files = await service.generate(
            text=request.text,
            model=request.voice_model,
            output_format=request.output_format,
            voice=request.voice,
        )
        
        if not audio_files:
            raise HTTPException(status_code=500, detail="No audio generated")
        
        audio_file = audio_files[0]
        return FileResponse(
            path=str(audio_file),
            media_type=f"audio/{request.output_format}",
            filename=audio_file.name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voices")
async def list_voices():
    """List all generated voice files."""
    try:
        if not VOICE_STORAGE_DIR.exists():
            return {"voices": [], "total": 0, "storage_path": str(VOICE_STORAGE_DIR)}
        
        voices = []
        for file in sorted(VOICE_STORAGE_DIR.glob("*.wav"), key=os.path.getmtime, reverse=True):
            file_stat = file.stat()
            voices.append({
                "filename": file.name,
                "size_bytes": file_stat.st_size,
                "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                "created": file_stat.st_mtime,
                "download_url": f"/tts/voices/{file.name}"
            })
        
        return {
            "voices": voices,
            "total": len(voices),
            "storage_path": str(VOICE_STORAGE_DIR.absolute())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voices/{filename}")
async def download_voice(filename: str):
    """Download a specific generated voice file."""
    try:
        file_path = VOICE_STORAGE_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Voice file '{filename}' not found")
        
        # Security check: ensure file is within the storage directory
        if not str(file_path.resolve()).startswith(str(VOICE_STORAGE_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return FileResponse(
            path=str(file_path),
            media_type="audio/wav",
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/voices/{filename}")
async def delete_voice(filename: str):
    """Delete a specific generated voice file."""
    try:
        file_path = VOICE_STORAGE_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Voice file '{filename}' not found")
        
        # Security check: ensure file is within the storage directory
        if not str(file_path.resolve()).startswith(str(VOICE_STORAGE_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        
        file_path.unlink()
        return {"message": f"Voice file '{filename}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
