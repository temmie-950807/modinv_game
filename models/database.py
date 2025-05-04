# models/database.py
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

# 資料庫檔案路徑
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'modular_inverse_game.db')

def init_db():
    """初始化資料庫，建立必要的資料表"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 建立使用者資料表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        pw_hash TEXT NOT NULL,
        rating INTEGER DEFAULT 1500,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    conn.commit()
    conn.close()
    print("資料庫初始化完成")

def find_user(username):
    """查詢使用者帳號
    
    Args:
        username: 使用者名稱
        
    Returns:
        dict: 使用者資料字典，不存在則返回None
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # 讓查詢結果可以用列名訪問
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return dict(user)  # 轉換為字典，與原來的 JSON 格式相容
    return None

def register_user(username, password):
    """註冊新帳號
    
    Args:
        username: 使用者名稱
        password: 使用者密碼
        
    Returns:
        bool: 註冊是否成功
    """
    if find_user(username):
        return False
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (username, pw_hash, rating) VALUES (?, ?, ?)",
            (username, generate_password_hash(password), 1500)
        )
        conn.commit()
        result = True
    except sqlite3.IntegrityError:
        # 可能是使用者名稱已存在的衝突
        conn.rollback()
        result = False
    finally:
        conn.close()
    
    return result

def verify_user_credentials(username, password):
    """驗證帳號密碼
    
    Args:
        username: 使用者名稱
        password: 使用者密碼
        
    Returns:
        bool: 驗證是否成功
    """
    user = find_user(username)
    return user and check_password_hash(user['pw_hash'], password)

def update_user_rating(username, new_rating):
    """更新使用者 rating
    
    Args:
        username: 使用者名稱
        new_rating: 新的 rating 值
        
    Returns:
        bool: 更新是否成功
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE users SET rating = ? WHERE username = ?",
            (new_rating, username)
        )
        conn.commit()
        result = True
    except:
        conn.rollback()
        result = False
    finally:
        conn.close()
    
    return result

def get_leaderboard_data():
    """獲取排行榜數據
    
    Returns:
        list: 包含所有玩家資料的列表，按 rating 降序排列
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT username, rating 
        FROM users 
        ORDER BY rating DESC
    """)
    
    players = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return players

def migrate_json_to_sqlite(json_file_path):
    """將 JSON 格式使用者資料遷移到 SQLite
    
    Args:
        json_file_path: JSON 檔案路徑
        
    Returns:
        tuple: (成功遷移數量, 跳過數量)
    """
    import json
    
    # 確保資料庫已初始化
    init_db()
    
    # 載入 JSON 帳號資料
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0, 0
    
    # 連接資料庫
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    migrated = 0
    skipped = 0
    
    # 開始遷移
    for account in accounts:
        username = account.get('username')
        pw_hash = account.get('pw_hash')
        rating = account.get('rating', 1500)
        
        if not username or not pw_hash:
            skipped += 1
            continue
        
        # 檢查帳號是否已存在
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            cursor.execute("UPDATE users SET rating = ? WHERE username = ?", (rating, username))
            migrated += 1
        else:
            cursor.execute(
                "INSERT INTO users (username, pw_hash, rating) VALUES (?, ?, ?)",
                (username, pw_hash, rating)
            )
            migrated += 1
    
    conn.commit()
    conn.close()
    
    return migrated, skipped