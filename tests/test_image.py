import os
import io
from types import SimpleNamespace
from pathlib import Path
import pytest
from PIL import Image
from image_utils import generate_images_for_prompt
import image_utils as iu
import image_utils as iu
import image_utils as iu
import image_utils as iu

# Absolute import from the namespace package (same dir as image_utils.py)

def test_generate_images_for_prompt_non_g4f_creates_jpegs(tmp_path, monkeypatch):
    # Dummy client with text_to_image returning a PIL Image
    class DummyClient:
        def text_to_image(self, prompt, model, height, width, seed):
            return Image.new("RGB", (width, height), "white")

    # Replace the client in image_utils with our dummy
    monkeypatch.setattr(iu, "client", DummyClient(), raising=True)

    folder = tmp_path / "out"
    model = "custom-model"  # not in g4f_models => use text_to_image path
    imgs = generate_images_for_prompt(
        prompt="A serene landscape",
        index=1,
        folder_path=str(folder),
        model=model,
        num_images=2,
        width=320,
        height=200,
        task_id=None,
    )

    assert len(imgs) == 2
    for i, p in enumerate(imgs, start=1):
        assert Path(p).exists()
        assert p.endswith(f"personality_1_{model}_{i}.jpeg")

def test_generate_images_for_prompt_g4f_downloads_pngs_and_saves(tmp_path, monkeypatch):
    # Dummy client.images.generate returning a URL
    class DummyImages:
        def __init__(self):
            self.last_prompt = None

        def generate(self, model, prompt, response_format, width, height, timeout):
            self.last_prompt = prompt
            return SimpleNamespace(data=[SimpleNamespace(url="http://example.com/fake.png")])

    class DummyClient:
        def __init__(self):
            self.images = DummyImages()

    # Fake requests.get that returns binary content
    class FakeResp:
        content = b"\x89PNG\r\n\x1a\nfake"
        def raise_for_status(self): pass

    monkeypatch.setattr(iu, "client", DummyClient(), raising=True)
    monkeypatch.setattr(iu.requests, "get", lambda url, timeout: FakeResp(), raising=True)

    folder = tmp_path / "g4f"
    model = "flux"  # in g4f_models => use g4f path
    imgs = generate_images_for_prompt(
        prompt="Sci-fi city at dusk",
        index=7,
        folder_path=str(folder),
        model=model,
        num_images=3,
        width=256,
        height=256,
        task_id=None,
    )

    assert len(imgs) == 3
    for i, p in enumerate(imgs, start=1):
        assert Path(p).exists()
        assert p.endswith(f"img_7_{model}_{i}.png")

def test_generate_images_for_prompt_midjourney_adds_aspect_ratio(tmp_path, monkeypatch):
    captured = {"prompt": None}

    class DummyImages:
        def generate(self, model, prompt, response_format, width, height, timeout):
            captured["prompt"] = prompt
            return SimpleNamespace(data=[SimpleNamespace(url="http://example.com/fake.png")])

    class DummyClient:
        def __init__(self):
            self.images = DummyImages()

    class FakeResp:
        content = b"\x89PNG\r\n\x1a\nfake"
        def raise_for_status(self): pass

    monkeypatch.setattr(iu, "client", DummyClient(), raising=True)
    monkeypatch.setattr(iu.requests, "get", lambda url, timeout: FakeResp(), raising=True)

    folder = tmp_path / "mid"
    imgs = generate_images_for_prompt(
        prompt="A dragon flying over mountains",
        index=2,
        folder_path=str(folder),
        model="midjourney",
        num_images=1,
        width=512,
        height=512,
        task_id=None,
    )

    assert len(imgs) == 1
    assert Path(imgs[0]).exists()
    # Ensure aspect ratio flag was appended for midjourney
    assert "--ar 16:9" in captured["prompt"]

def test_generate_images_for_prompt_g4f_failure_creates_dummy(tmp_path, monkeypatch):
    # Force client.images.generate to raise, to trigger dummy fallback
    class FailingImages:
        def generate(self, *args, **kwargs):
            raise RuntimeError("simulated failure")

    class DummyClient:
        def __init__(self):
            self.images = FailingImages()

    monkeypatch.setattr(iu, "client", DummyClient(), raising=True)

    folder = tmp_path / "fail"
    model = "flux"
    imgs = generate_images_for_prompt(
        prompt="Abstract geometry",
        index=5,
        folder_path=str(folder),
        model=model,
        num_images=2,
        width=128,
        height=128,
        task_id=None,
    )

    # When top-level catches, it returns whatever it collected (empty if failure happened before append)
    # However, generate_image_g4f handles its own exception and returns a dummy file path,
    # so we should still get 2 images.
    assert len(imgs) == 2
    for p in imgs:
        assert Path(p).exists()
        assert Path(p).name.startswith(f"dummy_{model}_5_")

@pytest.mark.skipif(not os.getenv("RUN_INTERACTIVE_TESTS"), reason="Interactive test skipped by default")
def test_generate_images_for_prompt_interactive(tmp_path):
    # This interactive test asks user for model and prompt, then tries to generate 1 image.
    model = input("Enter image model (e.g., flux, midjourney, custom-model): ").strip()
    prompt = input("Enter prompt to generate image: ").strip()
    folder = tmp_path / "interactive"
    imgs = generate_images_for_prompt(
        prompt=prompt or "A calm beach at sunset",
        index=1,
        folder_path=str(folder),
        model=model or "custom-model",
        num_images=1,
        width=256,
        height=256,
        task_id=None,
    )
    assert len(imgs) == 1
    assert Path(imgs[0]).exists()