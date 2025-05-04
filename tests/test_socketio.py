import sys
import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock

# 添加專案根目錄到 Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app
from models.database import init_db, register_account
from flask_socketio import SocketIOTestClient

class TestSocketIO(unittest.TestCase):
    """測試 SocketIO 相關功能"""

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
        
        # 註冊一個測試用戶
        with patch('models.database.DB_FILE', self.db_path):
            register_account('testuser', 'password123')
            register_account('testuser2', 'password123')
        
        # 創建一個 Flask 測試客戶端
        self.client = app.app.test_client()
        
        # 保存原始房間數據以便測試後恢復
        self.original_rooms = app.rooms.copy()
        self.original_ranked_queue = app.ranked_queue.copy() if isinstance(app.ranked_queue, list) else app.ranked_queue[:]
        
        # 清空測試前的房間數據
        app.rooms.clear()
        if isinstance(app.ranked_queue, list):
            app.ranked_queue.clear()
        else:
            app.ranked_queue = []
        
        # 創建 SocketIO 測試客戶端
        self.socketio_client = SocketIOTestClient(app.app, app.socketio)
        
        # 創建測試房間
        with app.app.test_request_context('/'):
            app.session['username'] = 'testuser'
            app.session['room_id'] = 'test123'
            
            # 創建一個測試房間
            app.rooms['test123'] = {
                'players': ['testuser'],
                'ready': {},
                'scores': {'testuser': 0},
                'current_question': {
                    'p': 11,
                    'a': 3,
                    'answer': 4,
                    'time_started': app.time.time()
                },
                'question_number': 1,
                'answers': {},
                'game_started': False,
                'question_timer': None,
                'difficulty': 'easy',
                'game_mode': 'first',
                'game_time': '30',
                'question_count': 7,
                'correct_order': [],
                'first_correct_done': False,
                'is_practice': False
            }

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
        
        # 恢復原始隊列數據
        if isinstance(app.ranked_queue, list):
            app.ranked_queue.clear()
            app.ranked_queue.extend(self.original_ranked_queue)
        else:
            app.ranked_queue = self.original_ranked_queue

    def test_socket_connect(self):
        """測試 SocketIO 連接"""
        # 使用測試請求上下文
        with app.app.test_request_context('/'):
            # 設置會話
            app.session['username'] = 'testuser'
            app.session['room_id'] = 'test123'
            
            # 連接到 Socket.IO
            self.socketio_client.connect()
            
            # 斷開連接
            self.socketio_client.disconnect()

    def test_player_ready(self):
        """測試玩家準備功能"""
        # 使用測試請求上下文
        with app.app.test_request_context('/'):
            # 設置會話
            app.session['username'] = 'testuser'
            app.session['room_id'] = 'test123'
            
            # 連接到 Socket.IO
            self.socketio_client.connect()
            self.socketio_client.get_received()  # 清除初始消息
            
            # 使用 Socket.IO 測試客戶端發送準備消息
            self.socketio_client.emit('player_ready')
            
            # 斷開連接
            self.socketio_client.disconnect()

    @patch('app.next_question')
    def test_submit_answer(self, mock_next_question):
        """測試提交答案功能"""
        # 使用測試請求上下文
        with app.app.test_request_context('/'):
            # 設置會話
            app.session['username'] = 'testuser'
            app.session['room_id'] = 'test123'
            
            # 連接到 Socket.IO
            self.socketio_client.connect()
            self.socketio_client.get_received()  # 清除初始消息
            
            # 發送答案
            self.socketio_client.emit('submit_answer', {'answer': '4'})
            
            # 斷開連接
            self.socketio_client.disconnect()

    def test_game_countdown(self):
        """測試遊戲倒數功能"""
        # 使用測試請求上下文
        with app.app.test_request_context('/'):
            # 設置會話
            app.session['username'] = 'testuser'
            app.session['room_id'] = 'test123'
            
            # 連接到 Socket.IO
            self.socketio_client.connect()
            self.socketio_client.get_received()  # 清除初始消息
            
            # 模擬遊戲開始倒數
            app.socketio.emit('game_countdown', {'countdown': 3}, room='test123')
            
            # 斷開連接
            self.socketio_client.disconnect()

    def test_ranked_countdown(self):
        """測試積分模式倒數功能"""
        # 使用測試請求上下文
        with app.app.test_request_context('/'):
            # 設置會話
            app.session['username'] = 'testuser'
            app.session['room_id'] = 'test123'
            
            # 設置房間為積分模式
            app.rooms['test123']['is_ranked'] = True
            app.rooms['test123']['match_time'] = app.time.time() - 3  # 已經過了3秒
            
            # 連接到 Socket.IO
            self.socketio_client.connect()
            self.socketio_client.get_received()  # 清除初始消息
            
            # 發送積分模式倒數檢查
            self.socketio_client.emit('check_ranked_countdown')
            
            # 獲取接收到的消息
            received = self.socketio_client.get_received()
            
            # 斷開連接
            self.socketio_client.disconnect()

    def test_game_over(self):
        """測試遊戲結束功能"""
        # 使用測試請求上下文
        with app.app.test_request_context('/'):
            # 設置會話
            app.session['username'] = 'testuser'
            app.session['room_id'] = 'test123'
            
            # 設置房間狀態
            app.rooms['test123']['players'] = ['testuser', 'testuser2']
            app.rooms['test123']['scores'] = {'testuser': 3, 'testuser2': 1}
            app.rooms['test123']['game_started'] = True
            app.rooms['test123']['ready'] = {'testuser': True, 'testuser2': True}
            
            # 連接到 Socket.IO
            self.socketio_client.connect()
            self.socketio_client.get_received()  # 清除初始消息
            
            # 模擬遊戲結束
            app.end_game('test123')
            
            # 獲取接收到的消息
            received = self.socketio_client.get_received()
            
            # 確認房間狀態已重置
            self.assertFalse(app.rooms['test123']['game_started'])
            self.assertEqual(app.rooms['test123']['question_number'], 0)
            self.assertEqual(app.rooms['test123']['ready'], {})
            
            # 斷開連接
            self.socketio_client.disconnect()

    def test_user_disconnect(self):
        """測試用戶斷開連接功能"""
        # 使用測試請求上下文
        with app.app.test_request_context('/'):
            # 設置會話
            app.session['username'] = 'testuser'
            app.session['room_id'] = 'test123'
            
            # 連接到 Socket.IO
            self.socketio_client.connect()
            self.socketio_client.get_received()  # 清除初始消息
            
            # 斷開連接
            self.socketio_client.disconnect()

if __name__ == '__main__':
    unittest.main()