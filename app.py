# app.py
import os, json, time, random, math, secrets
from datetime import timedelta
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "replace‑me‑with‑a‑real‑secret")
socketio = SocketIO(app, cors_allowed_origins="*")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# game mode

@app.before_request
def refresh_permanent_session():
    if 'username' in session:
        session.permanent = True

ACCOUNTS_FILE = os.path.join(os.path.dirname(__file__), 'accounts.json')

DIFFICULTY_BOUNDS = {
    'easy':    50,          # a,b < 50
    'medium':  1000,        # a,b < 1 000
    'hard':    48763    # a,b < 1 000 000 000
}
GAME_MODES = {'first', 'speed'}          # first = 搶快；speed = 比速度

# 遊戲房間數據
rooms = {}

def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE,'w',encoding='utf-8') as f:
            json.dump([], f)
    with open(ACCOUNTS_FILE,'r',encoding='utf-8') as f:
        return json.load(f)

def save_accounts(accs):
    with open(ACCOUNTS_FILE,'w',encoding='utf-8') as f:
        json.dump(accs, f, ensure_ascii=False, indent=2)

def find_account(username):
    return next((u for u in load_accounts() if u['username']==username), None)

def register_account(username, password):
    if find_account(username):
        return False
    accs = load_accounts()
    accs.append({
        'username': username,
        'pw_hash': generate_password_hash(password),
        'rating': 1500
    })
    save_accounts(accs)
    return True
def verify_account(username, password):
    u = find_account(username)
    return u and check_password_hash(u['pw_hash'], password)

def update_ratings(score_dict):
    """
    score_dict: dict of username → 得分（比賽中的實際分數）
    支援多人比賽，採用正規化 Elo：
      S_i_norm = Σ_{j≠i} s_ij  ／ (n-1)
      E_i_norm = Σ_{j≠i} 1/(1+10^((R_j-R_i)/400)) ／ (n-1)
      R_i ← R_i + K * (S_i_norm - E_i_norm)
    其中 s_ij = 1 if player i 得分 > player j 得分,
                  0.5 if 相同,
                  0 otherwise.
    """
    accs = load_accounts()
    # 取出在 accounts.json 裡的帳號 dict，方便原地修改
    user_map = {u['username']: u for u in accs}

    players = list(score_dict.keys())
    n = len(players)
    if n < 2:
        # 少於 2 人不更新
        return

    # K 值 — 和雙人一樣
    K = 32

    # 1) 準備每人的舊 R
    R = {u: user_map[u]['rating'] for u in players}

    # 2) 計算每人 「實際對戰得分總和」 Σ s_ij
    actual = {}
    for i in players:
        si = score_dict[i]
        total = 0.0
        for j in players:
            if i == j: continue
            sj = score_dict[j]
            if   si >  sj: total += 1
            elif si == sj: total += 0.5
        actual[i] = total

    # 3) 計算每人 「期望得分總和」 Σ E_ij
    expected = {}
    for i in players:
        Ri = R[i]
        esum = 0.0
        for j in players:
            if i == j: continue
            Rj = R[j]
            esum += 1 / (1 + 10 ** ((Rj - Ri) / 400))
        expected[i] = esum

    # 4) 更新：先正規化，再按 Elo 公式改變 rating
    for u in players:
        S_norm = actual[u]   / (n - 1)
        E_norm = expected[u] / (n - 1)
        delta  = K * (S_norm - E_norm)
        new_R  = round(R[u] + delta)
        user_map[u]['rating'] = new_R

    # 5) 寫回檔案
    save_accounts(accs)


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
    return render_template('index.html',
                           username=username,
                           rating=rating)
    # 清除任何現有的會話數據

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
    question_count = int(request.form.get('question_count', '7'))  # 預設為7題
    
    # 檢查用戶名長度
    if len(username) > 10:
        return jsonify({'error': '用戶名最多10個字符'})
    
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
        'question_timer': None,
        'difficulty': difficulty,
        'game_mode': game_mode,
        'game_time': game_time,
        'question_count': question_count,  # 新增問題數量設定
        'correct_order': [],        # 比速度用
        'first_correct_done': False # 搶快用
    }
    
    return jsonify({'room_id': room_id})

