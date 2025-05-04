import sys
import os
import tempfile
import pytest
from unittest.mock import patch

# 添加專案根目錄到 Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app
from models.database import init_db, register_account

@pytest.fixture
def client():
    """創建一個測試用的 Flask 客戶端"""
    # 創建臨時資料庫文件
    db_fd, db_path = tempfile.mkstemp()
    
    # 設置應用配置
    app.app.config['TESTING'] = True
    app.app.config['SECRET_KEY'] = 'test_secret_key'
    
    # 修改資料庫路徑
    original_db_file = os.environ.get('DB_FILE', '')
    os.environ['DB_FILE'] = db_path
    
    # 初始化測試資料庫
    with patch('models.database.DB_FILE', db_path):
        init_db()
    
    # 創建測試客戶端
    with app.app.test_client() as client:
        # 設置應用上下文
        with app.app.app_context():
            yield client
    
    # 清理
    os.close(db_fd)
    os.unlink(db_path)
    
    # 恢復原始資料庫路徑
    if original_db_file:
        os.environ['DB_FILE'] = original_db_file
    else:
        os.environ.pop('DB_FILE', None)

@pytest.fixture
def authenticated_client(client):
    """創建一個已認證的測試客戶端"""
    # 註冊測試用戶
    with patch('models.database.DB_FILE', os.environ.get('DB_FILE')):
        register_account('testuser', 'password123')
    
    # 登入測試用戶
    client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    })
    
    return client

@pytest.fixture
def socket_client():
    """創建一個 SocketIO 測試客戶端"""
    # 創建臨時資料庫文件
    db_fd, db_path = tempfile.mkstemp()
    
    # 設置應用配置
    app.app.config['TESTING'] = True
    app.app.config['SECRET_KEY'] = 'test_secret_key'
    
    # 修改資料庫路徑
    original_db_file = os.environ.get('DB_FILE', '')
    os.environ['DB_FILE'] = db_path
    
    # 初始化測試資料庫
    with patch('models.database.DB_FILE', db_path):
        init_db()
    
    # 創建 SocketIO 測試客戶端
    from flask_socketio import SocketIOTestClient
    socket_client = SocketIOTestClient(app.app, app.socketio)
    
    # 註冊並登入測試用戶
    with patch('models.database.DB_FILE', db_path):
        register_account('testuser', 'password123')
    
    with app.app.test_client() as client:
        client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        })
        # 模擬 session (雖然在實際使用中 SocketIOTestClient 無法共享 Flask session)
        socket_client.session = {'username': 'testuser'}
    
    yield socket_client
    
    # 清理
    os.close(db_fd)
    os.unlink(db_path)
    
    # 恢復原始資料庫路徑
    if original_db_file:
        os.environ['DB_FILE'] = original_db_file
    else:
        os.environ.pop('DB_FILE', None)