# routes/game.py
from flask import render_template, request, session, jsonify, redirect, url_for
from routes.auth import login_required
from services.game_service import (
    create_game_room, join_game_room, leave_game_room, 
    get_room_info, get_room_details, reset_ranked_match,
    join_ranked_queue, check_match_status, cancel_ranked_queue
)
from services.auth_service import find_account

def init_game_routes(app):
    """初始化與遊戲相關的路由"""
    @app.route('/')
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

    @app.route('/create_room', methods=['POST'])
    @login_required
    def create_room():
        """創建新的遊戲房間"""
        username = session['username']
        room_id = request.form.get('room_id')
        difficulty = request.form.get('difficulty', 'easy')
        game_mode = request.form.get('game_mode', 'first')
        game_time = request.form.get('game_time', '30')
        question_count = int(request.form.get('question_count', '7'))
        
        result = create_game_room(username, room_id, difficulty, game_mode, 
                                game_time, question_count)
        
        if 'error' in result:
            return jsonify(result)
        
        session['room_id'] = result['room_id']
        return jsonify(result)

    @app.route('/join_room', methods=['POST'])
    @login_required
    def join_existing_room():
        """加入現有遊戲房間"""
        username = session['username']
        room_id = request.form.get('room_id')
        
        result = join_game_room(username, room_id)
        
        if 'error' in result:
            return jsonify(result)
        
        session['room_id'] = result['room_id']
        return jsonify(result)

    @app.route('/leave_room', methods=['POST'])
    @login_required
    def leave_current_room():
        """離開當前房間"""
        if 'username' in session and 'room_id' in session:
            username = session['username']
            room_id = session['room_id']
            
            result = leave_game_room(username, room_id)
            
            # 清除會話中的房間ID
            session.pop('room_id', None)
        
        return jsonify({'success': True})

    @app.route('/game')
    @login_required
    def game():
        """遊戲頁面"""
        if 'username' not in session or 'room_id' not in session:
            return redirect(url_for('index'))
        
        room_id = session['room_id']
        if not get_room_info(room_id):
            return redirect(url_for('index'))
        
        return render_template('game.html')

    @app.route('/get_room_id')
    @login_required
    def get_room_id():
        """獲取當前會話中的房間ID和基本信息"""
        if 'room_id' in session:
            room_id = session['room_id']
            room_info = get_room_info(room_id)
            if room_info:
                return jsonify({
                    'room_id': room_id,
                    'game_mode': room_info['game_mode']
                })
        return jsonify({'error': '未找到房間ID'})

    @app.route('/get_room_info')
    @login_required
    def get_room_details_route():
        """獲取當前會話中的房間詳細信息"""
        if 'room_id' in session:
            room_id = session['room_id']
            room_details = get_room_details(room_id)
            if room_details:
                return jsonify(room_details)
        return jsonify({'error': '未找到房間信息'})

    # 積分模式相關路由
    @app.route('/join_ranked_queue', methods=['POST'])
    @login_required
    def join_ranked_queue_route():
        """加入積分模式匹配隊列"""
        username = session.get('username')
        
        if not username:
            return jsonify({'error': '用戶未登入'})
        
        result = join_ranked_queue(username)
        return jsonify(result)

    @app.route('/check_match_status', methods=['POST'])
    @login_required
    def check_match_status_route():
        """檢查玩家的匹配狀態"""
        username = session.get('username')
        
        if not username:
            return jsonify({'error': '用戶未登入'})
        
        result = check_match_status(username)
        
        # 如果匹配成功，設置會話
        if result.get('status') == 'matched':
            session['room_id'] = result.get('room_id')
            
        return jsonify(result)

    @app.route('/cancel_ranked_queue', methods=['POST'])
    @login_required
    def cancel_ranked_queue_route():
        """取消積分模式匹配"""
        username = session.get('username')
        
        if not username:
            return jsonify({'error': '用戶未登入'})
        
        result = cancel_ranked_queue(username)
        return jsonify(result)

    @app.route('/reset_ranked_match', methods=['POST'])
    @login_required
    def reset_ranked_match_route():
        """重置卡住的積分模式匹配"""
        username = session.get('username')
        
        if not username:
            return jsonify({'error': '用戶未登入'})
        
        result = reset_ranked_match(username)
        return jsonify(result)