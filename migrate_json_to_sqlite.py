#!/usr/bin/env python3
"""
將現有的 JSON 格式使用者資料遷移到 SQLite 資料庫
"""

import json
import os
import sqlite3
from db_utils import init_db, register_account, find_account, update_user_rating

# JSON 檔案路徑
JSON_FILE = os.path.join(os.path.dirname(__file__), 'accounts.json')
DB_FILE = os.path.join(os.path.dirname(__file__), 'modular_inverse_game.db')

def load_json_accounts():
    """從 JSON 檔案載入帳號資料"""
    if not os.path.exists(JSON_FILE):
        print(f"找不到 JSON 檔案 '{JSON_FILE}'")
        return []
    
    try:
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
        return accounts
    except json.JSONDecodeError:
        print(f"JSON 檔案 '{JSON_FILE}' 格式錯誤")
        return []

def migrate_accounts():
    """將帳號資料從 JSON 遷移到 SQLite"""
    # 確保資料庫已初始化
    init_db()
    
    # 載入 JSON 帳號資料
    accounts = load_json_accounts()
    if not accounts:
        print("沒有找到有效的 JSON 帳號資料")
        return
    
    print(f"找到 {len(accounts)} 個帳號資料")
    
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
            print(f"跳過無效帳號: {account}")
            skipped += 1
            continue
        
        # 檢查帳號是否已存在
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            print(f"帳號 '{username}' 已存在，更新其 rating")
            cursor.execute("UPDATE users SET rating = ? WHERE username = ?", (rating, username))
            migrated += 1
        else:
            print(f"新增帳號 '{username}'")
            cursor.execute(
                "INSERT INTO users (username, pw_hash, rating) VALUES (?, ?, ?)",
                (username, pw_hash, rating)
            )
            migrated += 1
    
    conn.commit()
    conn.close()
    
    print(f"遷移完成: {migrated} 個帳號已遷移，{skipped} 個帳號已跳過")
    print(f"建議備份原始 JSON 檔案，然後可以刪除 '{JSON_FILE}'")

if __name__ == "__main__":
    if not os.path.exists(JSON_FILE):
        print(f"找不到 JSON 檔案 '{JSON_FILE}'")
        exit(1)
    
    proceed = input(f"確認將帳號資料從 '{JSON_FILE}' 遷移到 '{DB_FILE}'? (y/n): ")
    if proceed.lower() != 'y':
        print("取消操作")
        exit()
    
    migrate_accounts()