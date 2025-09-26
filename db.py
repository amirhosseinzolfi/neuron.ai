import sqlite3
import time
import logging

DB_PATH = 'bot.db'

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # enable WAL for better concurrency and set busy timeout
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER UNIQUE,
        balance INTEGER DEFAULT 0
    )
    """)
    # ensure columns for Telegram metadata
    cur.execute("PRAGMA table_info(users)")
    cols = [col[1] for col in cur.fetchall()]
    
    # Add existing column checks
    if "username" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "first_name" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
    if "last_name" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
        
    # Add new column checks
    if "progress" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN progress INTEGER DEFAULT 0")
    if "information" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN information TEXT")
    if "image" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN image TEXT")  # Store image file path
    if "stars" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN stars INTEGER DEFAULT 0")
    if "psychology_profile" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN psychology_profile TEXT")  # Store JSON file path

    # create payment_screenshots table
    cur.execute("CREATE TABLE IF NOT EXISTS payment_screenshots ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "chat_id INTEGER,"
                "file_path TEXT,"
                "timestamp REAL"
                ")")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        test_name TEXT,
        result_text TEXT,
        timestamp REAL
    )
    """)
    cur.execute("PRAGMA table_info(test_results)")
    cols = [col[1] for col in cur.fetchall()]
    if "pdf_path" not in cols:
        cur.execute("ALTER TABLE test_results ADD COLUMN pdf_path TEXT")
    # NEW: ensure final_analyze column exists for storing concise analysis/caption
    if "final_analyze" not in cols:
        cur.execute("ALTER TABLE test_results ADD COLUMN final_analyze TEXT")
    
    # Create packages tables
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        package_id TEXT,
        purchase_timestamp REAL,
        completed INTEGER DEFAULT 0
    )
    """)
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS package_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_package_id INTEGER,
        test_id INTEGER,
        completed INTEGER DEFAULT 0,
        FOREIGN KEY (user_package_id) REFERENCES user_packages(id)
    )
    """)
    
    conn.commit()
    conn.close()

