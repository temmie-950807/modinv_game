# socket_handlers/game_events.py
from flask import session, request
from flask_socketio import emit, join_room, leave_room
from services.auth_service import find_account
from services.game_service import (
    rooms, get_room_info, start_game, 
    handle_answer, cancel_ranked_queue
)

# 全局變數，將在register_socket_events中被設置
socketio = None

def register_socket_events(socket_io):
    """註冊所有Socket.IO事件處理器"""
    global socketio
    socketio = socket_io
    
    # 連接事件
    socketio.on_event('connect', handle_connect)
    socketio.on_event('disconnect', handle_disconnect)
    
    # 遊戲事件
    socketio.on_event('player_ready', handle_player_ready)
    socketio.on_event('player_cancel_ready', handle_player_cancel_ready)
    socketio.on_event('submit_answer', handle_submit_answer)
    socketio.on_event('check_ranked_countdown', handle_check_ranked_countdown)

def handle_connect():
    """處理連接事件"""
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

def handle_disconnect():
    """處理斷開連接事件"""
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

def handle_player_ready():
    """處理玩家準備事件"""
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

def handle_player_cancel_ready():
    """處理玩家取消準備事件"""
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

def handle_submit_answer(data):
    """處理提交答案事件"""
    username = session.get('username')
    room_id = session.get('room_id')
    raw_ans = data.get('answer', '').strip()
    
    # 基本檢查
    if not (username and room_id and room_id in rooms):
        return
    if not raw_ans.isdigit():
        emit('answer_rejected', {'message': '答案必須是整數'})
        return
    
    # 獲取答案結果
    result = handle_answer(username, room_id, raw_ans)
    
    if 'error' in result:
        emit('answer_rejected', {'message': result['error']})
    else:
        emit('answer_result', result, to=request.sid)

def handle_check_ranked_countdown():
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