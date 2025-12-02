# Profile Extractor Fixes

## Issues Fixed

### 1. API Key Configuration
**Problem**: Profile extractor was using hardcoded API key instead of environment variable.

**Solution**: 
- Added `get_profile_extractor_llm()` function in `ai_utils.py` to use `GOOGLE_API_KEY_PROFILE` from `.env`
- Updated `profile_extract_agent_json.py` to load API key from environment variable `GOOGLE_API_KEY_PROFILE`

### 2. JSON Parsing Error
**Problem**: API was returning malformed JSON with error: `{"detail":"'\n   \"core_info\"'"}`

**Root Cause**: 
- The FastAPI router was returning `result["profile_json"]` which is a JSON string
- When FastAPI serializes a string response, it was being double-encoded
- The client was trying to parse this double-encoded JSON, causing the error

**Solution**:
- Changed router to return `result["profile"]` (dict) instead of `result["profile_json"]` (string)
- FastAPI automatically serializes dict to proper JSON response
- Updated JSON parsing in `ai_utils.py` to handle both dict and string responses properly
- Added proper JSON encoding with `separators=(',', ':')` to minimize whitespace

## Files Modified

### 1. `/root/blue-psychology-test/ai_utils.py`
- Added `get_profile_extractor_llm()` function with `GOOGLE_API_KEY_PROFILE`
- Fixed JSON encoding in form_data payload (added `separators` parameter)
- Improved response parsing logic to handle both JSON objects and strings

### 2. `/root/blue-psychology-test/app/services/profile_extract_agent_json.py`
- Added `dotenv` import and `load_dotenv()` call
- Changed hardcoded API key to `os.getenv("GOOGLE_API_KEY_PROFILE", fallback)`

### 3. `/root/blue-psychology-test/app/api/profile_extractor_router.py`
- Changed return value from `result["profile_json"]` to `result["profile"]` in both endpoints
- This ensures FastAPI returns proper JSON object instead of double-encoded string

## Testing

To verify the fixes work:

```bash
# 1. Ensure the profile extractor API is running
python -m app.main

# 2. Run a test with the psychology test bot
# The profile should now update successfully without JSON parsing errors
```

## Environment Variable

Make sure `.env` contains:
```
GOOGLE_API_KEY_PROFILE=your_google_api_key_profile
```

## Expected Behavior

After these fixes:
1. ✅ Profile extractor uses dedicated API key from environment
2. ✅ API returns properly formatted JSON (not double-encoded)
3. ✅ Client successfully parses and saves updated profile
4. ✅ No more `{"detail":"'\n   \"core_info\"'"}` errors
