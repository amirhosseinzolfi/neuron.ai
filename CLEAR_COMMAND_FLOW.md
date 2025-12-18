# /clear Command Flow Diagram

## User Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    User sends /clear                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Bot shows confirmation dialog                   │
│                                                              │
│  ⚠️ Warning!                                                 │
│                                                              │
│  Items to be deleted:                                        │
│  • Test results                                              │
│  • Purchased packages                                        │
│  • Psychology profile                                        │
│  • Chat history and smart messages                           │
│  • Long-term memory (Mem0)                                   │
│                                                              │
│  Items preserved:                                            │
│  • Wallet balance 💰                                         │
│  • Gift status 🎁                                            │
│                                                              │
│  [✅ Yes, clear]  [❌ No, cancel]                            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
                    User confirms?
                         │
            ┌────────────┴────────────┐
            │                         │
           Yes                       No
            │                         │
            ▼                         ▼
    ┌───────────────┐        ┌──────────────┐
    │ Execute clear │        │ Show cancel  │
    └───────┬───────┘        │   message    │
            │                └──────────────┘
            ▼
┌─────────────────────────────────────────────────────────────┐
│              Clear Operation (Sequential)                    │
└─────────────────────────────────────────────────────────────┘
            │
            ├─► Step 1: Clear User Data (bot.db)
            │   ├─ DELETE test_results
            │   ├─ DELETE package_tests
            │   ├─ DELETE user_packages
            │   └─ UPDATE users (reset profile fields)
            │
            ├─► Step 2: Clear Chat History (psychology_bot.db)
            │   ├─ DELETE FROM checkpoints WHERE thread_id = user_id
            │   └─ DELETE FROM checkpoint_writes WHERE thread_id = user_id
            │
            ├─► Step 3: Clear Mem0 Memories
            │   └─ mem0_client.delete_all(user_id)
            │
            └─► Step 4: Clear Session State
                └─ context.user_data["smart_chat_active"] = False
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                   Show Success Message                       │
│                                                              │
│  ✅ Your data has been successfully cleared!                 │
│                                                              │
│  Items cleared:                                              │
│  • Test results ✅                                           │
│  • Purchased packages ✅                                     │
│  • Psychology profile ✅                                     │
│  • Smart chat history ✅                                     │
│  • Long-term memory (Mem0) ✅                                │
│                                                              │
│  Items preserved:                                            │
│  • Wallet balance 💰                                         │
│  • Gift status 🎁                                            │
│                                                              │
│  Bot has been reset. Use main menu to start again.          │
└─────────────────────────────────────────────────────────────┘
```

## Data Storage Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Data Layers                        │
└─────────────────────────────────────────────────────────────┘

Layer 1: User Profile & Tests (database/bot.db)
┌──────────────────────────────────────────────┐
│  users table:                                │
│  - chat_id, balance, username                │
│  - progress, information, stars              │
│  - psychology_profile, user_profile          │
│  - gift_received ← PRESERVED                 │
│  - balance ← PRESERVED                       │
│                                              │
│  test_results table: ← CLEARED               │
│  - test results, PDFs, images                │
│                                              │
│  user_packages table: ← CLEARED              │
│  - purchased packages                        │
│                                              │
│  package_tests table: ← CLEARED              │
│  - package test completion status            │
└──────────────────────────────────────────────┘

Layer 2: Chat History (database/psychology_bot.db)
┌──────────────────────────────────────────────┐
│  checkpoints table: ← CLEARED                │
│  - LangGraph conversation state              │
│  - thread_id = user's chat_id                │
│                                              │
│  checkpoint_writes table: ← CLEARED          │
│  - Pending checkpoint writes                 │
└──────────────────────────────────────────────┘

Layer 3: Long-term Memory (Mem0 + Qdrant)
┌──────────────────────────────────────────────┐
│  Mem0 AI Memory: ← CLEARED                   │
│  - Extracted facts about user                │
│  - Conversation summaries                    │
│  - Semantic memories                         │
│                                              │
│  Qdrant Vector Store: ← CLEARED              │
│  - Embeddings of memories                    │
│  - Collection: mem0_nomic_768                │
└──────────────────────────────────────────────┘

Layer 4: Session State (In-memory)
┌──────────────────────────────────────────────┐
│  context.user_data: ← CLEARED                │
│  - smart_chat_active flag                    │
│  - temporary session data                    │
└──────────────────────────────────────────────┘
```

## Code Execution Flow

