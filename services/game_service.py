# services/game_service.py
import random
import time
from flask_socketio import emit
from utils.math_utils import generate_question
from services.auth_service import find_account
from services.ranking_service import calculate_rating_changes
from models.database import update_ratings

# 遊戲房間數據
rooms = {}
# 積分模式隊列
ranked_queue = []

# 遊戲設定
DIFFICULTY_BOUNDS = {
    'easy': 50,   # a,b < 50
    'medium': 100, # a,b < 100
    'hard': 200   # a,b < 200
}
GAME_MODES = {'first', 'speed', 'practice', 'ranked'}

def create_game_room(username, room_id, difficulty, game_mode, game_time, question_count):
    """創建新的遊戲房間"""
    if not room_id:
        # 創建一個6位數的隨機房間ID
        room_id = ''.join(random.choices('0123456789', k=6))
    
    if room_id in rooms:
        return {'error': '房間已存在，請選擇其他房間ID'}
    
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
    
    return {'room_id': room_id}

def join_game_room(username, room_id):
    """加入現有遊戲房間"""
    if not room_id in rooms:
        return {'error': '找不到此房間'}
    
    if rooms[room_id]["game_started"] == True:
        return {'error': '遊戲已經開始，無法加入'}
    
    # 檢查是否為練習模式房間，練習模式只允許創建者一人
    if rooms[room_id].get('is_practice', False) or rooms[room_id]['game_mode'] == 'practice':
        return {'error': '此為練習模式房間，不允許其他玩家加入'}
    
    if len(rooms[room_id]['players']) >= 10:
        return {'error': '房間已滿'}
    
    rooms[room_id]['players'].append(username)
    rooms[room_id]['scores'][username] = 0
    
    return {'room_id': room_id}

def leave_game_room(username, room_id):
    """離開當前房間"""
    if room_id in rooms and username in rooms[room_id]['players']:
        rooms[room_id]['players'].remove(username)
        
        if username in rooms[room_id]['scores']:
            del rooms[room_id]['scores'][username]
        
        if username in rooms[room_id]['ready']:
            del rooms[room_id]['ready'][username]
        
        # 如果房間空了，刪除房間
        if len(rooms[room_id]['players']) == 0:
            del rooms[room_id]
            return True
        else:
            # 準備廣播數據
            from socket_handlers.game_events import socketio
            
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
            
    return True

def get_room_id(username):
    """獲取用戶所在房間的ID"""
    for room_id, room in rooms.items():
        if username in room['players']:
            return room_id
    return None

def get_room_info(room_id):
    """獲取房間信息"""
    return rooms.get(room_id, None)

def start_game(room_id):
    """開始遊戲"""
    if room_id not in rooms:
        return False
    
    from socket_handlers.game_events import socketio
    
    game_mode = rooms[room_id]['game_mode']
    is_ranked = rooms[room_id].get('is_ranked', False)
    
    # 重置積分和問題計數
    rooms[room_id]['question_number'] = 1
    rooms[room_id]['scores'] = {player: 0 for player in rooms[room_id]['players']}
    rooms[room_id]['answers'] = {}
    
    # 發送開始遊戲倒數
    socketio.emit('game_countdown', {'countdown': 5}, room=room_id)
    
    # 等待5秒後開始第一題
    socketio.sleep(5)
    
    # 檢查房間是否還存在
    if room_id not in rooms:
        return False
    
    # 如果是積分模式，確保使用搶快模式
    if is_ranked and game_mode != 'first':
        rooms[room_id]['game_mode'] = 'first'
        game_mode = 'first'
    
    socketio.emit('game_started', {'game_mode': game_mode}, room=room_id)
    next_question(room_id)
    return True

def next_question(room_id):
    """生成下一個問題"""
    from socket_handlers.game_events import socketio
    
    # 檢查房間是否存在
    if room_id not in rooms:
        return False
    
    # 檢查是否達到最大問題數量
    if rooms[room_id]['question_number'] > rooms[room_id]['question_count']:
        end_game(room_id)
        return False
    
    # 發送下一題倒數提示
    if rooms[room_id]['question_number'] > 1:
        socketio.emit('next_question_countdown', {'countdown': 3}, room=room_id)
        socketio.sleep(3)
    
    # 重置房間狀態
    rooms[room_id]['first_correct_done'] = False
    rooms[room_id]['answers'] = {}
    rooms[room_id]['correct_order'] = []
    
    # 生成新問題
    question = generate_question(rooms[room_id]['difficulty'], DIFFICULTY_BOUNDS)
    rooms[room_id]['current_question'] = question
    
    # 啟動新的問題計時器
    rooms[room_id]['question_timer'] = socketio.start_background_task(
        question_timeout, room_id, rooms[room_id]['question_number']
    )
    
    # 發送新問題到前端
    socketio.emit('new_question', {
        'question_number': rooms[room_id]['question_number'],
        'question_count': rooms[room_id]['question_count'],
        'p': question['p'],
        'a': question['a'],
        'game_mode': rooms[room_id]['game_mode'],
        'game_time': rooms[room_id]['game_time'],
    }, room=room_id)
    
    return True

