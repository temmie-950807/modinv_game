#!/usr/bin/env python3
"""
初始化模反元素遊戲的 SQLite 資料庫
"""

from db_utils import init_db
import os

# 檢查資料庫檔案是否已存在
DB_FILE = os.path.join(os.path.dirname(__file__), 'modular_inverse_game.db')

if os.path.exists(DB_FILE):
    overwrite = input(f"資料庫檔案 '{DB_FILE}' 已存在，是否要覆蓋? (y/n): ")
    if overwrite.lower() != 'y':
        print("取消操作")
        exit()
    os.remove(DB_FILE)
    print(f"已刪除舊資料庫檔案")

# 初始化資料庫
init_db()
print(f"資料庫已初始化於 '{DB_FILE}'")
