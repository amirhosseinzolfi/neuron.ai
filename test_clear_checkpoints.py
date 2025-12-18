#!/usr/bin/env python3
"""
Test script to verify checkpoint clearing works correctly.
"""
import sqlite3

def check_checkpoints(user_id):
    """Check how many checkpoints exist for a user."""
    conn = sqlite3.connect('database/psychology_bot.db')
    cursor = conn.cursor()
    
    # Count checkpoints
    cursor.execute("SELECT COUNT(*) FROM checkpoints WHERE thread_id = ?", (str(user_id),))
    checkpoint_count = cursor.fetchone()[0]
    
    # Count writes
    cursor.execute("SELECT COUNT(*) FROM writes WHERE thread_id = ?", (str(user_id),))
    writes_count = cursor.fetchone()[0]
    
    # Get sample checkpoint IDs
    cursor.execute("SELECT checkpoint_id FROM checkpoints WHERE thread_id = ? LIMIT 5", (str(user_id),))
    sample_ids = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    print(f"User {user_id}:")
    print(f"  Checkpoints: {checkpoint_count}")
    print(f"  Writes: {writes_count}")
    if sample_ids:
        print(f"  Sample IDs: {sample_ids[:3]}")
    print()
    
    return checkpoint_count, writes_count

def clear_checkpoints(user_id):
    """Clear all checkpoints for a user."""
    conn = sqlite3.connect('database/psychology_bot.db')
    cursor = conn.cursor()
    
    # Delete writes
    cursor.execute("DELETE FROM writes WHERE thread_id = ?", (str(user_id),))
    writes_deleted = cursor.rowcount
    
    # Delete checkpoints
    cursor.execute("DELETE FROM checkpoints WHERE thread_id = ?", (str(user_id),))
    checkpoints_deleted = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"Cleared for user {user_id}:")
    print(f"  Checkpoints deleted: {checkpoints_deleted}")
    print(f"  Writes deleted: {writes_deleted}")
    print()
    
    return checkpoints_deleted, writes_deleted

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python test_clear_checkpoints.py <user_id> [clear]")
        print("\nExamples:")
        print("  python test_clear_checkpoints.py 5816681487        # Check only")
        print("  python test_clear_checkpoints.py 5816681487 clear  # Clear and verify")
        sys.exit(1)
    
    user_id = sys.argv[1]
    should_clear = len(sys.argv) > 2 and sys.argv[2] == "clear"
    
    print("=" * 60)
    print("BEFORE:")
    print("=" * 60)
    before_checkpoints, before_writes = check_checkpoints(user_id)
    
    if should_clear:
        print("=" * 60)
        print("CLEARING:")
        print("=" * 60)
        clear_checkpoints(user_id)
        
        print("=" * 60)
        print("AFTER:")
        print("=" * 60)
        after_checkpoints, after_writes = check_checkpoints(user_id)
        
        if after_checkpoints == 0 and after_writes == 0:
            print("✅ SUCCESS: All checkpoints and writes cleared!")
        else:
            print("❌ FAILED: Some data remains")
    else:
        print("Run with 'clear' argument to actually clear the data.")
