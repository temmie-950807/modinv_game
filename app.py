import os, time, random, math, sqlite3
from datetime import timedelta
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from functools import wraps

# 引入我們的 SQLite 資料庫函數
from db_utils import init_db, find_account, register_account, verify_account, update_ratings

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "replace‑me‑with‑a‑real‑secret")
socketio = SocketIO(app, cors_allowed_origins="*")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# 確保資料庫初始化
init_db()

# game mode
@app.before_request
def refresh_permanent_session():
    if 'username' in session:
        session.permanent = True

DIFFICULTY_BOUNDS = {
    'easy':    50,  # a,b < 50
    'medium':  100, # a,b < 100
    'hard':    200  # a,b < 200
}
GAME_MODES = {'first', 'speed', 'practice', 'ranked'}  # 添加 'ranked' 積分模式

# 遊戲房間數據
rooms = {}

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapped

@app.route('/register', methods=['GET','POST'])
def register():
    error = ''
    if request.method=='POST':
        u = request.form['username'].strip()
        p = request.form['password']
        if not u or not p:
            error = '帳號密碼不可空'
        elif not register_account(u, p):
            error = '使用者已存在'
        else:
            return redirect(url_for('login'))
    return render_template('register.html', error=error)

@app.route('/login', methods=['GET','POST'])
def login():
    error = ''
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        remember = request.form.get('remember')  # 來自前端的 checkbox
        if verify_account(u, p):
            session['username'] = u
            # 如果使用者勾選「記住我」，把這個 Session 設為永久
            session.permanent = bool(remember)
            return redirect(url_for('index'))
        error = '帳號或密碼錯誤'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

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

def generate_question(difficulty: str):
    """生成一個有關模反元素的問題"""
    bound = DIFFICULTY_BOUNDS[difficulty]
    primes = get_primes(11, bound - 1)
    p = random.choice(primes)
    
    # 選擇 a，確保 a 和 p 互質 (這裡小於 p 的數一定與 p 互質，因為 p 是質數)
    a = random.randint(2, p - 1)
    
    answer = mod_inverse(a, p)
    return {
        'p': p,
        'a': a,
        'answer': answer,
        'time_started': time.time()  # 記錄問題開始時間
    }

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

# 修改 create_room 函數，添加 question_count 參數
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
    
    if not room_id:
        # 創建一個6位數的隨機房間ID
        room_id = ''.join(random.choices('0123456789', k=6))
    
    if room_id in rooms:
        return jsonify({'error': '房間已存在，請選擇其他房間ID'})
    
    session['username'] = username
    session['room_id'] = room_id
    
    # 設置房間屬性，包括是否為練習模式
    is_practice = game_mode == 'practice'
    
    rooms[room_id] = {
        'players': [username],
        'ready': {},
        'scores': {username: 0},
        'current_question': None,
        'question_number': 0,
        'answers': {},
        'game_started': False,
        'question_timer': None,
        'difficulty': difficulty,
        'game_mode': game_mode,
        'game_time': game_time,
        'question_count': question_count,
        'correct_order': [],        # 比速度用
        'first_correct_done': False, # 搶快用
        'is_practice': is_practice   # 標記是否為練習模式
    }
    
    return jsonify({'room_id': room_id})

# 修改 join_existing_room 函數，檢查用戶名長度
@app.route('/join_room', methods=['POST'])
@login_required
def join_existing_room():
    """加入現有遊戲房間"""
    username = session['username']
    room_id = request.form.get('room_id')
    
    if not room_id in rooms:
        return jsonify({'error': '找不到此房間'})
    
    if rooms[room_id]["game_started"] == True:
        return jsonify({'error': '遊戲已經開始，無法加入'})
    
    # 檢查是否為練習模式房間，練習模式只允許創建者一人
    if rooms[room_id].get('is_practice', False) or rooms[room_id]['game_mode'] == 'practice':
        return jsonify({'error': '此為練習模式房間，不允許其他玩家加入'})
    
    if len(rooms[room_id]['players']) >= 10:
        return jsonify({'error': '房間已滿'})
    
    session['username'] = username
    session['room_id'] = room_id
    
    rooms[room_id]['players'].append(username)
    rooms[room_id]['scores'][username] = 0
    
    return jsonify({'room_id': room_id})

