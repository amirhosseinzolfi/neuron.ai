import time
import random
import logging
import asyncio
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from g4f import Client
from PIL import Image, ImageDraw
import requests

logger = logging.getLogger(__name__)


class ImageGenerationService:
    def __init__(self):
        self.client = Client()
        self.output_dir = Path("generated_images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = 120
        self.executor = ThreadPoolExecutor(max_workers=2)

    async def generate(
        self,
        prompt: str,
        model: str = "flux",
        width: int = 512,
        height: int = 512,
        num_images: int = 1
    ) -> list[Path]:
        """Generate images from text prompt."""
        g4f_models = [
            "dall-e-3", "midjourney", "flux", "sdxl", "sdxl-lora", 
            "sd-3", "playground-v2.5", "flux-pro", "flux-dev", 
            "flux-realism", "flux-anime", "flux-3d", "flux-4o", "any-dark"
        ]
        
        generated_files = []
        timestamp = int(time.time())
        loop = asyncio.get_event_loop()
        
        for i in range(num_images):
            try:
                if model in g4f_models:
                    file_path = await loop.run_in_executor(
                        self.executor,
                        self._generate_g4f_sync,
                        prompt, model, width, height, i, timestamp
                    )
                else:
                    file_path = await loop.run_in_executor(
                        self.executor,
                        self._generate_text_to_image_sync,
                        prompt, model, width, height, i, timestamp
                    )
                generated_files.append(file_path)
            except Exception as e:
                logger.error(f"Failed to generate image {i+1}: {e}")
                dummy_path = self._create_dummy_image(
                    prompt, width, height, model, i, timestamp
                )
                generated_files.append(dummy_path)
        
        return generated_files

    def _generate_g4f_sync(
        self, 
        prompt: str, 
        model: str, 
        width: int, 
        height: int, 
        index: int,
        timestamp: int
    ) -> Path:
        """Generate image using g4f models (synchronous)."""
        start = time.time()
        
        if model.lower() == "flux" and "--ar" not in prompt:
            prompt += " --ar 16:9"
        
        response = self.client.images.generate(
            model=model,
            prompt=prompt,
            response_format="url",
            width=width,
            height=height,
            timeout=self.timeout
        )
        
        url = response.data[0].url
        file_path = self._download_image_sync(
            url, prompt, model, index, timestamp
        )
        
        logger.info(f"Image generated in {time.time()-start:.1f}s")
        return file_path

    def _generate_text_to_image_sync(
        self,
        prompt: str,
        model: str,
        width: int,
        height: int,
        index: int,
        timestamp: int
    ) -> Path:
        """Generate image using text_to_image method (synchronous)."""
        seed = random.randint(1, 10**6)
        image = self.client.text_to_image(
            prompt=prompt,
            model=model,
            height=height,
            width=width,
            seed=seed
        )
        
        filename = f"img_{timestamp}_{model}_{index}.jpeg"
        file_path = self.output_dir / filename
        image.save(file_path, format="JPEG")
        
        logger.info(f"Image saved: {file_path}")
        return file_path

    def _download_image_sync(
        self,
        url: str,
        prompt: str,
        model: str,
        index: int,
        timestamp: int
    ) -> Path:
        """Download image from URL (synchronous)."""
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            filename = f"img_{timestamp}_{model}_{index}.png"
            file_path = self.output_dir / filename
            
            file_path.write_bytes(response.content)
            logger.info(f"Image downloaded: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return self._create_dummy_image(prompt, 512, 512, model, index, timestamp)

    def _create_dummy_image(
        self,
        prompt: str,
        width: int,
        height: int,
        model: str,
        index: int,
        timestamp: int
    ) -> Path:
        """Create a dummy placeholder image on failure."""
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)
        draw.text(
            (width // 2, height // 2),
            f"Failed: {prompt[:50]}",
            fill="black",
            anchor="mm"
        )
        
        filename = f"dummy_{timestamp}_{model}_{index}.png"
        file_path = self.output_dir / filename
        image.save(file_path)
        
        return file_path
