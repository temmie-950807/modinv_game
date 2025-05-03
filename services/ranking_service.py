# services/ranking_service.py

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