@app.route('/leave_room', methods=['POST'])
@login_required
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
                ratings = {}
                for u in rooms[room_id]['players']:
                    acct = find_account(u)
                    ratings[u] = acct['rating'] if acct else 1500

                socketio.emit('room_status', {
                    'players':      rooms[room_id]['players'],
                    'scores':       rooms[room_id]['scores'],
                    'ready':        rooms[room_id]['ready'],
                    'game_started': rooms[room_id]['game_started'],
                    'ratings':      ratings
                }, room=room_id)
        
        # 清除會話
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
            
            # 如果是積分模式，標記該玩家已連接
            if rooms[room_id].get('is_ranked', False) or rooms[room_id]['game_mode'] == 'ranked':
                # 記錄玩家已連接，但還不是準備狀態
                if username not in rooms[room_id]['ready']:
                    rooms[room_id]['ready'][username] = False
                
                # 檢查是否所有玩家都已連接
                if len(rooms[room_id]['ready']) == len(rooms[room_id]['players']):
                    # 觸發積分模式倒數
                    socketio.emit('ranked_all_connected', {
                        'countdown': 5,
                        'players': rooms[room_id]['players']
                    }, room=room_id)
            
            # 更新房間狀態
            ratings = {}
            for u in rooms[room_id]['players']:
                acct = find_account(u)
                ratings[u] = acct['rating'] if acct else 1500

            socketio.emit('room_status', {
                'players':      rooms[room_id]['players'],
                'scores':       rooms[room_id]['scores'],
                'ready':        rooms[room_id]['ready'],
                'game_started': rooms[room_id]['game_started'],
                'ratings':      ratings,
                'game_mode':    rooms[room_id]['game_mode'],
                'is_ranked':    rooms[room_id].get('is_ranked', False),
                'auto_start':   rooms[room_id].get('auto_start', False)
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
                    ratings = {}
                    for u in rooms[room_id]['players']:
                        acct = find_account(u)
                        ratings[u] = acct['rating'] if acct else 1500

                    socketio.emit('room_status', {
                        'players':      rooms[room_id]['players'],
                        'scores':       rooms[room_id]['scores'],
                        'ready':        rooms[room_id]['ready'],
                        'game_started': rooms[room_id]['game_started'],
                        'ratings':      ratings
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
    all_ready = len(rooms[room_id]['ready']) == len(rooms[room_id]['players'])
    
    # 檢查玩家人數是否滿足要求：練習模式允許單人，其他模式需要至少兩人
    game_mode = rooms[room_id]['game_mode']
    min_players = 1 if game_mode == 'practice' else 2
    enough_players = len(rooms[room_id]['players']) >= min_players
    
    if all_ready and enough_players and not rooms[room_id]['game_started']:
        emit('player_ready_status', {
            'username': username,
            'ready_count': len(rooms[room_id]['ready']),
            'total_players': len(rooms[room_id]['players'])
        }, room=room_id)
        rooms[room_id]['game_started'] = True
        start_game(room_id)
    else:
        # 如果準備好了但人數不足，發送特殊消息
        if all_ready and not enough_players and game_mode != 'practice':
            emit('not_enough_players', {
                'min_players': min_players,
                'current_players': len(rooms[room_id]['players']),
                'game_mode': rooms[room_id]['game_mode']
            }, room=room_id)
        else:
            emit('player_ready_status', {
                'username': username,
                'ready_count': len(rooms[room_id]['ready']),
                'total_players': len(rooms[room_id]['players'])
            }, room=room_id)

# 修改 start_game 函數
def start_game(room_id):
    """開始遊戲"""
    if room_id not in rooms:
        return
    
    game_mode = rooms[room_id]['game_mode']
    is_ranked = rooms[room_id].get('is_ranked', False)
    
    # 重置積分和問題計數
    rooms[room_id]['question_number'] = 1
    rooms[room_id]['scores'] = {player: 0 for player in rooms[room_id]['players']}
    rooms[room_id]['answers'] = {}
    
    # 發送開始遊戲倒數
    emit('game_countdown', {'countdown': 5}, room=room_id)
    
    # 等待5秒後開始第一題
    socketio.sleep(5)
    
    # 檢查房間是否還存在
    if room_id not in rooms:
        return
    
    # 如果是積分模式，確保使用搶快模式
    if is_ranked and game_mode != 'first':
        rooms[room_id]['game_mode'] = 'first'
        game_mode = 'first'
    
    emit('game_started', {'game_mode': game_mode}, room=room_id)
    next_question(room_id)

# 修改 next_question 函數，檢查題目數量
def next_question(room_id):
    """生成下一個問題"""
    print(f"進入 next_question 函數，房間 {room_id}，問題編號 {rooms[room_id]['question_number'] if room_id in rooms else 'N/A'}")
    
    # 檢查房間是否存在
    if room_id not in rooms:
        print(f"房間 {room_id} 不存在，退出 next_question")
        return
    
    # 檢查是否達到最大問題數量
    if rooms[room_id]['question_number'] > rooms[room_id]['question_count']:
        print(f"達到最大問題數量，結束遊戲，房間 {room_id}")
        end_game(room_id)
        return
    
    # 發送下一題倒數提示
    if rooms[room_id]['question_number'] > 1:
        print(f"發送下一題倒數，房間 {room_id}")
        socketio.emit('next_question_countdown', {'countdown': 3}, room=room_id)
        socketio.sleep(3)
    
    # 重置房間狀態
    print(f"重置房間狀態，准備新問題，房間 {room_id}")
    rooms[room_id]['first_correct_done'] = False
    rooms[room_id]['answers'] = {}
    rooms[room_id]['correct_order'] = []
    
    # 生成新問題
    question = generate_question(rooms[room_id]['difficulty'])
    rooms[room_id]['current_question'] = question
    
    # 啟動新的問題計時器
    rooms[room_id]['question_timer'] = socketio.start_background_task(
        question_timeout, room_id, rooms[room_id]['question_number']
    )
    
    # 發送新問題到前端
    print(f"發送新問題到前端，房間 {room_id}，問題編號 {rooms[room_id]['question_number']}")
    socketio.emit('new_question', {
        'question_number': rooms[room_id]['question_number'],
        'question_count': rooms[room_id]['question_count'],
        'p': question['p'],
        'a': question['a'],
        'game_mode': rooms[room_id]['game_mode'],
        'game_time': rooms[room_id]['game_time'],
    }, room=room_id)

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
    
    # 獲取賽前積分
    old_ratings = {}
    for u in rooms[room_id]['players']:
        user = find_account(u)
        old_ratings[u] = user['rating'] if user else 1500
    
    # 只有在積分模式下才更新積分
    rating_changes = {}
    if rooms[room_id].get('is_ranked', False):
        # 計算積分變化
        rating_changes = calculate_rating_changes(scores, old_ratings)
        
        # 更新每個玩家的積分
        # 直接傳入比賽分數，讓 update_ratings 函數自己計算積分變化
        update_ratings(scores)
    
    # 在 game_over 事件中添加積分變化信息
    result['is_ranked'] = rooms[room_id].get('is_ranked', False)
    result['old_ratings'] = old_ratings
    result['rating_changes'] = rating_changes

    # 廣播 game_over
    socketio.emit('game_over', result, room=room_id)

    # 準備最新的 ratings dict
    ratings = {}
    for u in rooms[room_id]['players']:
        user = find_account(u)
        ratings[u] = user['rating'] if user else 1500

    # 廣播最新房間狀態
    socketio.emit('room_status', {
        'players':      rooms[room_id]['players'],
        'scores':       rooms[room_id]['scores'],
        'ready':        rooms[room_id]['ready'],
        'game_started': rooms[room_id]['game_started'],
        'ratings':      ratings,
        'room_id':      room_id,
        'game_mode':    rooms[room_id]['game_mode']
    }, room=room_id)

    # 重置房間遊戲狀態
    rooms[room_id]['game_started']     = False
    rooms[room_id]['ready']            = {}
    rooms[room_id]['current_question'] = None
    rooms[room_id]['question_number']  = 0

def question_timeout(room_id, question_number):
    """處理問題計時，當時間到時自動進入下一題"""
    # 等待指定的遊戲時間
    socketio.sleep(int(rooms[room_id]['game_time']))
    
    # 檢查房間是否還存在
    if room_id not in rooms:
        return
    
    # 檢查是否仍在同一個問題（避免重複處理）
    if rooms[room_id]['question_number'] == question_number:
        # 通知所有玩家時間到
        socketio.emit('time_up', {
            'correct_answer': rooms[room_id]['current_question']['answer']
        }, room=room_id)
        
        # 在前端顯示答案後短暫延遲
        socketio.sleep(3)
        
        # 再次檢查房間是否存在，以防在延遲期間房間被刪除
        if room_id in rooms and rooms[room_id]['question_number'] == question_number:
            # 更新問題編號並進入下一題
            rooms[room_id]['question_number'] += 1
            
            # 使用獨立的任務啟動下一題，避免阻塞當前線程
            socketio.start_background_task(
                next_question, room_id
            )

@socketio.on('submit_answer')
def handle_answer(data):
    username = session.get('username')
    room_id  = session.get('room_id')
    raw_ans  = data.get('answer', '').strip()

    # -------- 基本檢查 --------
    if not (username and room_id and room_id in rooms):
        return
    if not raw_ans.isdigit():
        emit('answer_rejected', {'message': '答案必須是整數'})
        return
    answer = int(raw_ans)

    room = rooms[room_id]
    q    = room['current_question']
    mode = room['game_mode']

    # 已經回答過就忽略
    if username in room['answers']:
        return

    # -------- 搶快規則：第一個正確的人以後全部拒絕 --------
    if mode == 'first' and room['first_correct_done']:
        emit('answer_rejected', {'message': '已有玩家答對搶走分數'}, to=request.sid)
        return

    # -------- 記錄答案 --------
    room['answers'][username] = answer
    correct = answer == q['answer']
    time_taken = round(time.time() - q['time_started'], 2)
    emit('player_answered', {'username': username}, room=room_id, include_self=False)

    points = 0
    if correct:
        if mode == 'first':
            if not room['first_correct_done']:
                points = 1
                room['scores'][username] += points
                room['first_correct_done'] = True
        else:  # speed
            rank = len(room['correct_order'])
            points = max(1, 3 - rank)      # 3/2/1/1…
            room['correct_order'].append(username)
            room['scores'][username] += points
    socketio.emit('update_scores', {'scores': room['scores']}, room=room_id)

    emit('answer_result', {
        'username': username,
        'correct': correct,
        'points': points,
        'time_taken': time_taken,
        'correct_answer': q['answer']
    }, to=request.sid)

    if correct and points > 0:
        emit('someone_answered_correctly', {
            'username': username,
            'mode': mode,
            'stop_timer': mode == 'first'  # 如果是搶快模式則通知前端停止計時器
        }, room=room_id)
    else:
        emit('someone_answered_incorrectly', {
            'username': username,
            'mode': mode                  # ★ 告知前端目前模式
        }, room=room_id)

    # 下一題條件
    everyone_done = len(room['answers']) == len(room['players'])
    needs_next = False

    if mode == 'first' and room['first_correct_done']:
        needs_next = True  # 搶快模式且有人答對
    elif everyone_done:
        needs_next = True  # 所有人都已作答
        
    if needs_next:
        current_question = room['question_number']  # 記錄當前問題編號
        room['question_number'] += 1  # 增加問題編號
        
        # 使用短暫延遲讓玩家看到結果
        socketio.sleep(3)
        
        # 確保仍在相同問題（沒有由其他地方觸發下一題）
        if room_id in rooms and room['question_number'] == current_question + 1:
            next_question(room_id)

@app.route('/game')
def game():
    """遊戲頁面"""
    if 'username' not in session or 'room_id' not in session:
        return redirect(url_for('index'))
    
    room_id = session['room_id']
    if room_id not in rooms:
        return redirect(url_for('index'))
    
    return render_template('game.html')

@app.route('/get_room_id')
def get_room_id():
    """獲取當前會話中的房間ID和基本信息"""
    if 'room_id' in session and session['room_id'] in rooms:
        room_id = session['room_id']
        return jsonify({
            'room_id': room_id,
            'game_mode': rooms[room_id]['game_mode']
        })
    return jsonify({'error': '未找到房間ID'})

@app.route('/get_room_info')
def get_room_info():
    """獲取當前會話中的房間詳細信息"""
    if 'room_id' in session and session['room_id'] in rooms:
        room_id = session['room_id']
        room = rooms[room_id]
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

# Add this route to app.py
@app.route('/leaderboard')
def leaderboard():
    """Show the leaderboard of all players"""
    return render_template('leaderboard.html')

# Add this API endpoint to get leaderboard data
@app.route('/api/leaderboard')
def get_leaderboard():
    """Get the leaderboard data as JSON"""
    conn = sqlite3.connect('modular_inverse_game.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT username, rating 
        FROM users 
        ORDER BY rating DESC
    """)
    
    players = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({'players': players})

@socketio.on('player_cancel_ready')
def handle_player_cancel_ready():
    username = session.get('username')
    room_id = session.get('room_id')
    
    if not (username and room_id and room_id in rooms):
        return
    
    # 如果遊戲已經開始，則不允許取消準備
    if rooms[room_id]['game_started']:
        emit('cancel_ready_response', {
            'success': False,
            'message': '遊戲已經開始，無法取消準備'
        }, to=request.sid)
        return
    
    # 如果玩家之前已準備，則移除準備狀態
    if username in rooms[room_id]['ready']:
        del rooms[room_id]['ready'][username]
        
        # 通知所有玩家此玩家取消了準備
        emit('player_ready_status', {
            'username': username,
            'ready_count': len(rooms[room_id]['ready']),
            'total_players': len(rooms[room_id]['players']),
            'canceled': True  # 添加一個標記表示這是取消準備
        }, room=room_id)
        
        emit('cancel_ready_response', {
            'success': True
        }, to=request.sid)
    else:
        # 如果玩家之前沒有準備，則返回錯誤
        emit('cancel_ready_response', {
            'success': False,
            'message': '您尚未準備，無法取消準備'
        }, to=request.sid)

# 創建用於存儲積分模式隊列的字典
ranked_queue = []  # 僅使用一個簡單的列表儲存等待匹配的玩家

# 添加加入積分模式隊列的路由
@app.route('/join_ranked_queue', methods=['POST'])
@login_required
def join_ranked_queue():
    """加入積分模式匹配隊列"""
    username = session.get('username')
    
    if not username:
        return jsonify({'error': '用戶未登入'})
    
    # 檢查用戶是否已在隊列中
    if username in ranked_queue:
        return jsonify({'status': 'waiting'})
    
    # 添加用戶到隊列
    ranked_queue.append(username)
    
    # 如果隊列中至少有兩名玩家，進行匹配
    if len(ranked_queue) >= 2:
        # 獲取前兩名玩家
        player1 = ranked_queue.pop(0)
        player2 = ranked_queue.pop(0)
        
        # 注意：為確保穩定性，這裡再次檢查玩家是否存在
        if player1 != username and player2 != username:
            # 這種情況不應該發生，但為了防止錯誤，將當前玩家重新加入隊列
            ranked_queue.append(username)
            return jsonify({'status': 'waiting'})
        
        # 獲取玩家積分
        player1_data = find_account(player1)
        player2_data = find_account(player2)
        player1_rating = player1_data['rating'] if player1_data else 1500
        player2_rating = player2_data['rating'] if player2_data else 1500
        
        # 根據較低積分的玩家決定難度
        lower_rating = min(player1_rating, player2_rating)
        
        if lower_rating < 1400:  # 新手
            difficulty = 'easy'
            question_count = 3
        elif lower_rating < 1600:  # 專家
            difficulty = 'easy'
            question_count = 3
        elif lower_rating < 1900:  # 精通
            difficulty = 'medium'
            question_count = 7
        else:  # 大師
            difficulty = 'hard'
            question_count = 15
        
        # 創建房間
        room_id = ''.join(random.choices('0123456789', k=6))
        while room_id in rooms:
            room_id = ''.join(random.choices('0123456789', k=6))
        
        # 設置房間屬性
        rooms[room_id] = {
            'players': [player1, player2],
            'ready': {},
            'scores': {player1: 0, player2: 0},
            'current_question': None,
            'question_number': 0,
            'answers': {},
            'game_started': False,
            'question_timer': None,
            'difficulty': difficulty,
            'game_mode': 'first',  # 確保是搶快模式，而不是 'ranked'
            'game_time': '30',  # 固定為30秒
            'question_count': question_count,
            'correct_order': [],
            'first_correct_done': False,
            'is_ranked': True,  # 標記為積分模式
            'auto_start': True,  # 標記為自動開始
            'match_time': time.time()  # 記錄匹配時間
        }
        
        # 設置當前用戶的會話
        session['room_id'] = room_id
        
        # 返回匹配成功及房間信息
        return jsonify({
            'status': 'matched',
            'room_id': room_id,
            'opponent': player2 if username == player1 else player1,
            'difficulty': difficulty,
            'question_count': question_count
        })
    
    # 如果隊列中只有一個玩家，返回等待狀態
    return jsonify({'status': 'waiting'})

@app.route('/check_match_status', methods=['POST'])
@login_required
def check_match_status():
    """檢查玩家的匹配狀態"""
    username = session.get('username')
    
    if not username:
        return jsonify({'error': '用戶未登入'})
    
    # 檢查用戶是否已經在某個房間中
    for room_id, room in rooms.items():
        if username in room['players']:
            # 找到對手
            opponent = None
            for player in room['players']:
                if player != username:
                    opponent = player
                    break
            
            # 設置會話
            session['room_id'] = room_id
            
            # 返回房間信息
            return jsonify({
                'status': 'matched',
                'room_id': room_id,
                'opponent': opponent,
                'difficulty': room['difficulty'],
                'question_count': room['question_count']
            })
    
    # 檢查用戶是否在等待隊列中
    if username in ranked_queue:
        return jsonify({'status': 'waiting'})
    
    # 用戶既不在房間中也不在隊列中
    return jsonify({'status': 'not_in_queue'})

@app.route('/check_ranked_match', methods=['POST'])
@login_required
def check_ranked_match():
    """檢查是否已匹配到對戰"""
    username = session['username']
    
    # 檢查是否有已分配的房間
    if f"{username}_room" in ranked_queue:
        room_id = ranked_queue[f"{username}_room"]
        
        # 獲取房間信息
        room = rooms.get(room_id)
        if not room:
            # 房間不存在，清理
            del ranked_queue[f"{username}_room"]
            return jsonify({'status': 'not_matched'})
        
        # 獲取對手信息
        opponent = None
        for player in room['players']:
            if player != username:
                opponent = player
                break
        
        # 設置會話
        session['username'] = username
        session['room_id'] = room_id
        
        # 清理臨時存儲
        del ranked_queue[f"{username}_room"]
        
        return jsonify({
            'status': 'matched',
            'room_id': room_id,
            'opponent': opponent,
            'difficulty': room['difficulty'],
            'question_count': room['question_count'],
            'auto_redirect': True
        })
    
    # 查看是否在等待隊列中
    if username in ranked_queue['players']:
        return jsonify({'status': 'waiting'})
    
    return jsonify({'status': 'not_matched'})

@socketio.on('check_ranked_countdown')
def check_ranked_countdown():
    """檢查積分模式倒數狀態"""
    username = session.get('username')
    room_id = session.get('room_id')
    
    if not (username and room_id and room_id in rooms):
        return
    
    room = rooms[room_id]
    if not room.get('is_ranked', False):
        return
    
    # 計算自匹配以來經過的時間
    match_time = room.get('match_time', time.time())
    elapsed = time.time() - match_time
    countdown = max(0, 5 - int(elapsed))  # 5秒倒數
    
    # 發送倒數信息
    emit('ranked_countdown_update', {
        'countdown': countdown,
        'total_players': len(room['players']),
        'connected_players': len(room['ready'])
    }, room=room_id)
    
    # 如果倒數結束，且還沒開始遊戲，則自動標記所有玩家為準備就緒
    if countdown <= 0 and not room['game_started'] and len(room['players']) >= 2:
        # 確保所有玩家都準備就緒
        for player in room['players']:
            if player not in room['ready']:
                room['ready'][player] = True
        
        # 啟動遊戲
        room['game_started'] = True
        socketio.start_background_task(start_game, room_id)

# 添加確認積分模式匹配的路由
@app.route('/confirm_ranked_match', methods=['POST'])
@login_required
def confirm_ranked_match():
    """確認積分模式匹配並進入房間"""
    username = session['username']
    
    # 檢查玩家是否已匹配
    if username not in ranked_queue['matching']:
        return jsonify({'error': '未找到匹配記錄'})
    
    # 獲取房間ID
    room_id = ranked_queue['matching'][username]
    
    # 將玩家從匹配列表中移除
    del ranked_queue['matching'][username]
    
    # 設置會話
    session['username'] = username
    session['room_id'] = room_id
    
    return jsonify({'room_id': room_id})

# 添加取消積分模式匹配的路由
@app.route('/cancel_ranked_queue', methods=['POST'])
@login_required
def cancel_ranked_queue():
    """取消積分模式匹配"""
    username = session.get('username')
    
    if not username:
        return jsonify({'error': '用戶未登入'})
    
    # 從隊列中移除用戶
    if username in ranked_queue:
        ranked_queue.remove(username)
    
    return jsonify({'status': 'canceled'})

# 計算積分變化的函數
def calculate_rating_changes(scores, old_ratings):
    """計算每位玩家的積分變化"""
    players = list(scores.keys())
    n = len(players)
    if n < 2:
        return {}
    
    # 檢查是否有平手情況
    scores_values = list(scores.values())
    max_score = max(scores_values)
    winners = [p for p, s in scores.items() if s == max_score]
    
    # 如果有多個贏家（平手），返回空字典（不更新積分）
    if len(winners) > 1:
        return {player: 0 for player in players}
    
    # K 值
    K = 32
    
    # 計算實際得分
    actual = {}
    for i in players:
        si = scores[i]
        total = 0.0
        for j in players:
            if i == j:
                continue
            sj = scores[j]
            if si > sj:
                total += 1
            elif si == sj:
                total += 0.5
        actual[i] = total
    
    # 計算期望得分
    expected = {}
    for i in players:
        Ri = old_ratings[i]
        esum = 0.0
        for j in players:
            if i == j:
                continue
            Rj = old_ratings[j]
            esum += 1 / (1 + 10 ** ((Rj - Ri) / 400))
        expected[i] = esum
    
    # 計算積分變化
    changes = {}
    for player in players:
        S_norm = actual[player] / (n - 1)
        E_norm = expected[player] / (n - 1)
        delta = K * (S_norm - E_norm)
        changes[player] = round(delta)
    
    return changes

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)

# 添加到 app.py
@app.route('/reset_ranked_match', methods=['POST'])
@login_required
def reset_ranked_match():
    """重置卡住的積分模式匹配"""
    username = session.get('username')
    
    if not username:
        return jsonify({'error': '用戶未登入'})
    
    # 檢查用戶是否在某個房間中
    user_room_id = None
    for room_id, room in rooms.items():
        if username in room['players'] and room.get('is_ranked', False):
            user_room_id = room_id
            break
    
    if not user_room_id:
        return jsonify({'message': '未找到積分模式匹配'})
    
    # 清除用戶在該房間的記錄
    rooms[user_room_id]['players'].remove(username)
    if username in rooms[user_room_id]['scores']:
        del rooms[user_room_id]['scores'][username]
    if username in rooms[user_room_id]['ready']:
        del rooms[user_room_id]['ready'][username]
    
    # 如果房間空了，刪除房間
    if len(rooms[user_room_id]['players']) == 0:
        del rooms[user_room_id]
    
    # 同時從積分隊列中移除
    if username in ranked_queue:
        ranked_queue.remove(username)
    
    session.pop('room_id', None)
    
    return jsonify({'success': True, 'message': '已重置積分模式匹配狀態'})