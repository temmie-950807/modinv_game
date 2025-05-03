# routes/leaderboard.py
from flask import Blueprint, render_template, jsonify
from models.database import get_all_users

leaderboard_routes = Blueprint('leaderboard', __name__)

@leaderboard_routes.route('/leaderboard')
def leaderboard():
    """Show the leaderboard of all players"""
    return render_template('leaderboard.html')

@leaderboard_routes.route('/api/leaderboard')
def get_leaderboard():
    """Get the leaderboard data as JSON"""
    players = get_all_users()
    # 依照積分排序
    sorted_players = sorted(players, key=lambda x: x['rating'], reverse=True)
    
    return jsonify({'players': sorted_players})