# 修改 join_existing_room 函數，檢查用戶名長度
@app.route('/join_room', methods=['POST'])
@login_required
def join_existing_room():
    """加入現有遊戲房間"""
    username = session['username']
    room_id = request.form.get('room_id')
    
    # 檢查用戶名長度
    if len(username) > 10:
        return jsonify({'error': '用戶名最多10個字符'})
    
    if not room_id in rooms:
        return jsonify({'error': '找不到此房間'})
    
    if rooms[room_id]["game_started"] == True:
        return jsonify({'error': '遊戲已經開始，無法加入'})
    
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
                'ratings':      ratings
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
    all_ready = len(rooms[room_id]['ready']) == len(rooms[room_id]['players']) and len(rooms[room_id]['players'])
    
    if all_ready and not rooms[room_id]['game_started']:
        emit('player_ready_status', {
            'username': username,
            'ready_count': len(rooms[room_id]['ready']),
            'total_players': len(rooms[room_id]['players'])
        }, room=room_id)
        rooms[room_id]['game_started'] = True
        start_game(room_id)
    else:
        emit('player_ready_status', {
            'username': username,
            'ready_count': len(rooms[room_id]['ready']),
            'total_players': len(rooms[room_id]['players'])
        }, room=room_id)

# 修改 start_game 函數，加入倒數計時功能
def start_game(room_id):
    """開始遊戲"""
    if room_id not in rooms:
        return
    
    rooms[room_id]['question_number'] = 1
    rooms[room_id]['scores'] = {player: 0 for player in rooms[room_id]['players']}
    rooms[room_id]['answers'] = {}
    
    # 發送開始遊戲倒數
    emit('game_countdown', {'countdown': 5}, room=room_id)
    
    # 等待5秒後開始第一題
    socketio.sleep(5)
    
    emit('game_started', room=room_id)
    next_question(room_id)

# 修改 next_question 函數，檢查題目數量
def next_question(room_id):
    """生成下一個問題"""
    if room_id not in rooms:
        return
    
    if rooms[room_id]['question_number'] > rooms[room_id]['question_count']:
        end_game(room_id)
        return
    
    # 發送下一題倒數
    if rooms[room_id]['question_number'] > 1:
        emit('next_question_countdown', {'countdown': 3}, room=room_id)
        socketio.sleep(3)
    
    rooms[room_id]['timer_abort'] = False
    rooms[room_id]['first_correct_done'] = False # ★ 每題重置
    question = generate_question(rooms[room_id]['difficulty'])
    rooms[room_id]['current_question'] = question
    rooms[room_id]['answers'] = {}
    rooms[room_id]['correct_order'] = []     # 比速度用
    
    rooms[room_id]['timer_abort'] = False
    rooms[room_id]['question_timer'] = socketio.start_background_task(
        question_timeout, room_id, rooms[room_id]['question_number']
    )
    
    emit('new_question', {
        'question_number': rooms[room_id]['question_number'],
        'question_count': rooms[room_id]['question_count'],  # 添加總題數
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
    
    update_ratings(scores)  # 定義見上 :contentReference[oaicite:0]{index=0}:contentReference[oaicite:1]{index=1}

    # 3. 廣播 game_over
    socketio.emit('game_over', result, room=room_id)

    # 4. 準備最新的 ratings dict
    ratings = {u: find_account(u)['rating'] for u in rooms[room_id]['players']}

    # 5. 廣播最新房間狀態（包含更新後 R 值）
    socketio.emit('room_status', {
        'players':      rooms[room_id]['players'],
        'scores':       rooms[room_id]['scores'],
        'ready':        rooms[room_id]['ready'],
        'game_started': rooms[room_id]['game_started'],
        'ratings':      ratings,
        'room_id':      room_id
    }, room=room_id)

    # 6. 重置房間遊戲狀態（保留玩家列表，但清空準備/問題狀態）
    rooms[room_id]['game_started']     = False
    rooms[room_id]['ready']            = {}
    rooms[room_id]['current_question'] = None
    rooms[room_id]['question_number']  = 0

def question_timeout(room_id, question_number):
    socketio.sleep(rooms[room_id]['game_time'])
    
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
            'mode': mode                  # ★ 告知前端目前模式
        }, room=room_id)
    else:
        emit('someone_answered_incorrectly', {
            'username': username,
            'mode': mode                  # ★ 告知前端目前模式
        }, room=room_id)

    # 下一題條件
    everyone_done = len(room['answers']) == len(room['players'])
    if (
        (mode == 'first' and room['first_correct_done'])  # 搶快：有人搶答成功
        or everyone_done                                  # 速度：都答完
    ):
        room['question_number'] += 1
        socketio.sleep(3)
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

# 修改 app.py 中的相關函數

@app.route('/get_room_id')
def get_room_id():
    """獲取當前會話中的房間ID"""
    if 'room_id' in session:
        return jsonify({'room_id': session['room_id']})
    return jsonify({'error': '未找到房間ID'})


if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=8000, debug=True)