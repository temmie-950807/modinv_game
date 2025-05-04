# routes/leaderboard.py
from flask import render_template, jsonify
from models.database import get_leaderboard_data

def init_leaderboard_routes(app):
    """初始化與排行榜相關的路由"""
    @app.route('/leaderboard')
    def leaderboard():
        """顯示排行榜頁面"""
        return render_template('leaderboard.html')

    @app.route('/api/leaderboard')
    def get_leaderboard():
        """獲取排行榜數據 API"""
        players = get_leaderboard_data()
        return jsonify({'players': players})