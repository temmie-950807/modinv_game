# routes/game.py
from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for
from services.auth_service import find_account
from services.game_service import (
    create_game_room, join_game_room, leave_game_room, 
    get_room_id, get_room_info, join_ranked_queue, 
    check_match_status, cancel_ranked_queue,
    reset_ranked_match
)
from routes.auth import login_required

game_routes = Blueprint('game', __name__)

@game_routes.route('/')
@login_required
def index():
    username = session['username']
    user = find_account(username)
    rating = user['rating'] if user else 1500
    
    # 提供 rating_class 給模板
    rating_class = ""
    if rating >= 1900:
        rating_class = "candidate_master"
    elif rating >= 1600:
        rating_class = "expert"
    elif rating >= 1400:
        rating_class = "specialist"
    
    return render_template('index.html',
                           username=username,
                           rating=rating,
                           rating_class=rating_class)

@game_routes.route('/create_room', methods=['POST'])
@login_required
def create_room():
    username = session['username']
    room_id = request.form.get('room_id')
    difficulty = request.form.get('difficulty', 'easy')
    game_mode = request.form.get('game_mode', 'first')
    game_time = request.form.get('game_time', '30')
    question_count = int(request.form.get('question_count', '7'))
    
    result = create_game_room(username, room_id, difficulty, game_mode, game_time, question_count)
    
    if 'error' in result:
        return jsonify(result)
    
    session['room_id'] = result['room_id']
    return jsonify(result)

@game_routes.route('/join_room', methods=['POST'])
@login_required
def join_existing_room():
    username = session['username']
    room_id = request.form.get('room_id')
    
    result = join_game_room(username, room_id)
    
    if 'error' in result:
        return jsonify(result)
    
    session['room_id'] = result['room_id']
    return jsonify(result)

@game_routes.route('/leave_room', methods=['POST'])
@login_required
def leave_current_room():
    if 'username' in session and 'room_id' in session:
        username = session['username']
        room_id = session['room_id']
        
        leave_game_room(username, room_id)
        session.pop('room_id', None)
    
    return jsonify({'success': True})

@game_routes.route('/game')
@login_required
def game():
    if 'username' not in session or 'room_id' not in session:
        return redirect(url_for('game.index'))
    
    room_id = session['room_id']
    if not get_room_info(room_id):
        return redirect(url_for('game.index'))
    
    return render_template('game.html')

@game_routes.route('/get_room_id')
@login_required
def get_current_room_id():
    room_id = session.get('room_id')
    if room_id:
        room_info = get_room_info(room_id)
        if room_info:
            return jsonify({
                'room_id': room_id,
                'game_mode': room_info['game_mode']
            })
    return jsonify({'error': '未找到房間ID'})

@game_routes.route('/get_room_info')
@login_required
def get_current_room_info():
    room_id = session.get('room_id')
    if room_id:
        room = get_room_info(room_id)
        if room:
            return jsonify({
                'room_id': room_id,
                'game_mode': room['game_mode'],
                'difficulty': room['difficulty'],
                'game_time': room['game_time'],
                'question_count': room['question_count'],
                'players_count': len(room['players']),
                'is_ranked': room.get('is_ranked', room['game_mode'] == 'ranked')
            })
    return jsonify({'error': '未找到房間信息'})

@game_routes.route('/join_ranked_queue', methods=['POST'])
@login_required
def handle_join_ranked_queue():
    username = session.get('username')
    
    if not username:
        return jsonify({'error': '用戶未登入'})
    
    result = join_ranked_queue(username)
    
    if 'room_id' in result:
        session['room_id'] = result['room_id']
        
    return jsonify(result)

@game_routes.route('/check_match_status', methods=['POST'])
@login_required
def handle_check_match_status():
    username = session.get('username')
    
    if not username:
        return jsonify({'error': '用戶未登入'})
    
    result = check_match_status(username)
    
    if result.get('status') == 'matched':
        session['room_id'] = result['room_id']
        
    return jsonify(result)

@game_routes.route('/cancel_ranked_queue', methods=['POST'])
@login_required
def handle_cancel_ranked_queue():
    username = session.get('username')
    
    if not username:
        return jsonify({'error': '用戶未登入'})
    
    return jsonify(cancel_ranked_queue(username))

@game_routes.route('/reset_ranked_match', methods=['POST'])
@login_required
def handle_reset_ranked_match():
    username = session.get('username')
    
    if not username:
        return jsonify({'error': '用戶未登入'})
    
    return jsonify(reset_ranked_match(username))