def get_balance(chat_id: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('INSERT OR IGNORE INTO users (chat_id) VALUES (?)', (chat_id,))
    conn.commit()
    cur.execute('SELECT balance FROM users WHERE chat_id = ?', (chat_id,))
    balance = cur.fetchone()['balance']
    conn.close()
    return balance

def update_balance(chat_id: int, amount: int):
    conn = get_conn()
    cur = conn.cursor()
    # ensure user row exists
    cur.execute('INSERT OR IGNORE INTO users (chat_id) VALUES (?)', (chat_id,))
    # fetch old balance
    cur.execute('SELECT balance FROM users WHERE chat_id = ?', (chat_id,))
    row = cur.fetchone()
    old = row['balance'] if row else 0
    # compute and clamp to SQLite INTEGER range
    new = old + amount
    min_i64, max_i64 = -2**63, 2**63 - 1
    if new < min_i64: new = min_i64
    if new > max_i64: new = max_i64
    # update with clamped value
    cur.execute('UPDATE users SET balance = ? WHERE chat_id = ?', (new, chat_id))
    conn.commit()
    conn.close()

def save_user(chat_id: int, username: str, first_name: str, last_name: str):
    """Insert or update a user record with Telegram metadata."""
    conn = get_conn()
    cur = conn.cursor()
    
    # Check if user exists
    cur.execute('SELECT chat_id FROM users WHERE chat_id = ?', (chat_id,))
    user_exists = cur.fetchone() is not None
    
    # Insert if new user
    if not user_exists:
        cur.execute('INSERT INTO users (chat_id) VALUES (?)', (chat_id,))
        # Initialize psychological profile for new users
        initialize_psychology_profile(chat_id)
    
    # Update user metadata
    cur.execute(
        'UPDATE users SET username = ?, first_name = ?, last_name = ? WHERE chat_id = ?',
        (username, first_name, last_name, chat_id)
    )
    conn.commit()
    conn.close()

def save_test_result(chat_id: int, test_name: str, result_text: str, pdf_path: str, final_analyze: str = None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        # include final_analyze column in insert; keep backward-compatible by using named columns
        "INSERT INTO test_results (chat_id, test_name, result_text, pdf_path, final_analyze, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (chat_id, test_name, result_text, pdf_path, final_analyze, time.time())
    )
    conn.commit()
    conn.close()

def save_payment_screenshot(chat_id: int, file_path: str):
    """Insert a payment screenshot record for a user."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO payment_screenshots (chat_id, file_path, timestamp) VALUES (?, ?, ?)',
        (chat_id, file_path, time.time())
    )
    conn.commit()
    conn.close()

def get_user_tests(chat_id: int):
    """Return list of saved test result records for a user."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, test_name, timestamp FROM test_results WHERE chat_id = ? ORDER BY timestamp DESC', (chat_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_test_result(record_id: int):
    """Return dict with test_name, result_text, pdf_path and final_analyze for a given record id."""
    conn = get_conn()
    cur = conn.cursor()
    # include final_analyze in select
    cur.execute('SELECT test_name, result_text, pdf_path, final_analyze FROM test_results WHERE id = ?', (record_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'test_name': row['test_name'],
        'result_text': row['result_text'],
        'pdf_path': row['pdf_path'],
        'final_analyze': row['final_analyze']
    }

# Package-related functions
def purchase_package(chat_id: int, package_id: str):
    """Record a package purchase for a user"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            'INSERT INTO user_packages (chat_id, package_id, purchase_timestamp) VALUES (?, ?, ?)',
            (chat_id, package_id, time.time())
        )
        package_id = cur.lastrowid
        conn.commit()
        conn.close()
        return package_id
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e

def add_package_tests(user_package_id: int, test_ids: list):
    """Add tests to a user's purchased package"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        for test_id in test_ids:
            cur.execute(
                'INSERT INTO package_tests (user_package_id, test_id) VALUES (?, ?)',
                (user_package_id, test_id)
            )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e

def get_user_packages(chat_id: int):
    """Get all packages purchased by a user"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, package_id, purchase_timestamp, completed FROM user_packages WHERE chat_id = ? ORDER BY purchase_timestamp DESC', (chat_id,))
    packages = cur.fetchall()
    conn.close()
    return packages

def get_package_tests(user_package_id: int):
    """Get all tests in a user's package"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, test_id, completed FROM package_tests WHERE user_package_id = ?', (user_package_id,))
    tests = cur.fetchall()
    conn.close()
    return tests

def mark_package_test_completed(package_test_id: int):
    """Mark a test in a package as completed"""
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute('UPDATE package_tests SET completed = 1 WHERE id = ?', (package_test_id,))
        conn.commit()
        
        # Check if all tests in the package are completed
        cur.execute('SELECT user_package_id FROM package_tests WHERE id = ?', (package_test_id,))
        user_package_id = cur.fetchone()['user_package_id']
        
        cur.execute('SELECT COUNT(*) as total FROM package_tests WHERE user_package_id = ?', (user_package_id,))
        total_tests = cur.fetchone()['total']
        
        cur.execute('SELECT COUNT(*) as completed FROM package_tests WHERE user_package_id = ? AND completed = 1', (user_package_id,))
        completed_tests = cur.fetchone()['completed']
        
        # If all tests are completed, mark the package as completed
        if total_tests == completed_tests:
            cur.execute('UPDATE user_packages SET completed = 1 WHERE id = ?', (user_package_id,))
            conn.commit()
        
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        raise e

def get_package_test_by_test_id(user_package_id: int, test_id: int):
    """Get a specific test in a package by its test_id"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, test_id, completed FROM package_tests WHERE user_package_id = ? AND test_id = ?', 
                (user_package_id, test_id))
    test = cur.fetchone()
    conn.close()
    return test

def get_user_package(user_package_id: int):
    """Get a specific user package by its ID"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT id, chat_id, package_id, purchase_timestamp, completed FROM user_packages WHERE id = ?', 
                (user_package_id,))
    package = cur.fetchone()
    conn.close()
    return package

