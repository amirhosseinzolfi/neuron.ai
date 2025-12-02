from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from pathlib import Path

from app.services.image_service import ImageGenerationService

router = APIRouter(prefix="/image", tags=["image-generation"])


class ImageRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000, description="Text prompt for image generation")
    model: Optional[str] = Field(default="flux", description="Image generation model")
    width: Optional[int] = Field(default=512, ge=256, le=2048, description="Image width")
    height: Optional[int] = Field(default=512, ge=256, le=2048, description="Image height")
    num_images: Optional[int] = Field(default=1, ge=1, le=4, description="Number of images to generate")


class ImageResponse(BaseModel):
    success: bool
    image_path: str
    model: str
    prompt: str


@router.post("/generate", response_model=ImageResponse)
async def generate_image(request: ImageRequest):
    """Generate image from text prompt and return the first generated image."""
    try:
        service = ImageGenerationService()
        image_files = await service.generate(
            prompt=request.text,
            model=request.model,
            width=request.width,
            height=request.height,
            num_images=request.num_images
        )
        
        if not image_files:
            raise HTTPException(status_code=500, detail="No images generated")
        
        # Return first image as file response
        image_file = image_files[0]
        return FileResponse(
            path=str(image_file),
            media_type="image/png",
            filename=image_file.name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-multiple")
async def generate_multiple_images(request: ImageRequest):
    """Generate multiple images from text prompt and return paths."""
    try:
        service = ImageGenerationService()
        image_files = await service.generate(
            prompt=request.text,
            model=request.model,
            width=request.width,
            height=request.height,
            num_images=request.num_images
        )
        
        if not image_files:
            raise HTTPException(status_code=500, detail="No images generated")
        
        return {
            "success": True,
            "count": len(image_files),
            "images": [
                {
                    "path": str(f),
                    "filename": f.name,
                    "url": f"/image/file/{f.name}"
                }
                for f in image_files
            ],
            "model": request.model,
            "prompt": request.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/file/{filename}")
async def get_image_file(filename: str):
    """Retrieve a generated image file by filename."""
    file_path = Path("generated_images") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(
        path=str(file_path),
        media_type="image/png",
        filename=filename
    )
