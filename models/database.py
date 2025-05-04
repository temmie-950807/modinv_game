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
    """查詢使用者帳號"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # 讓查詢結果可以用列名訪問
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return dict(user)  # 轉換為字典，與原來的 JSON 格式相容
    return None

def add_user(username, password):
    """註冊新帳號"""
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

def verify_user(username, password):
    """驗證帳號密碼"""
    user = find_user(username)
    return user and check_password_hash(user['pw_hash'], password)

def update_user_rating(username, new_rating):
    """更新使用者 rating"""
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

def update_ratings(rating_changes):
    """
    更新多個使用者 rating
    rating_changes: dict of username → rating change
    """
    if not rating_changes:
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        for username, change in rating_changes.items():
            user = find_user(username)
            if user:
                new_rating = user['rating'] + change
                cursor.execute(
                    "UPDATE users SET rating = ? WHERE username = ?",
                    (new_rating, username)
                )
        
        conn.commit()
    except:
        conn.rollback()
    finally:
        conn.close()

def get_all_users():
    """獲取所有使用者資料"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT username, rating FROM users ORDER BY rating DESC")
    
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return users