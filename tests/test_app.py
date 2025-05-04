import sys
import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock

# 添加專案根目錄到 Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app
from models.database import init_db, register_account, update_user_rating

class TestApp(unittest.TestCase):
    """測試 app.py 中的 Flask 應用功能"""

    def setUp(self):
        """每個測試前準備測試環境"""
        # 創建臨時資料庫文件
        self.db_fd, self.db_path = tempfile.mkstemp()
        
        # 修改資料庫路徑指向測試用臨時資料庫
        app.app.config['TESTING'] = True
        self.original_db_file = os.environ.get('DB_FILE', '')
        os.environ['DB_FILE'] = self.db_path
        
        # 設置測試用 secret key
        app.app.config['SECRET_KEY'] = 'test_secret_key'
        
        # 初始化測試資料庫
        with patch('models.database.DB_FILE', self.db_path):
            init_db()
        
        # 創建測試客戶端
        self.client = app.app.test_client()
        
        # 保存原始房間數據以便測試後恢復
        self.original_rooms = app.rooms.copy()
        
        # 清空測試前的房間數據
        app.rooms.clear()

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
        
        # 恢復原始房間數據
        app.rooms.clear()
        app.rooms.update(self.original_rooms)

    def test_index_redirect_when_not_logged_in(self):
        """測試未登入時首頁重定向到登入頁面"""
        response = self.client.get('/', follow_redirects=False)
        self.assertEqual(response.status_code, 302)  # 302表示重定向
        self.assertTrue('/login' in response.location)

    def test_register_page(self):
        """測試註冊頁面"""
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)

        # 測試註冊功能
        with patch('models.database.DB_FILE', self.db_path):
            response = self.client.post('/register', data={
                'username': 'testuser',
                'password': 'password123'
            }, follow_redirects=True)
            
            self.assertEqual(response.status_code, 200)
            
            # 測試重複註冊
            response = self.client.post('/register', data={
                'username': 'testuser',
                'password': 'anotherpassword'
            })
            
            self.assertEqual(response.status_code, 200)

    def test_login_page(self):
        """測試登入頁面"""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)

        # 註冊一個測試帳號
        with patch('models.database.DB_FILE', self.db_path):
            register_account('testuser', 'password123')
            
            # 測試登入功能 - 正確的帳號密碼
            response = self.client.post('/login', data={
                'username': 'testuser',
                'password': 'password123',
                'remember': '1'
            }, follow_redirects=True)
            
            self.assertEqual(response.status_code, 200)
            
            # 測試登入功能 - 錯誤的密碼
            response = self.client.post('/login', data={
                'username': 'testuser',
                'password': 'wrongpassword'
            })
            
            self.assertEqual(response.status_code, 200)
            
            # 測試登入功能 - 不存在的帳號
            response = self.client.post('/login', data={
                'username': 'nonexistentuser',
                'password': 'password123'
            })
            
            self.assertEqual(response.status_code, 200)

    def test_logout(self):
        """測試登出功能"""
        # 先登入
        with patch('models.database.DB_FILE', self.db_path):
            register_account('testuser', 'password123')
            
            self.client.post('/login', data={
                'username': 'testuser',
                'password': 'password123'
            })
            
            # 測試登出
            response = self.client.get('/logout', follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            
            # 登出後應無法訪問首頁
            response = self.client.get('/', follow_redirects=False)
            self.assertEqual(response.status_code, 302)

    def test_create_room(self):
        """測試創建房間功能"""
        # 先登入
        with patch('models.database.DB_FILE', self.db_path):
            register_account('testuser', 'password123')
            
            with self.client.session_transaction() as session:
                session['username'] = 'testuser'
            
            # 測試創建房間
            response = self.client.post('/create_room', data={
                'room_id': 'test123',
                'difficulty': 'easy',
                'game_mode': 'first',
                'game_time': '30',
                'question_count': '7'
            })
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertEqual(json_data['room_id'], 'test123')
            
            # 測試重複創建同一房間
            response = self.client.post('/create_room', data={
                'room_id': 'test123',
                'difficulty': 'medium',
                'game_mode': 'speed',
                'game_time': '15'
            })
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertIn('error', json_data)
            self.assertIn('\u623f\u9593\u5df2\u5b58\u5728', json_data['error'])  # 使用 Unicode 轉義序列

    def test_join_room(self):
        """測試加入房間功能"""
        # 先登入兩個用戶
        with patch('models.database.DB_FILE', self.db_path):
            register_account('user1', 'password123')
            register_account('user2', 'password123')
            
            # 用戶1創建房間
            with self.client.session_transaction() as session:
                session['username'] = 'user1'
            
            self.client.post('/create_room', data={
                'room_id': 'test123',
                'difficulty': 'easy',
                'game_mode': 'first'
            })
            
            # 用戶2加入房間
            with self.client.session_transaction() as session:
                session['username'] = 'user2'
            
            response = self.client.post('/join_room', data={
                'room_id': 'test123'
            })
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertEqual(json_data['room_id'], 'test123')
            
            # 測試加入不存在的房間
            response = self.client.post('/join_room', data={
                'room_id': 'nonexistent'
            })
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertIn('error', json_data)
            self.assertIn('\u627e\u4e0d\u5230\u6b64\u623f\u9593', json_data['error'])  # 使用 Unicode 轉義序列
            
            # 測試加入練習模式房間
            # 先讓用戶1創建一個練習模式房間
            with self.client.session_transaction() as session:
                session['username'] = 'user1'
            
            self.client.post('/create_room', data={
                'room_id': 'practice123',
                'difficulty': 'easy',
                'game_mode': 'practice'
            })
            
            # 用戶2嘗試加入練習模式房間
            with self.client.session_transaction() as session:
                session['username'] = 'user2'
            
            response = self.client.post('/join_room', data={
                'room_id': 'practice123'
            })
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertIn('error', json_data)
            self.assertIn('\u7df4\u7fd2\u6a21\u5f0f', json_data['error'])  # 使用 Unicode 轉義序列

    def test_get_room_id(self):
        """測試獲取房間ID功能"""
        # 先登入並創建房間
        with patch('models.database.DB_FILE', self.db_path):
            register_account('testuser', 'password123')
            
            with self.client.session_transaction() as session:
                session['username'] = 'testuser'
            
            self.client.post('/create_room', data={
                'room_id': 'test123',
                'difficulty': 'easy',
                'game_mode': 'first'
            })
            
            # 設置 session
            with self.client.session_transaction() as session:
                session['room_id'] = 'test123'
            
            # 測試獲取房間ID
            response = self.client.get('/get_room_id')
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertEqual(json_data['room_id'], 'test123')
            self.assertEqual(json_data['game_mode'], 'first')
            
            # 測試無房間時的情況
            with self.client.session_transaction() as session:
                if 'room_id' in session:
                    del session['room_id']
            
            response = self.client.get('/get_room_id')
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertIn('error', json_data)

    def test_leave_room(self):
        """測試離開房間功能"""
        # 先登入兩個用戶
        with patch('models.database.DB_FILE', self.db_path):
            register_account('user1', 'password123')
            register_account('user2', 'password123')
            
            # 用戶1創建房間
            with self.client.session_transaction() as session:
                session['username'] = 'user1'
            
            self.client.post('/create_room', data={
                'room_id': 'test123',
                'difficulty': 'easy',
                'game_mode': 'first'
            })
            
            # 用戶2加入房間
            with self.client.session_transaction() as session:
                session['username'] = 'user2'
                session['room_id'] = 'test123'
            
            self.client.post('/join_room', data={
                'room_id': 'test123'
            })
            
            # 用戶2離開房間
            response = self.client.post('/leave_room')
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertTrue(json_data['success'])
            
            # 檢查 session 是否清理
            with self.client.session_transaction() as session:
                self.assertNotIn('room_id', session)
            
            # 測試用戶1離開後房間應被刪除
            with self.client.session_transaction() as session:
                session['username'] = 'user1'
                session['room_id'] = 'test123'
            
            response = self.client.post('/leave_room')
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertTrue(json_data['success'])
            
            # 測試房間是否已刪除
            with self.client.session_transaction() as session:
                session['username'] = 'user2'
            
            response = self.client.post('/join_room', data={
                'room_id': 'test123'
            })
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertIn('error', json_data)
            self.assertIn('\u627e\u4e0d\u5230\u6b64\u623f\u9593', json_data['error'])  # 使用 Unicode 轉義序列

    def test_leaderboard(self):
        """測試排行榜頁面"""
        response = self.client.get('/leaderboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<title>\xe6\xa8\xa1\xe5\x8f\x8d\xe5\x85\x83\xe7\xb4\xa0\xe7\xab\xb6\xe8\xb3\xbd - \xe6\x8e\x92\xe8\xa1\x8c\xe6\xa6\x9c</title>', response.data)

    def test_get_leaderboard_api(self):
        """測試獲取排行榜API"""
        # 先添加一些用戶
        with patch('models.database.DB_FILE', self.db_path):
            register_account('player1', 'password123')
            register_account('player2', 'password123')
            
            # 更新積分 - 直接使用引入的模組函數
            update_user_rating('player1', 1800)
            update_user_rating('player2', 1600)
            
            # 測試API
            response = self.client.get('/api/leaderboard')
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertIn('players', json_data)
            self.assertEqual(len(json_data['players']), 2)
            
            # 檢查排序
            self.assertEqual(json_data['players'][0]['username'], 'player1')
            self.assertEqual(json_data['players'][0]['rating'], 1800)
            self.assertEqual(json_data['players'][1]['username'], 'player2')
            self.assertEqual(json_data['players'][1]['rating'], 1600)

    def test_get_room_info(self):
        """測試獲取房間詳細信息功能"""
        # 先登入
        with patch('models.database.DB_FILE', self.db_path):
            register_account('testuser', 'password123')
            
            # 設置用戶會話
            with self.client.session_transaction() as session:
                session['username'] = 'testuser'
            
            # 創建房間前確保 session 中沒有舊的 room_id
            with self.client.session_transaction() as session:
                if 'room_id' in session:
                    del session['room_id']
            
            # 創建一個房間
            response = self.client.post('/create_room', data={
                'room_id': 'test123',
                'difficulty': 'medium',
                'game_mode': 'first',
                'game_time': '30',
                'question_count': 15
            })
            
            # 檢查創建房間的響應
            self.assertEqual(response.status_code, 200)
            create_data = response.get_json()
            self.assertEqual(create_data['room_id'], 'test123')
            
            # 檢查會話中是否設置了 room_id - create_room 應該已經設置了 session
            with self.client.session_transaction() as session:
                self.assertIn('room_id', session)
                self.assertEqual(session['room_id'], 'test123')
            
            # 確保 app.rooms 中有該房間
            self.assertIn('test123', app.rooms, "app.rooms 中找不到房間")
            
            # 測試獲取房間詳細信息
            response = self.client.get('/get_room_info')
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertEqual(json_data['room_id'], 'test123')
            self.assertEqual(json_data['game_mode'], 'first')
            self.assertEqual(json_data['difficulty'], 'medium')
            self.assertEqual(json_data['game_time'], '30')
            self.assertEqual(json_data['question_count'], 15)
            self.assertEqual(json_data['players_count'], 1)
            
            # 測試無房間時的情況
            with self.client.session_transaction() as session:
                if 'room_id' in session:
                    del session['room_id']
            
            response = self.client.get('/get_room_info')
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertIn('error', json_data)

    def test_ranked_queue(self):
        """測試積分模式隊列功能"""
        # 先登入
        with patch('models.database.DB_FILE', self.db_path):
            register_account('testuser', 'password123')
            
            with self.client.session_transaction() as session:
                session['username'] = 'testuser'
            
            # 測試加入積分模式隊列
            response = self.client.post('/join_ranked_queue')
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertEqual(json_data['status'], 'waiting')
            
            # 測試重複加入
            response = self.client.post('/join_ranked_queue')
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertEqual(json_data['status'], 'waiting')
            
            # 測試取消匹配
            response = self.client.post('/cancel_ranked_queue')
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertEqual(json_data['status'], 'canceled')
            
    def test_check_match_status(self):
        """測試檢查匹配狀態功能"""
        # 先登入
        with patch('models.database.DB_FILE', self.db_path):
            register_account('testuser', 'password123')
            
            with self.client.session_transaction() as session:
                session['username'] = 'testuser'
            
            # 測試檢查匹配狀態
            response = self.client.post('/check_match_status')
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertEqual(json_data['status'], 'not_in_queue')
            
            # 測試加入隊列後的狀態
            self.client.post('/join_ranked_queue')
            response = self.client.post('/check_match_status')
            
            self.assertEqual(response.status_code, 200)
            json_data = response.get_json()
            self.assertEqual(json_data['status'], 'waiting')

if __name__ == '__main__':
    unittest.main()