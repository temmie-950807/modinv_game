# app.py
import os
from datetime import timedelta
from flask import Flask
from flask_socketio import SocketIO

# 導入各模組初始化函數
from routes.auth import init_auth_routes
from routes.game import init_game_routes
from routes.leaderboard import init_leaderboard_routes
from socket_handlers.game_events import init_socket_events
from models.database import init_db

# 創建 Flask 應用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "replace‑me‑with‑a‑real‑secret")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# 初始化 SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# 確保資料庫初始化
init_db()

# 初始化各模組
init_auth_routes(app)
init_game_routes(app)
init_leaderboard_routes(app)
init_socket_events(socketio)

# 在請求前更新永久會話設定
@app.before_request
def refresh_permanent_session():
    from flask import session
    if 'username' in session:
        session.permanent = True

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)