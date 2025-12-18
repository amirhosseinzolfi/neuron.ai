# /clear Command - Quick Reference

## What It Does
Completely resets the user's bot experience by clearing all data, chat history, and memories while preserving wallet balance and gift status.

## Quick Facts

| Aspect | Details |
|--------|---------|
| **Command** | `/clear` |
| **Confirmation** | Required (Yes/No buttons) |
| **Reversible** | ❌ No - permanent deletion |
| **Preserves** | Wallet balance, Gift status |
| **Clears** | Tests, Packages, Profile, Chat History, Memories |

## What Gets Cleared ✅

### 1. User Data (bot.db)
- ✅ All test results
- ✅ All purchased packages  
- ✅ Psychology profile
- ✅ User progress & information
- ✅ Profile images

### 2. Chat History (psychology_bot.db)
- ✅ All conversation messages
- ✅ LangGraph checkpoints
- ✅ Conversation state

### 3. Long-term Memory (Mem0)
- ✅ All stored memories
- ✅ Extracted facts
- ✅ Conversation summaries

### 4. Session State
- ✅ Active smart chat session
- ✅ Temporary context data

## What Gets Preserved 💰

- 💰 **Wallet Balance** - Your money stays safe
- 🎁 **Gift Status** - Whether you received the welcome gift

## User Messages

### Warning Message (Persian)
```
⚠️ هشدار!

آیا مطمئن هستید که میخواهید تمام اطلاعات خود را پاک کنید؟

موارد حذف شده:
• نتایج تمام تستها
• پکیجهای خریداری شده
• پروفایل روانشناسی
• تاریخچه گفتگو و پیامهای هوشمند
• حافظه بلندمدت (Mem0)

موارد حفظ شده:
• موجودی کیف پول 💰
• وضعیت دریافت هدیه 🎁

🔄 پس از پاک کردن:
جلسه گفتگوی هوشمند به طور کامل ریست میشود و یک جلسه جدید شروع خواهد شد.

⚠️ این عملیات قابل بازگشت نیست!
```

### Success Message (Persian)
```
✅ اطلاعات شما با موفقیت پاک شد!

موارد پاک شده:
• نتایج تستها ✅
• پکیجهای خریداری شده ✅
• پروفایل روانشناسی ✅
• تاریخچه گفتگوی هوشمند ✅
• حافظه بلندمدت (Mem0) ✅

موارد حفظ شده:
• موجودی کیف پول 💰
• وضعیت دریافت هدیه 🎁

ربات به حالت اولیه بازگشت. برای شروع مجدد از منوی اصلی استفاده کنید.
```

## Code Locations

| Component | File | Function |
|-----------|------|----------|
| Command Handler | `telegram_handlers.py` | `clear_data()` |
| Confirmation Handler | `telegram_handlers.py` | `confirm_clear_data_callback()` |
| Cancel Handler | `telegram_handlers.py` | `cancel_clear_data_callback()` |
| DB Clear | `db.py` | `clear_user_data()` |
| Memory Service | `app/services/memory_service.py` | `get_memory_service()` |
| Chat Memory | `app/chat/smart_chat.py` | `get_memory()` |

## Technical Details

### Storage Systems Cleared

```
1. SQLite (bot.db)
   └─ Tables: test_results, user_packages, package_tests, users (partial)

2. SQLite (psychology_bot.db)  
   └─ Tables: checkpoints, checkpoint_writes

3. Mem0 + Qdrant
   └─ All user memories via mem0_client.delete_all()

4. In-memory
   └─ context.user_data["smart_chat_active"]
```

### SQL Operations

```sql
-- User data
DELETE FROM test_results WHERE chat_id = ?;
DELETE FROM package_tests WHERE user_package_id IN (...);
DELETE FROM user_packages WHERE chat_id = ?;
UPDATE users SET progress=0, information=NULL, ... WHERE chat_id = ?;

-- Chat history
DELETE FROM checkpoints WHERE thread_id = ?;
DELETE FROM checkpoint_writes WHERE thread_id = ?;
```

### Python Operations

```python
# Mem0 clear
memory_service.mem0_client.delete_all(user_id=str(cid))

# Session clear
context.user_data["smart_chat_active"] = False
```

## Error Handling

Each operation is independent:
- ✅ Failures are logged
- ✅ Other operations continue
- ✅ User sees detailed status
- ✅ Partial success is possible

## Use Cases

### When to Use /clear

1. **Privacy** - User wants to erase all conversation history
2. **Fresh Start** - User wants to start over with clean slate
3. **Testing** - Developer testing bot behavior
4. **Stuck State** - Bot is in a weird state, need reset
5. **New Profile** - User wants to rebuild their profile from scratch

### When NOT to Use /clear

1. **Just to clear chat** - Use /end_chat instead
2. **To reset wallet** - Wallet is preserved
3. **Accidental** - Operation is irreversible

## Testing Checklist

- [ ] Test with active smart chat session
- [ ] Test with stored Mem0 memories  
- [ ] Verify wallet balance preserved
- [ ] Verify gift status preserved
- [ ] Test error handling (DB unavailable)
- [ ] Test error handling (Mem0 unavailable)
- [ ] Verify new chat starts fresh
- [ ] Test cancel button works
- [ ] Verify confirmation required
- [ ] Check all messages display correctly

## Related Commands

| Command | Purpose |
|---------|---------|
| `/clear` | Clear all data (this command) |
| `/end_chat` | End smart chat session only |
| `/start` | Show main menu |

## Logging

All operations are logged:
```python
console.log(f"[red]Clearing data for user {cid}[/red]")
console.log(f"[green]✅ Smart chat history cleared[/green]")
console.log(f"[green]✅ Mem0 memories cleared[/green]")
console.log(f"[yellow]⚠️ Failed to clear: {error}[/yellow]")
```

## Security Considerations

- ✅ Requires explicit user confirmation
- ✅ Shows clear warning about irreversibility
- ✅ Preserves financial data (wallet)
- ✅ Logs all operations for audit
- ✅ No admin override needed (user controls own data)

## Performance

- **Speed**: Fast (< 1 second typically)
- **Blocking**: Non-blocking (async operations)
- **Database**: Uses transactions for consistency
- **Memory**: Minimal memory usage

## Future Enhancements

Potential improvements:
- [ ] Export data before clearing
- [ ] Selective clearing options
- [ ] Scheduled auto-clear
- [ ] Backup/restore functionality
- [ ] Clear confirmation via PIN
- [ ] Clear history (keep profile)
- [ ] Clear profile (keep history)

## Support

For issues:
1. Check logs in console
2. Verify database connections
3. Check Mem0 service status
4. Review error messages
5. Open GitHub issue if needed

---

**Last Updated**: 2024
**Version**: 1.0
**Status**: ✅ Production Ready
