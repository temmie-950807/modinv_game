import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

# 資料庫檔案路徑
DB_FILE = os.path.join(os.path.dirname(__file__), '../modular_inverse_game.db')

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

def find_account(username):
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

def register_account(username, password):
    """註冊新帳號"""
    if find_account(username):
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

def verify_account(username, password):
    """驗證帳號密碼"""
    user = find_account(username)
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

def update_ratings(score_dict):
    """
    更新多個使用者 rating
    score_dict: dict of username → 得分（比賽中的實際分數）
    
    平手情況下不更新 rating
    """
    players = list(score_dict.keys())
    n = len(players)
    if n < 2:
        # 少於 2 人不更新
        return
    
    # 檢查是否有平手情況
    scores = list(score_dict.values())
    max_score = max(scores)
    winners = [p for p, s in score_dict.items() if s == max_score]
    
    # 如果有多個贏家（平手），則不更新 rating
    if len(winners) > 1:
        print(f"遊戲結果平手，玩家 {', '.join(winners)} 的 rating 不變")
        return
    
    # 取出每個玩家的資料
    users = {}
    for username in players:
        user = find_account(username)
        if user:
            users[username] = user
    
    # K 值 — 和雙人一樣
    K = 32
    
    # 1) 準備每人的舊 R
    R = {username: users[username]['rating'] for username in users}
    
    # 2) 計算每人「實際對戰得分總和」Σ s_ij
    actual = {}
    for i in players:
        if i not in users:
            continue
        si = score_dict[i]
        total = 0.0
        for j in players:
            if i == j or j not in users:
                continue
            sj = score_dict[j]
            if si > sj:
                total += 1
            elif si == sj:
                total += 0.5
        actual[i] = total
    
    # 3) 計算每人「期望得分總和」Σ E_ij
    expected = {}
    for i in players:
        if i not in users:
            continue
        Ri = R[i]
        esum = 0.0
        for j in players:
            if i == j or j not in users:
                continue
            Rj = R[j]
            esum += 1 / (1 + 10 ** ((Rj - Ri) / 400))
        expected[i] = esum
    
    # 4) 更新：先正規化，再按 Elo 公式改變 rating
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        for username in users:
            S_norm = actual[username] / (n - 1)
            E_norm = expected[username] / (n - 1)
            delta = K * (S_norm - E_norm)
            new_R = round(R[username] + delta)
            
            cursor.execute(
                "UPDATE users SET rating = ? WHERE username = ?",
                (new_R, username)
            )
        
        conn.commit()
    except:
        conn.rollback()
    finally:
        conn.close()

def get_leaderboard_data():
    """獲取排行榜數據"""
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