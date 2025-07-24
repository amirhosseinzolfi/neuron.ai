import sqlite3
import time

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
    if "username" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "first_name" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN first_name TEXT")
    if "last_name" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN last_name TEXT")
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
    cur.execute('INSERT OR IGNORE INTO users (chat_id) VALUES (?)', (chat_id,))
    cur.execute(
        'UPDATE users SET username = ?, first_name = ?, last_name = ? WHERE chat_id = ?',
        (username, first_name, last_name, chat_id)
    )
    conn.commit()
    conn.close()

def save_test_result(chat_id: int, test_name: str, result_text: str, pdf_path: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO test_results (chat_id, test_name, result_text, pdf_path, timestamp) VALUES (?, ?, ?, ?, ?)",
        (chat_id, test_name, result_text, pdf_path, time.time())
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
    """Return dict with test_name, result_text and pdf_path for a given record id."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute('SELECT test_name, result_text, pdf_path FROM test_results WHERE id = ?', (record_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        'test_name': row['test_name'],
        'result_text': row['result_text'],
        'pdf_path': row['pdf_path']
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

def get_all_users():
    """Return list of all users ever seen, including metadata and balance."""
    conn = get_conn()
    cur = conn.cursor()
    # pull existing users
    cur.execute('SELECT chat_id, balance, username, first_name, last_name FROM users')
    rows = cur.fetchall()
    user_map = {}
    for row in rows:
        user_map[row['chat_id']] = {
            'chat_id': row['chat_id'],
            'balance': row['balance'],
            'username': row['username'],
            'first_name': row['first_name'],
            'last_name': row['last_name']
        }
    # include chat_ids from test_results
    cur.execute('SELECT DISTINCT chat_id FROM test_results')
    for trow in cur.fetchall():
        cid = trow['chat_id']
        if cid not in user_map:
            user_map[cid] = {'chat_id': cid, 'balance': 0, 'username': None, 'first_name': None, 'last_name': None}
    conn.close()
    return list(user_map.values())

