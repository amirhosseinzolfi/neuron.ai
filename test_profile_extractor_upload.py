"""Test script for /profile/extract endpoint using profile JSON TEXT (stateless).

Runs a sequence:
1. Send existing profile as JSON text + text update
2. Optionally include image/audio if available
3. Prints final JSON profile text returned by the API (no persistence)

Requires API running (port 15800 per app/main.py).
"""
import json
import os
import time
from pathlib import Path
import requests

BASE_URL = "http://localhost:15800"
EXTRACT_ENDPOINT = f"{BASE_URL}/profile/extract"

USER_ID = "upload_user_001"

EXISTING_PROFILE = {
    "user_id": USER_ID,
    "core_info": {"name": "Alice Brown", "age": 31, "occupation": "Data Analyst"},
    "professional_profile": {"career_summary": "Works with data", "skills": ["python"], "job_history": []},
    "social_profile": {"relationship_status": None, "relations": []},
    "lifestyle": {"summary": None, "routines": []},
    "personal_outlook": {"interests": ["running"], "goals": [], "values": []},
    "psychological_profile": {"summary": None, "personality_traits": {}, "cognitive_biases": [], "strengths": [], "areas_for_development": []},
    "psychological_tests": [],
    "additional_data": {},
    "metadata": {"confidence": 0.65, "extracted_from": ["text"], "last_updated": "2025-01-01T00:00:00"}
}

TEXT_UPDATE = "I recently transitioned to machine learning engineering. I value curiosity and integrity."


def _maybe_media():
    root = Path("/root/blue-psychology-test")
    img_candidates = list(root.glob("**/*.png")) + list(root.glob("**/*.jpg"))
    aud_candidates = list(root.glob("**/*.wav")) + list(root.glob("**/*.mp3"))
    image = next((str(p) for p in img_candidates if p.is_file()), None)
    audio = next((str(p) for p in aud_candidates if p.is_file()), None)
    return image, audio


def _unwrap_profile(obj):
    """Return the inner profile dict if wrapped; otherwise return obj itself."""
    if isinstance(obj, dict) and "profile" in obj and isinstance(obj["profile"], dict):
        return obj["profile"]
    return obj


def send_with_profile_text(text: str, include_media: bool):
    files = {}
    image_path, audio_path = _maybe_media() if include_media else (None, None)
    if image_path:
        files["images"] = (os.path.basename(image_path), open(image_path, "rb"), "image/jpeg")
    if audio_path:
        files["audios"] = (os.path.basename(audio_path), open(audio_path, "rb"), "audio/wav")

    data = {
        "user_id": USER_ID,
        "text_messages": text,
        "user_profile": json.dumps(EXISTING_PROFILE)
    }

    # Structured request log
    print("\n" + "-" * 80)
    print("REQUEST")
    print("-" * 80)
    print(f"Endpoint: {EXTRACT_ENDPOINT}")
    print(f"User ID: {USER_ID}")
    print(f"Include media: {include_media}")
    print("Input Profile JSON (text):")
    print(json.dumps(EXISTING_PROFILE, indent=2))
    print("Input Message:")
    print(text)
    if image_path or audio_path:
        print("Media:")
        if image_path:
            print(f"  - image: {image_path}")
        if audio_path:
            print(f"  - audio: {audio_path}")

    print("\n➡️  Sending request ...")
    start = time.time()
    resp = requests.post(EXTRACT_ENDPOINT, data=data, files=files if files else None)
    elapsed = time.time() - start

    # Close file handles
    for f in files.values():
        if isinstance(f, tuple):
            try:
                f[1].close()
            except Exception:
                pass

    # Structured response log
    print("\n" + "-" * 80)
    print("RESPONSE")
    print("-" * 80)
    print(f"Status: {resp.status_code}")
    print(f"Latency: {elapsed:.2f}s")
    if resp.status_code != 200:
        print("Body:")
        print(resp.text)
        return None

    body = None
    try:
        body = resp.json()
    except Exception:
        body = resp.text

    # The API returns either a JSON object or a JSON string representing the profile or wrapper.
    if isinstance(body, str):
        try:
            parsed = json.loads(body)
        except Exception:
            # attempt to fix single-quote dict-like strings
            fixed = body.replace("'", '"')
            parsed = json.loads(fixed)
    else:
        parsed = body

    final_profile = _unwrap_profile(parsed)

    # Pretty print final output
    print("\nFinal Output JSON Profile:")
    try:
        print(json.dumps(final_profile, indent=2))
    except Exception:
        print(final_profile)

    # Quick summary
    try:
        name = final_profile.get("core_info", {}).get("name")
        age = final_profile.get("core_info", {}).get("age")
        occupation = final_profile.get("core_info", {}).get("occupation")
        print("\nSummary:")
        print(f"  - name: {name}")
        print(f"  - age: {age}")
        print(f"  - occupation: {occupation}")
    except Exception:
        pass

    return final_profile


def verify_shape(profile: dict) -> bool:
    if not isinstance(profile, dict):
        print("❌ Profile is not a dict")
        return False
    keys = ["core_info", "professional_profile", "social_profile", "personal_outlook", "psychological_profile", "metadata"]
    missing = [k for k in keys if k not in profile]
    if missing:
        print("⚠️ Missing keys:", missing)
        return False
    return True


def run():
    # Health check
    try:
        h = requests.get(f"{BASE_URL}/health")
        if h.status_code == 200:
            print("API healthy")
        else:
            print("Health status:", h.status_code)
    except Exception as e:
        print("Cannot reach API:", e)
        return

    # 1. Initial update with profile text only
    r1 = send_with_profile_text(TEXT_UPDATE, include_media=False)
    # 2. Update with media if available
    r2 = send_with_profile_text("Adding an image/audio for further refinement.", include_media=True)

    summary = {
        "initial_valid": verify_shape(r1) if r1 else False,
        "media_valid": verify_shape(r2) if r2 else False,
    }
    print("\n📊 Summary:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    run()