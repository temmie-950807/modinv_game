# services/ranking_service.py
from models.database import update_user_rating, find_user

def calculate_rating_changes(score_dict, old_ratings):
    """計算每位玩家的積分變化
    
    Args:
        score_dict: 遊戲中每位玩家的得分字典
        old_ratings: 遊戲前每位玩家的積分字典
        
    Returns:
        dict: 每位玩家的積分變化字典
    """
    players = list(score_dict.keys())
    n = len(players)
    if n < 2:
        return {}
    
    # 檢查是否有平手情況
    scores_values = list(score_dict.values())
    max_score = max(scores_values)
    winners = [p for p, s in score_dict.items() if s == max_score]
    
    # 如果有多個贏家（平手），返回空字典（不更新積分）
    if len(winners) > 1:
        return {player: 0 for player in players}
    
    # K 值
    K = 32
    
    # 計算實際得分
    actual = {}
    for i in players:
        si = score_dict[i]
        total = 0.0
        for j in players:
            if i == j:
                continue
            sj = score_dict[j]
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
        
        # 更新玩家積分
        new_rating = old_ratings[player] + changes[player]
        update_user_rating(player, new_rating)
    
    return changes

def update_ratings(score_dict):
    """更新多個使用者 rating
    
    Args:
        score_dict: dict of username → 得分（比賽中的實際分數）
    """
    players = list(score_dict.keys())
    n = len(players)
    if n < 2:
        # 少於 2 人不更新
        return
    
    # 檢查是否有平手情況
    scores = list(score_dict.values())
    max_score = max(scores)
    winners = [p for p, s in score_dict.items() if s == max_score]
    
    # 如果有多個贏家（平手），則不更新 rating
    if len(winners) > 1:
        return
    
    # 取出每個玩家的資料
    old_ratings = {}
    for username in players:
        user = find_user(username)
        if user:
            old_ratings[username] = user['rating']
    
    # 計算積分變化
    rating_changes = calculate_rating_changes(score_dict, old_ratings)
    
    # rating_changes 已包含更新玩家積分的操作