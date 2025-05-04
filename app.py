# app.py
import os
import time
import secrets
from flask import Flask, session
from flask_socketio import SocketIO
from functools import wraps

# 匯入模組
from routes.auth import auth_routes
from routes.game import game_routes
from routes.leaderboard import leaderboard_routes
from models.database import init_db
from socket_handlers.game_events import register_socket_events

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "replace‑me‑with‑a‑real‑secret")
socketio = SocketIO(app, cors_allowed_origins="*")

# 確保資料庫初始化
init_db()

# 註冊路由
app.register_blueprint(auth_routes)
app.register_blueprint(game_routes)
app.register_blueprint(leaderboard_routes)

# 註冊Socket.IO事件處理器
register_socket_events(socketio)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)