def question_timeout(room_id, question_number):
    """處理問題計時，當時間到時自動進入下一題"""
    from socket_handlers.game_events import socketio
    
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

def end_game(room_id):
    """結束遊戲並計算最終結果"""
    if room_id not in rooms:
        return
    
    from socket_handlers.game_events import socketio
    
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
    if rooms[room_id]['game_mode'] == 'ranked':
        # 計算並更新積分
        rating_changes = calculate_rating_changes(scores, old_ratings)
        update_ratings(rating_changes)
    
    # 在 game_over 事件中添加積分變化信息
    result['is_ranked'] = rooms[room_id]['game_mode'] == 'ranked'
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

def handle_answer(username, room_id, answer_text):
    """處理玩家答題"""
    if not room_id in rooms:
        return {'error': '房間不存在'}
    
    from socket_handlers.game_events import socketio
    
    room = rooms[room_id]
    q = room['current_question']
    mode = room['game_mode']
    
    # 已經回答過就忽略
    if username in room['answers']:
        return {'error': '已經回答過'}
    
    # 搶快規則：第一個正確的人以後全部拒絕
    if mode == 'first' and room['first_correct_done']:
        return {'error': '已有玩家答對搶走分數'}
    
    # 記錄答案
    answer = int(answer_text)
    room['answers'][username] = answer
    correct = answer == q['answer']
    time_taken = round(time.time() - q['time_started'], 2)
    
    # 通知其他玩家有人作答
    socketio.emit('player_answered', {'username': username}, room=room_id)
    
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
    
    answer_result = {
        'username': username,
        'correct': correct,
        'points': points,
        'time_taken': time_taken,
        'correct_answer': q['answer']
    }
    
    if correct and points > 0:
        socketio.emit('someone_answered_correctly', {
            'username': username,
            'mode': mode,
            'stop_timer': mode == 'first'  # 如果是搶快模式則通知前端停止計時器
        }, room=room_id)
    else:
        socketio.emit('someone_answered_incorrectly', {
            'username': username,
            'mode': mode
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
    
    return answer_result

def join_ranked_queue(username):
    """加入積分模式匹配隊列"""
    # 檢查用戶是否已在隊列中
    if username in ranked_queue:
        return {'status': 'waiting'}
    
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
            return {'status': 'waiting'}
        
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
        
        # 返回匹配成功及房間信息
        return {
            'status': 'matched',
            'room_id': room_id,
            'opponent': player2 if username == player1 else player1,
            'difficulty': difficulty,
            'question_count': question_count
        }
    
    # 如果隊列中只有一個玩家，返回等待狀態
    return {'status': 'waiting'}

def check_match_status(username):
    """檢查玩家的匹配狀態"""
    # 檢查用戶是否已經在某個房間中
    for room_id, room in rooms.items():
        if username in room['players']:
            # 找到對手
            opponent = None
            for player in room['players']:
                if player != username:
                    opponent = player
                    break
            
            # 返回房間信息
            return {
                'status': 'matched',
                'room_id': room_id,
                'opponent': opponent,
                'difficulty': room['difficulty'],
                'question_count': room['question_count']
            }
    
    # 檢查用戶是否在等待隊列中
    if username in ranked_queue:
        return {'status': 'waiting'}
    
    # 用戶既不在房間中也不在隊列中
    return {'status': 'not_in_queue'}

def cancel_ranked_queue(username):
    """取消積分模式匹配"""
    # 從隊列中移除用戶
    if username in ranked_queue:
        ranked_queue.remove(username)
    
    return {'status': 'canceled'}

def reset_ranked_match(username):
    """重置卡住的積分模式匹配"""
    # 檢查用戶是否在某個房間中
    user_room_id = None
    for room_id, room in rooms.items():
        if username in room['players'] and room.get('is_ranked', False):
            user_room_id = room_id
            break
    
    if not user_room_id:
        return {'message': '未找到積分模式匹配'}
    
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
    
    return {'success': True, 'message': '已重置積分模式匹配狀態'}