```python
def confirm_clear_data_callback(update, context):
    cid = query.message.chat_id
    
    # ═══════════════════════════════════════════════════════
    # STEP 1: Clear User Data (Database)
    # ═══════════════════════════════════════════════════════
    success = db.clear_user_data(cid)
    # Deletes: test_results, packages, profile data
    # Preserves: balance, gift_received
    
    # ═══════════════════════════════════════════════════════
    # STEP 2: Clear Chat History (LangGraph)
    # ═══════════════════════════════════════════════════════
    try:
        memory = get_memory()  # SqliteSaver instance
        conn = memory.conn
        cursor = conn.cursor()
        
        # Clear checkpoints for this user's thread
        cursor.execute(
            "DELETE FROM checkpoints WHERE thread_id = ?", 
            (str(cid),)
        )
        cursor.execute(
            "DELETE FROM checkpoint_writes WHERE thread_id = ?", 
            (str(cid),)
        )
        conn.commit()
        chat_history_cleared = True
    except Exception as e:
        logger.error(f"Chat history clear error: {e}")
        chat_history_cleared = False
    
    # ═══════════════════════════════════════════════════════
    # STEP 3: Clear Mem0 Memories
    # ═══════════════════════════════════════════════════════
    try:
        memory_service = get_memory_service()
        if memory_service.mem0_enabled:
            # Delete all memories for this user
            memory_service.mem0_client.delete_all(
                user_id=str(cid)
            )
            memories_cleared = True
    except Exception as e:
        logger.error(f"Mem0 clear error: {e}")
        memories_cleared = False
    
    # ═══════════════════════════════════════════════════════
    # STEP 4: Clear Session State
    # ═══════════════════════════════════════════════════════
    if context.user_data.get("smart_chat_active"):
        context.user_data["smart_chat_active"] = False
    
    # ═══════════════════════════════════════════════════════
    # STEP 5: Show Success Message
    # ═══════════════════════════════════════════════════════
    query.edit_message_text(success_message)
```

## Error Handling Strategy

```
Each clearing operation is independent:

┌─────────────────┐
│ Clear User Data │ ──► Success/Fail (logged)
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Clear Chat Hist │ ──► Success/Fail (logged)
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Clear Mem0      │ ──► Success/Fail (logged)
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Clear Session   │ ──► Success/Fail (logged)
└─────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Show detailed status to user        │
│ (which operations succeeded/failed) │
└─────────────────────────────────────┘

Benefits:
✅ Partial success is possible
✅ User knows exactly what was cleared
✅ Failures don't block other operations
✅ All errors are logged for debugging
```

## Smart Chat Session Reset

```
Before /clear:
┌────────────────────────────────────────┐
│ User: "Hello, I'm feeling anxious"    │
│ Bot: "I understand. Tell me more..."  │
│ User: "I have a big presentation"     │
│ Bot: "Let's work through this..."     │
│                                        │
│ [Stored in checkpoints table]         │
│ [Stored in Mem0 memories]             │
└────────────────────────────────────────┘

After /clear:
┌────────────────────────────────────────┐
│ [All history cleared]                  │
│ [All memories cleared]                 │
│ [Session state reset]                  │
│                                        │
│ Next conversation starts fresh:        │
│ User: "Hello"                          │
│ Bot: "سلام! به جلسه هوشمند خوش آمدید!" │
│                                        │
│ [No memory of previous conversation]  │
└────────────────────────────────────────┘
```

## Database Schema Impact

### Before Clear
```sql
-- checkpoints table
thread_id | checkpoint_id | parent_id | checkpoint_data
----------|---------------|-----------|----------------
"123456"  | "uuid-1"      | NULL      | {...messages...}
"123456"  | "uuid-2"      | "uuid-1"  | {...messages...}
"123456"  | "uuid-3"      | "uuid-2"  | {...messages...}

-- checkpoint_writes table
thread_id | checkpoint_id | task_id | channel | data
----------|---------------|---------|---------|------
"123456"  | "uuid-3"      | "t1"    | "ch1"   | {...}
```

### After Clear
```sql
-- checkpoints table
thread_id | checkpoint_id | parent_id | checkpoint_data
----------|---------------|-----------|----------------
[empty for user 123456]

-- checkpoint_writes table
thread_id | checkpoint_id | task_id | channel | data
----------|---------------|---------|---------|------
[empty for user 123456]
```

## Summary

The `/clear` command now provides a **complete reset** of the user's bot experience:

✅ **Comprehensive** - Clears all three storage layers
✅ **Safe** - Preserves wallet balance and gift status  
✅ **Transparent** - Shows detailed status of what was cleared
✅ **Robust** - Handles errors gracefully
✅ **Fresh Start** - User can begin a new session with no history
