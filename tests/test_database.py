import sys
import os
import unittest
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock

# 添加專案根目錄到 Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.database import init_db, find_account, register_account, verify_account, update_user_rating, update_ratings, get_leaderboard_data

class TestDatabase(unittest.TestCase):
    """測試 database.py 中的數據庫功能"""

    def setUp(self):
        """每個測試前準備測試環境"""
        # 創建臨時資料庫文件
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # 修改資料庫路徑指向測試用臨時資料庫
        self.original_db_file = os.environ.get('DB_FILE', '')
        os.environ['DB_FILE'] = self.db_path
        
        # 初始化測試資料庫
        with patch('models.database.DB_FILE', self.db_path):
            init_db()

    def tearDown(self):
        """每個測試後清理測試環境"""
        # 關閉資料庫連接
        os.close(self.db_fd)
        
        # 刪除測試用臨時資料庫
        os.unlink(self.db_path)
        
        # 恢復原始資料庫路徑
        if self.original_db_file:
            os.environ['DB_FILE'] = self.original_db_file
        else:
            os.environ.pop('DB_FILE', None)

    def test_init_db(self):
        """測試資料庫初始化函數"""
        # 設置模擬值
        with patch('models.database.DB_FILE', self.db_path):
            # 執行初始化
            init_db()
            
            # 檢查是否成功創建資料表
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 檢查是否存在 users 資料表
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
            self.assertIsNotNone(cursor.fetchone())
            
            # 檢查資料表結構
            cursor.execute('PRAGMA table_info(users)')
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            self.assertIn('id', column_names)
            self.assertIn('username', column_names)
            self.assertIn('pw_hash', column_names)
            self.assertIn('rating', column_names)
            
            conn.close()

    def test_register_and_find_account(self):
        """測試帳號註冊與查詢功能"""
        # 設置模擬值
        with patch('models.database.DB_FILE', self.db_path):
            # 註冊新帳號
            result = register_account('testuser', 'password123')
            self.assertTrue(result)
            
            # 嘗試註冊已存在的帳號
            result = register_account('testuser', 'anotherpassword')
            self.assertFalse(result)
            
            # 測試帳號查詢
            user = find_account('testuser')
            self.assertIsNotNone(user)
            self.assertEqual(user['username'], 'testuser')
            self.assertEqual(user['rating'], 1500)
            
            # 測試查詢不存在的帳號
            user = find_account('nonexistentuser')
            self.assertIsNone(user)

    def test_verify_account(self):
        """測試帳號驗證功能"""
        # 設置模擬值
        with patch('models.database.DB_FILE', self.db_path):
            register_account('testuser', 'password123')
            
            # 正確的密碼
            self.assertTrue(verify_account('testuser', 'password123'))
            
            # 錯誤的密碼
            self.assertFalse(verify_account('testuser', 'wrongpassword'))
            
            # 不存在的帳號
            self.assertFalse(verify_account('nonexistentuser', 'password123'))

    def test_update_user_rating(self):
        """測試更新使用者積分功能"""
        # 設置模擬值
        with patch('models.database.DB_FILE', self.db_path):
            register_account('testuser', 'password123')
            
            # 更新積分
            result = update_user_rating('testuser', 1600)
            self.assertTrue(result)
            
            # 檢查積分是否更新成功
            user = find_account('testuser')
            self.assertEqual(user['rating'], 1600)
            
            # 測試更新不存在的用戶積分
            result = update_user_rating('nonexistentuser', 1700)
            self.assertTrue(result)  # 應該返回 True，但實際上不會更新任何記錄

    def test_update_ratings(self):
        """測試多人積分更新功能"""
        # 設置模擬值
        with patch('models.database.DB_FILE', self.db_path):
            register_account('player1', 'password123')
            register_account('player2', 'password123')
            register_account('player3', 'password123')
            
            # 模擬遊戲積分結果（player1 獲勝）
            score_dict = {
                'player1': 3,
                'player2': 1,
                'player3': 0
            }
            
            # 更新積分
            update_ratings(score_dict)
            
            # 檢查積分變化
            player1 = find_account('player1')
            player2 = find_account('player2')
            player3 = find_account('player3')
            
            # 由於 rating 計算基於 ELO 算法，無法精確預測結果
            # 但可以檢查 player1 應該獲得積分增加
            self.assertGreater(player1['rating'], 1500)

    def test_get_leaderboard_data(self):
        """測試獲取排行榜數據功能"""
        # 設置模擬值
        with patch('models.database.DB_FILE', self.db_path):
            register_account('player1', 'password123')
            register_account('player2', 'password123')
            register_account('player3', 'password123')
            
            update_user_rating('player1', 1800)
            update_user_rating('player2', 1600)
            update_user_rating('player3', 2000)
            
            # 獲取排行榜數據
            leaderboard = get_leaderboard_data()
            
            # 檢查排行榜順序是否正確（按積分降序排列）
            self.assertEqual(len(leaderboard), 3)
            self.assertEqual(leaderboard[0]['username'], 'player3')
            self.assertEqual(leaderboard[0]['rating'], 2000)
            self.assertEqual(leaderboard[1]['username'], 'player1')
            self.assertEqual(leaderboard[1]['rating'], 1800)
            self.assertEqual(leaderboard[2]['username'], 'player2')
            self.assertEqual(leaderboard[2]['rating'], 1600)

if __name__ == '__main__':
    unittest.main()