# app.py
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, emit
import random
import math
import secrets
import os
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_hex(16)
socketio = SocketIO(app, cors_allowed_origins="*")

# 遊戲房間數據
rooms = {}

def is_prime(n):
    """檢查一個數是否為質數"""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

def get_primes(start, end):
    """獲取指定範圍內的所有質數"""
    return [num for num in range(start, end + 1) if is_prime(num)]

def extended_gcd(a, b):
    """擴展歐幾里得算法，用於計算模反元素"""
    if a == 0:
        return b, 0, 1
    else:
        gcd, x, y = extended_gcd(b % a, a)
        return gcd, y - (b // a) * x, x

def mod_inverse(a, m):
    """計算模反元素"""
    if math.gcd(a, m) != 1:
        return None  # 不存在模反元素
    else:
        _, x, _ = extended_gcd(a, m)
        return (x % m + m) % m  # 確保結果為正數

def generate_question():
    """生成一個有關模反元素的問題"""
    primes = get_primes(2, 50)
    p = random.choice(primes)
    
    # 選擇 a，確保 a 和 p 互質 (這裡小於 p 的數一定與 p 互質，因為 p 是質數)
    a = random.randint(1, p - 1)
    
    answer = mod_inverse(a, p)
    return {
        'p': p,
        'a': a,
        'answer': answer,
        'time_started': time.time()  # 記錄問題開始時間
    }

@app.route('/')
def index():
    # 清除任何現有的會話數據
    session.clear()
    return render_template('index.html')

@app.route('/create_room', methods=['POST'])
def create_room():
    """創建新的遊戲房間"""
    username = request.form.get('username')
    room_id = request.form.get('room_id')
    
    if not room_id:
        # 創建一個6位數的隨機房間ID
        room_id = ''.join(random.choices('0123456789', k=6))
    
    if room_id in rooms:
        return jsonify({'error': '房間已存在，請選擇其他房間ID'})
    
    session['username'] = username
    session['room_id'] = room_id
    
    rooms[room_id] = {
        'players': [username],
        'ready': {},
        'scores': {username: 0},
        'current_question': None,
        'question_number': 0,
        'answers': {},
        'game_started': False,
        'question_timer': None
    }
    
    return jsonify({'room_id': room_id})

@app.route('/join_room', methods=['POST'])
def join_existing_room():
    """加入現有遊戲房間"""
    username = request.form.get('username')
    room_id = request.form.get('room_id')
    
    if not room_id in rooms:
        return jsonify({'error': '找不到此房間'})
    
    if len(rooms[room_id]['players']) >= 2:
        return jsonify({'error': '房間已滿'})
    
    session['username'] = username
    session['room_id'] = room_id
    
    rooms[room_id]['players'].append(username)
    rooms[room_id]['scores'][username] = 0
    
    return jsonify({'room_id': room_id})

@app.route('/leave_room', methods=['POST'])
def leave_current_room():
    """離開當前房間"""
    if 'username' in session and 'room_id' in session:
        username = session['username']
        room_id = session['room_id']
        
        if room_id in rooms and username in rooms[room_id]['players']:
            rooms[room_id]['players'].remove(username)
            
            if username in rooms[room_id]['scores']:
                del rooms[room_id]['scores'][username]
            
            if username in rooms[room_id]['ready']:
                del rooms[room_id]['ready'][username]
            
            # 如果房間空了，刪除房間
            if len(rooms[room_id]['players']) == 0:
                del rooms[room_id]
            else:
                # 通知房間內其他玩家
                socketio.emit('user_left', {'username': username}, room=room_id)
                socketio.emit('room_status', {
                    'players': rooms[room_id]['players'],
                    'scores': rooms[room_id]['scores'],
                    'game_started': rooms[room_id]['game_started']
                }, room=room_id)
        
        # 清除會話
        session.pop('username', None)
        session.pop('room_id', None)
        
    return jsonify({'success': True})

@socketio.on('connect')
def handle_connect():
    if 'username' in session and 'room_id' in session:
        username = session['username']
        room_id = session['room_id']
        
        if room_id in rooms:
            join_room(room_id)
            emit('user_joined', {'username': username}, room=room_id)
            
            # 更新房間狀態
            emit('room_status', {
                'players': rooms[room_id]['players'],
                'scores': rooms[room_id]['scores'],
                'game_started': rooms[room_id]['game_started'],
                'room_id': room_id  # 確保房間ID被傳回
            }, room=room_id)

@socketio.on('disconnect')
def handle_disconnect():
    if 'username' in session and 'room_id' in session:
        username = session['username']
        room_id = session['room_id']
        
        if room_id in rooms:
            if username in rooms[room_id]['players']:
                rooms[room_id]['players'].remove(username)
                
                if username in rooms[room_id]['scores']:
                    del rooms[room_id]['scores'][username]
                
                if username in rooms[room_id]['ready']:
                    del rooms[room_id]['ready'][username]
                
                if len(rooms[room_id]['players']) == 0:
                    del rooms[room_id]
                else:
                    emit('user_left', {'username': username}, room=room_id)
                    emit('room_status', {
                        'players': rooms[room_id]['players'],
                        'scores': rooms[room_id]['scores'],
                        'game_started': rooms[room_id]['game_started']
                    }, room=room_id)
            
        leave_room(room_id)

@socketio.on('player_ready')
def handle_player_ready():
    username = session.get('username')
    room_id = session.get('room_id')
    
    if not (username and room_id and room_id in rooms):
        return
    
    rooms[room_id]['ready'][username] = True
    
    # 檢查是否所有玩家都準備好了
    all_ready = len(rooms[room_id]['ready']) == len(rooms[room_id]['players']) and len(rooms[room_id]['players']) == 2
    
    if all_ready and not rooms[room_id]['game_started']:
        rooms[room_id]['game_started'] = True
        start_game(room_id)
    else:
        emit('player_ready_status', {
            'username': username,
            'ready_count': len(rooms[room_id]['ready']),
            'total_players': len(rooms[room_id]['players'])
        }, room=room_id)

def start_game(room_id):
    """開始遊戲"""
    if room_id not in rooms:
        return
    
    rooms[room_id]['question_number'] = 1
    rooms[room_id]['scores'] = {player: 0 for player in rooms[room_id]['players']}
    rooms[room_id]['answers'] = {}
    
    emit('game_started', room=room_id)
    next_question(room_id)

def next_question(room_id):
    """生成下一個問題"""
    if room_id not in rooms:
        return
    
    if rooms[room_id]['question_number'] > 7:
        # 遊戲結束
        end_game(room_id)
        return
    
    question = generate_question()
    rooms[room_id]['current_question'] = question
    rooms[room_id]['answers'] = {}
    
    # 設置30秒計時器
    rooms[room_id]['question_timer'] = socketio.start_background_task(
        question_timeout, room_id, rooms[room_id]['question_number']
    )
    
    emit('new_question', {
        'question_number': rooms[room_id]['question_number'],
        'p': question['p'],
        'a': question['a'],
        'time_limit': 30  # 30秒限時
    }, room=room_id)

def question_timeout(room_id, question_number):
    """問題計時器，30秒後自動進入下一題"""
    socketio.sleep(30)
    
    if room_id not in rooms:
        return
    
    # 確保我們仍然在同一個問題
    if rooms[room_id]['question_number'] == question_number:
        # 通知所有玩家時間到
        socketio.emit('time_up', {
            'correct_answer': rooms[room_id]['current_question']['answer']
        }, room=room_id)
        
        # 延遲一下再進入下一題
        socketio.sleep(3)
        
        if room_id in rooms:  # 再次確認房間仍然存在
            rooms[room_id]['question_number'] += 1
            next_question(room_id)

@socketio.on('submit_answer')
def handle_answer(data):
    """處理玩家提交的答案"""
    username = session.get('username')
    room_id = session.get('room_id')
    answer = data.get('answer')
    
    if not (username and room_id and room_id in rooms):
        return
    
    # 檢查遊戲是否進行中且該玩家還沒有回答
    if rooms[room_id]['game_started'] and username not in rooms[room_id]['answers']:
        current_question = rooms[room_id]['current_question']
        
        # 檢查是否有任何玩家已經回答正確
        any_correct = any(
            int(ans) == current_question['answer'] 
            for player, ans in rooms[room_id]['answers'].items()
        )
        
        # 如果已經有人回答正確，不再接受新答案
        if any_correct:
            emit('answer_rejected', {
                'message': '已有玩家回答正確'
            })
            return
        
        # 記錄答案
        rooms[room_id]['answers'][username] = answer
        
        # 檢查答案是否正確
        correct = int(answer) == current_question['answer']
        
        # 計算答題時間
        time_taken = time.time() - current_question['time_started']
        
        # 判斷是否為第一個回答正確的玩家
        first_correct = correct and len([u for u, a in rooms[room_id]['answers'].items() 
                                        if int(a) == current_question['answer']]) == 1
        
        if first_correct:
            rooms[room_id]['scores'][username] += 1
            # 如果有人答對，立即通知所有玩家
            emit('someone_answered_correctly', {'username': username}, room=room_id)
        
        # 通知該玩家答題結果
        emit('answer_result', {
            'correct': correct,
            'first_correct': first_correct,
            'correct_answer': current_question['answer'],
            'time_taken': round(time_taken, 2)
        })
        
        # 通知所有玩家有人答題
        emit('player_answered', {
            'username': username,
            'answered_count': len(rooms[room_id]['answers']),
            'total_players': len(rooms[room_id]['players']),
            'correct': correct
        }, room=room_id)
        
        # 如果所有玩家都已答題或有人答對，進入下一題
        if len(rooms[room_id]['answers']) == len(rooms[room_id]['players']) or first_correct:
            # 更新分數
            emit('update_scores', {'scores': rooms[room_id]['scores']}, room=room_id)
            
            # 延遲一下再進入下一題，讓玩家有時間看結果
            rooms[room_id]['question_number'] += 1
            socketio.sleep(3)
            next_question(room_id)

def end_game(room_id):
    """結束遊戲並計算最終結果"""
    if room_id not in rooms:
        return
    
    scores = rooms[room_id]['scores']
    winner = max(scores, key=scores.get) if scores else None
    max_score = scores.get(winner, 0) if winner else 0
    
    # 檢查是否有平局
    tied_players = [player for player, score in scores.items() if score == max_score]
    
    if len(tied_players) > 1:
        result = {
            'tie': True,
            'tied_players': tied_players,
            'scores': scores
        }
    else:
        result = {
            'tie': False,
            'winner': winner,
            'scores': scores
        }
    
    emit('game_over', result, room=room_id)
    
    # 重置房間遊戲狀態，但保留玩家
    rooms[room_id]['game_started'] = False
    rooms[room_id]['ready'] = {}
    rooms[room_id]['current_question'] = None
    rooms[room_id]['question_number'] = 0

@app.route('/game')
def game():
    """遊戲頁面"""
    if 'username' not in session or 'room_id' not in session:
        return redirect(url_for('index'))
    
    room_id = session['room_id']
    if room_id not in rooms:
        return redirect(url_for('index'))
    
    return render_template('game.html')

# 修改 app.py 中的相關函數

@app.route('/get_room_id')
def get_room_id():
    """獲取當前會話中的房間ID"""
    if 'room_id' in session:
        return jsonify({'room_id': session['room_id']})
    return jsonify({'error': '未找到房間ID'})

@socketio.on('submit_answer')
def handle_answer(data):
    """處理玩家提交的答案"""
    username = session.get('username')
    room_id = session.get('room_id')
    answer = data.get('answer')
    
    if not (username and room_id and room_id in rooms):
        return
    
    # 檢查遊戲是否進行中且該玩家還沒有回答
    if rooms[room_id]['game_started'] and username not in rooms[room_id]['answers']:
        current_question = rooms[room_id]['current_question']
        
        # 檢查是否有任何玩家已經回答正確
        any_correct = any(
            int(ans) == current_question['answer'] 
            for player, ans in rooms[room_id]['answers'].items()
        )
        
        # 如果已經有人回答正確，不再接受新答案
        if any_correct:
            emit('answer_rejected', {
                'message': '已有玩家回答正確'
            })
            return
        
        # 記錄答案
        rooms[room_id]['answers'][username] = answer
        
        # 檢查答案是否正確
        correct = int(answer) == current_question['answer']
        
        # 計算答題時間
        time_taken = time.time() - current_question['time_started']
        
        # 判斷是否為第一個回答正確的玩家
        first_correct = correct and len([u for u, a in rooms[room_id]['answers'].items() 
                                        if int(a) == current_question['answer']]) == 1
        
        if first_correct:
            rooms[room_id]['scores'][username] += 1
            # 如果有人答對，立即通知所有玩家
            emit('someone_answered_correctly', {'username': username}, room=room_id)
        
        # 通知該玩家答題結果
        emit('answer_result', {
            'correct': correct,
            'first_correct': first_correct,
            'correct_answer': current_question['answer'],
            'time_taken': round(time_taken, 2)
        })
        
        # 通知所有玩家有人答題
        emit('player_answered', {
            'username': username,
            'answered_count': len(rooms[room_id]['answers']),
            'total_players': len(rooms[room_id]['players']),
            'correct': correct
        }, room=room_id)
        
        # 如果所有玩家都已答題或有人答對，進入下一題
        if len(rooms[room_id]['answers']) == len(rooms[room_id]['players']) or first_correct:
            # 更新分數
            emit('update_scores', {'scores': rooms[room_id]['scores']}, room=room_id)
            
            # 延遲一下再進入下一題，讓玩家有時間看結果
            rooms[room_id]['question_number'] += 1
            socketio.sleep(3)
            next_question(room_id)

if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=8000, debug=True)