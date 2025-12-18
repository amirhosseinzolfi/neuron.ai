# /clear Command Analysis & Enhancement

## Overview
The `/clear` command has been enhanced to completely reset the user's bot experience, including clearing smart chat history and long-term memories.

## What Gets Cleared

### 1. **User Data** (from `database/bot.db`)
- ✅ Test results
- ✅ Purchased packages
- ✅ Psychology profile
- ✅ User progress and information

### 2. **Smart Chat History** (from `database/psychology_bot.db`)
- ✅ LangGraph conversation checkpoints
- ✅ All message history stored in SqliteSaver
- ✅ Clears both `checkpoints` and `checkpoint_writes` tables

### 3. **Long-term Memory** (Mem0 + Qdrant)
- ✅ All Mem0 memories for the user
- ✅ Stored facts and extracted information
- ✅ Conversation summaries

### 4. **Session State**
- ✅ Active smart chat session flag
- ✅ User context data

## What Gets Preserved

- 💰 **Wallet balance** - User's money is never deleted
- 🎁 **Gift status** - Whether user received the welcome gift

## Technical Implementation

### Architecture
The bot uses three separate storage systems:

1. **SQLite (bot.db)** - User profiles, test results, packages
2. **LangGraph SqliteSaver (psychology_bot.db)** - Chat conversation history
3. **Mem0 + Qdrant** - Long-term semantic memory

### Code Changes

#### File: `telegram_handlers.py`

**Function: `clear_data()`**
- Updated warning message to inform users that chat history and memories will be cleared
- Added note about starting a fresh session after clearing

**Function: `confirm_clear_data_callback()`**
Enhanced to clear all three storage systems:

```python
# 1. Clear user data (existing)
success = db.clear_user_data(cid)

# 2. Clear LangGraph chat history (NEW)
memory = get_memory()
conn = memory.conn
cursor = conn.cursor()
cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (str(cid),))
cursor.execute("DELETE FROM checkpoint_writes WHERE thread_id = ?", (str(cid),))
conn.commit()

# 3. Clear Mem0 memories (NEW)
memory_service = get_memory_service()
if memory_service.mem0_enabled:
    memory_service.mem0_client.delete_all(user_id=str(cid))

# 4. Clear active session (NEW)
context.user_data["smart_chat_active"] = False
```

## User Experience

### Before Enhancement
- Only cleared test results and packages
- Smart chat remembered previous conversations
- Mem0 retained all learned facts about the user

### After Enhancement
- ✅ Complete reset of all user data
- ✅ Fresh start for smart chat sessions
- ✅ No memory of previous conversations
- ✅ Clean slate for personality profiling
- 💰 Wallet balance preserved

## Usage Flow

1. User sends `/clear` command
2. Bot shows confirmation dialog with detailed list of what will be cleared
3. User confirms
4. Bot clears:
   - Database records
   - Chat history checkpoints
   - Mem0 memories
   - Active session state
5. Bot confirms success with detailed status
6. User can start fresh with a new session

## Error Handling

The implementation includes graceful error handling:
- Each clearing operation is wrapped in try-except
- Failures are logged but don't block other operations
- User receives detailed status of what was cleared
- Partial success is possible (e.g., data cleared but memories failed)

## Benefits

1. **Privacy** - Users can completely erase their conversation history
2. **Fresh Start** - Useful for testing or starting over
3. **Data Control** - Users have full control over their data
4. **Session Reset** - Clears any stuck states or contexts
5. **Memory Management** - Prevents memory bloat from long conversations

## Testing Recommendations

1. Test with active smart chat session
2. Test with stored Mem0 memories
3. Verify wallet balance is preserved
4. Verify gift status is preserved
5. Test error handling when services are unavailable
6. Verify new session starts fresh after clearing

## Related Files

- `telegram_handlers.py` - Main handler implementation
- `app/chat/smart_chat.py` - Chat agent and memory management
- `app/services/memory_service.py` - Mem0 service
- `db.py` - Database operations
- `database/bot.db` - User data storage
- `database/psychology_bot.db` - Chat history storage

## Future Enhancements

Potential improvements:
- Add option to export data before clearing
- Selective clearing (e.g., only chat history, not test results)
- Scheduled auto-clearing after inactivity
- Backup/restore functionality
