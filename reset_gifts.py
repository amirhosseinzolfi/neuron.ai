import sqlite3
import os

DB_PATH = 'database/bot.db'

def reset_all_user_gifts():
    """
    Connects to the database and resets the gift status for all users.
    This allows all users to claim the gift again.
    """
    if not os.path.exists(DB_PATH):
        print(f"Error: Database file '{DB_PATH}' not found.")
        print("Please run this script from the same directory as your bot.db file.")
        return

    conn = None
    try:
        # Connect to the database, using settings similar to the main app
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        cur = conn.cursor()

        print("Attempting to reset gift status for all users...")

        # Execute the update query
        cur.execute("UPDATE users SET gift_received = 0, gift_received_ts = NULL")

        # Get the number of rows affected
        updated_rows = cur.rowcount

        conn.commit()
        print(f"✅ Success! Gift status has been reset for {updated_rows} users.")
        print("All users can now receive the gift again.")

    except sqlite3.Error as e:
        print(f"❌ A database error occurred: {e}")
        if conn:
            conn.rollback()
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("--- Gift Status Reset Script ---")
    reset_all_user_gifts()
    print("--- Script finished ---")