def get_user(chat_id: int):
    """Return user data for a given chat_id."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT chat_id, balance, username, first_name, last_name,
               progress, information, image, stars, psychology_profile
        FROM users WHERE chat_id = ?''', (chat_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    # Defensive read: ensure we return psychology_profile even if DB older schema lacks it
    keys = row.keys()
    return {
        'chat_id': row['chat_id'],
        'balance': row['balance'],
        'username': row['username'],
        'first_name': row['first_name'],
        'last_name': row['last_name'],
        'progress': row['progress'],
        'information': row['information'],
        'image': row['image'],
        'stars': row['stars'],
        'psychology_profile': row['psychology_profile'] if 'psychology_profile' in keys else None
    }

def update_user_profile(chat_id: int, **kwargs):
    """Update user profile fields."""
    conn = get_conn()
    cur = conn.cursor()
    
    valid_fields = {'progress', 'information', 'image', 'stars'}
    updates = {k: v for k, v in kwargs.items() if k in valid_fields}
    
    if updates:
        set_clause = ', '.join(f'{k} = ?' for k in updates.keys())
        values = list(updates.values()) + [chat_id]
        
        cur.execute(f'''
            UPDATE users 
            SET {set_clause}
            WHERE chat_id = ?
        ''', values)
        
        conn.commit()
    conn.close()
    return bool(updates)

def get_test_result_by_test_id(chat_id: int, test_id: int):
    """Return the latest test result for a given user and test id."""
    conn = get_conn()
    cur = conn.cursor()
    import psychology_test as pt
    test_name = pt.all_tests["tests"][test_id - 1]["test_name"]
    # include final_analyze in select
    cur.execute('SELECT id, test_name, result_text, pdf_path, final_analyze FROM test_results WHERE chat_id = ? AND test_name = ? ORDER BY timestamp DESC LIMIT 1', (chat_id, test_name))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'id': row['id'],
        'test_name': row['test_name'],
        'result_text': row['result_text'],
        'pdf_path': row['pdf_path'],
        'final_analyze': row['final_analyze']
    }

def get_default_psychology_profile() -> dict:
    """Returns the default psychological profile template with null values."""
    from datetime import datetime
    
    return {
        "name": None,
        "age": None,
        "gender": None,
        "job": None,
        "education_level": None,
        "location": {
            "city": None,
            "region": None,
            "country": None
        },
        "contact": {
            "email": None,
            "phone": None
        },
        "interests": [],
        "values": [],
        "goals": [],
        "personality_traits": {
            "big_five": {
                "openness": None,
                "conscientiousness": None,
                "extraversion": None,
                "agreeableness": None,
                "neuroticism": None
            }
        },
        "schema_patterns": [],
        "communication_style": {
            "style": None,
            "tone_preference": None
        },
        "emotional_style": {
            "baseline_mood": None,
            "stress_tolerance": None,
            "coping_strategies": []
        },
        "strengths": [],
        "challenges": [],
        "notes": None,
        "last_updated": datetime.utcnow().isoformat()
    }

def initialize_psychology_profile(chat_id: int) -> bool:
    """Initialize a new user's psychological profile with default template.
    
    Args:
        chat_id: The user's chat ID
    
    Returns:
        bool: True if profile was initialized successfully, False otherwise
    """
    try:
        default_profile = get_default_psychology_profile()
        save_psychology_profile(chat_id, default_profile)
        return True
    except Exception as e:
        logging.error(f"Failed to initialize psychology profile for user {chat_id}: {e}")
        return False

def save_psychology_profile(chat_id: int, profile_data: dict):
    """Save psychology profile for a user and store it as a JSON file.
    
    Args:
        chat_id: The user's chat ID
        profile_data: Dictionary containing the psychology profile data
    """
    import os
    import json
    
    # Create profile directory if it doesn't exist
    profile_dir = 'database/psychology_profiles'
    os.makedirs(profile_dir, exist_ok=True)
    
    # Generate filename using chat_id
    filename = f"{chat_id}_profile.json"
    file_path = os.path.join(profile_dir, filename)
    
    # Save profile data as JSON file
    with open(file_path, 'w') as f:
        json.dump(profile_data, f, indent=2)
    
    # Update database with file path
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('UPDATE users SET psychology_profile = ? WHERE chat_id = ?', 
                (file_path, chat_id))
    conn.commit()
    conn.close()

def get_psychology_profile(chat_id: int) -> dict:
    """Retrieve psychology profile for a user.
    
    Args:
        chat_id: The user's chat ID
        
    Returns:
        Dictionary containing the psychology profile data or None if not found
    """
    import json
    
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT psychology_profile FROM users WHERE chat_id = ?', (chat_id,))
    row = cur.fetchone()
    conn.close()
    
    if not row or not row['psychology_profile']:
        return None
        
    try:
        with open(row['psychology_profile'], 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def get_all_users():
    """Return list of all users ever seen, including metadata and balance."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('''
        SELECT chat_id, balance, username, first_name, last_name,
               progress, information, image, stars 
        FROM users''')
    rows = cur.fetchall()
    user_map = {}
    for row in rows:
        user_map[row['chat_id']] = {
            'chat_id': row['chat_id'],
            'balance': row['balance'],
            'username': row['username'],
            'first_name': row['first_name'],
            'last_name': row['last_name'],
            'progress': row['progress'],
            'information': row['information'],
            'image': row['image'],
            'stars': row['stars']
        }
    # include chat_ids from test_results
    cur.execute('SELECT DISTINCT chat_id FROM test_results')
    for trow in cur.fetchall():
        cid = trow['chat_id']
        if cid not in user_map:
            user_map[cid] = {'chat_id': cid, 'balance': 0, 'username': None, 'first_name': None, 'last_name': None}
    conn.close()
    return list(user_map.values())

