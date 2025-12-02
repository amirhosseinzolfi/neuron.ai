# Profile Extractor Fix - Complete Summary

## ✅ Problem Solved

The profile extractor was failing with error: `{"detail":"'\n   \"core_info\"'"}` (KeyError)

## Root Cause

The `PROFILE_EXTRACTOR_INSTRUCTION_TEMPLATE` uses Python's `.format()` method with placeholders `{existing_profile_block}` and `{new_text}`. When we inserted JSON data into `existing_profile_block`, that JSON contained `{` and `}` characters which Python's `.format()` interpreted as additional placeholders, causing a KeyError.

## Solution

Changed from `.format()` to `.replace()` method to avoid interpreting JSON braces as placeholders:

```python
# BEFORE (caused KeyError):
instruction_text = PROFILE_EXTRACTOR_INSTRUCTION_TEMPLATE.format(
    existing_profile_block=existing_profile_block,
    new_text=text,
)

# AFTER (works correctly):
instruction_text = PROFILE_EXTRACTOR_INSTRUCTION_TEMPLATE.replace(
    "{existing_profile_block}", existing_profile_block
).replace(
    "{new_text}", text
)
```

## Changes Made

### 1. **ai_utils.py**
- ✅ Added `get_profile_extractor_llm()` using `GOOGLE_API_KEY_PROFILE`
- ✅ Improved JSON parsing in `_call_profile_extractor_api()`
- ✅ Better error handling for API responses

### 2. **app/services/profile_extract_agent_json.py**
- ✅ Uses `GOOGLE_API_KEY_PROFILE` from environment
- ✅ Fixed `.format()` → `.replace()` to avoid KeyError
- ✅ Added robust JSON extraction from LLM responses
- ✅ Better error logging with response previews

### 3. **app/api/profile_extractor_router.py**
- ✅ Returns dict instead of JSON string (prevents double-encoding)
- ✅ Better error handling with detailed messages
- ✅ Handles both string and dict inputs

## Test Results

```bash
$ python3 test_profile_direct.py

🧪 Direct Profile Extraction Test
============================================================
🧾 Using provided existing profile for test_user_123
🤖 Regenerating complete user profile...
   ✅ Profile regenerated successfully
✅ SUCCESS!
   User ID: test_user_123
   Confidence: 0.80
   Action: MERGE

📊 Profile:
   Name: Test User
   Age: 26

✅ Test PASSED
```

## Environment Setup

Ensure `.env` contains:
```
GOOGLE_API_KEY_PROFILE=YOUR_API_KEY_HERE
```

## Usage

The profile extractor now works correctly in both modes:

1. **Direct Python API:**
```python
from app.services.profile_extract_agent_json import process_input

result = process_input(
    user_id="user_123",
    message="Test results...",
    existing_profile={...},
    persist=False
)
```

2. **FastAPI Endpoint:**
```bash
curl -X POST http://localhost:15800/profile/extract \
  -F "user_id=123" \
  -F "user_profile={...}" \
  -F "text_messages=[...]"
```

## Files for Testing

- `test_profile_direct.py` - Direct Python test (no API server needed)
- `test_profile_update.py` - API endpoint test (requires running server)

Both tests verify the profile extractor works correctly with real test data.
