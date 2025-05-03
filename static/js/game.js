let gameMode = 'first';
const socket = io();
let myUsername = '';
let isAnswered = false;
let countdownInterval = null;
let timeLeft = 100;
let gameInProgress = false;
let correctAnswerUsername = null;
let redirectTimer = null;
let currentPValue = 0;  // 用於存儲當前題目的模數 p

// 定義一個函數來根據 rating 設定對應的 class
function getRatingClass(rating) {
    if (rating >= 1900) return 'candidate_master';
    if (rating >= 1600) return 'expert';
    if (rating >= 1400) return 'specialist';
    return '';
}

// 當連接到服務器時
// 添加到 socket.on('connect') 事件處理中
socket.on('connect', function() {
    console.log('已連接到服務器');
    fetchRoomInfo();
    
    // 檢查是否為積分模式，如果是則開始檢查倒數
    fetch('/get_room_info')
        .then(response => response.json())
        .then(data => {
            if (data.error) return;
            
            if (data.is_ranked || data.game_mode === 'ranked') {
                // 啟動積分模式倒數檢查
                rankedCountdownInterval = setInterval(function() {
                    socket.emit('check_ranked_countdown');
                }, 1000);
            }
        })
        .catch(error => {
            console.error('獲取房間信息出錯:', error);
        });
});

// 添加倒數更新事件處理
socket.on('ranked_countdown_update', function(data) {
    const countdown = data.countdown;
    const waitingMessage = document.querySelector('.waiting-message');
    
    if (countdown > 0) {
        waitingMessage.innerHTML = `積分模式：遊戲將在 ${countdown} 秒後開始（${data.connected_players}/${data.total_players} 人已連接）`;
    } else {
        waitingMessage.innerHTML = '積分模式：遊戲即將開始...';
        
        // 清除倒數計時器
        if (rankedCountdownInterval) {
            clearInterval(rankedCountdownInterval);
        }
    }
});

// 在全局變數區域添加
let rankedCountdownInterval = null;

// 在 window.onbeforeunload 中清理
window.addEventListener('beforeunload', function() {
    // 清除計時器
    if (rankedCountdownInterval) {
        clearInterval(rankedCountdownInterval);
    }
    
    // 現有的離開房間代碼
    fetch('/leave_room', { method: 'POST' });
});

function fetchRoomInfo() {
    fetch('/get_room_id')
        .then(response => response.json())
        .then(data => {
            if (data.room_id) {
                document.getElementById('room-id').textContent = data.room_id;
                
                // 獲取Session中的用戶名
                myUsername = localStorage.getItem('username') || '';
            }
        })
        .catch(error => {
            console.error('獲取房間信息出錯:', error);
        });
}

// 用戶加入
socket.on('user_joined', function(data) {
    console.log('用戶加入:', data.username);
});

// 房間狀態更新
socket.on('room_status', function(data) {
    console.log('房間狀態:', data);
    updatePlayerList(data.players, data.scores, data.ready || {}, data.ratings, data.game_started);
});

// 玩家準備狀態
socket.on('player_ready_status', function(data) {
    console.log('準備狀態:', data);
    document.querySelector('.waiting-message').textContent = 
        `等待玩家準備... (${data.ready_count}/${data.total_players})`;
        
    // 更新玩家準備狀態 - 注意：現在需要找到正確的玩家卡片
    const playerCards = document.querySelectorAll('.player-card');
    playerCards.forEach(card => {
        // 獲取玩家卡片中的玩家名稱，方法改變
        const playerNameElement = card.querySelector('.player-name');
        if (playerNameElement) {
            const playerName = playerNameElement.textContent.replace(' (你)', '');
            if (playerName === data.username) {
                card.classList.add('ready');
            }
        }
    });
});

// 遊戲開始
socket.on('game_started', function() {
    console.log('遊戲開始');
    gameInProgress = true;
    document.getElementById('waiting-screen').style.display = 'none';
    document.getElementById('game-screen').style.display = 'block';
    document.querySelectorAll('.player-card').forEach(card => {
        card.classList.remove('answered-correctly',
                             'answered-wrong',
                             'answered-starbrust',
                             'ready');
        card.classList.add('answered-starbrust');
    });
});

// 新問題
socket.on('new_question', function(data) {
    console.log('新問題:', data);
    isAnswered = false;
    timeLeft = data.game_time;
    gameMode = data.game_mode;
    correctAnswerUsername = null;

    // 自動聚焦到答題框 - 新增這一行
    document.getElementById('answer-input').focus();
    
    // 將當前的 p 值保存到全局變量，用於答題驗證 - 新增這一行
    currentPValue = data.p;
    
    // 重置UI
    document.getElementById('opponent-answered').style.display = 'none';
    document.getElementById('result-container').style.display = 'none';
    document.getElementById('time-up-message').style.display = 'none';
    
    // 啟動新計時器
    clearInterval(countdownInterval);
    updateTimer();
    countdownInterval = setInterval(updateTimer, 1000);
    
    document.getElementById('question-progress').textContent = `問題 ${data.question_number}/${data.question_count || 7}`;
    document.getElementById('question-text').innerHTML = `
        求 ${data.a} 在模 ${data.p} 下的模反元素。<br>
        <small>(即求 x，使得 ${data.a} · x ≡ 1 (mod ${data.p}))</small>
    `;
    
    document.getElementById('answer-input').value = '';
    document.getElementById('answer-input').disabled = false;
    document.getElementById('submit-button').disabled = false;
    document.getElementById('question-container').style.display = 'block';
    document.getElementById('result-container').style.display = 'none';
    document.getElementById('time-up-message').style.display = 'none';
    
    // 重置玩家卡片的答對標記
    document.querySelectorAll('.player-card').forEach(card => {
        card.classList.remove('answered-correctly',
                             'answered-wrong',
                             'answered-starbrust',
                             'ready');
        card.classList.add('answered-starbrust');
    });
});

// 更新計時器
function updateTimer() {
    document.getElementById('timer').textContent = `剩餘時間: ${timeLeft} 秒`;
    
    if (timeLeft <= 0) {
        clearInterval(countdownInterval);
        document.getElementById('timer').textContent = '時間到！';
        document.getElementById('answer-input').disabled = true;
        document.getElementById('submit-button').disabled = true;
        return;  // 確保時間到後不再遞減 timeLeft
    }
    
    timeLeft--;
}

// 玩家答題
socket.on('player_answered', function(data) {
    console.log('玩家答題:', data);
    // 找到玩家卡片，使用更可靠的方法
    const playerCards = document.querySelectorAll('.player-card');
    for (const card of playerCards) {
        // 查找玩家名稱元素
        const nameElements = card.querySelectorAll('span');
        for (const element of nameElements) {
            // 檢查文本內容是否包含玩家名稱
            if (element.textContent.includes(data.username)) {
                card.classList.add('answered-starbrust');
                break;
            }
        }
    }
});

// 時間到
// 時間到
socket.on('time_up', function(data) {
    console.log('時間到:', data);
    clearInterval(countdownInterval);
    document.getElementById('timer').textContent = '時間到！';
    document.getElementById('time-up-message').style.display = 'block';
    document.getElementById('time-up-message').textContent = `時間到！正確答案是: ${data.correct_answer}`;
    document.getElementById('answer-input').disabled = true;
    document.getElementById('submit-button').disabled = true;
    
    // 添加 debug 訊息，確認接收到時間到事件
    console.log('已接收時間到事件，等待服務器發送下一題...');
});

// 添加 debug 日誌，確認收到新問題
socket.on('new_question', function(data) {
    console.log('收到新問題:', data);
    // 其餘現有代碼不變...
});

// 有人回答正確
socket.on('someone_answered_correctly', function(data) {
    console.log('有人回答正確:', data);
    correctAnswerUsername = data.username;
    
    // 標記答對的玩家（保持原有邏輯）
    const playerCards = document.querySelectorAll('.player-card');
    for (const card of playerCards) {
        // 查找所有文本元素
        const textElements = card.querySelectorAll('span');
        let found = false;
        
        // 檢查每個文本元素是否包含玩家名稱
        for (const element of textElements) {
            if (element.textContent.includes(data.username)) {
                card.classList.remove('answered-starbrust');
                card.classList.add('answered-correctly');
                found = true;
                break;
            }
        }
        
        if (found) break;
    }
    
    // 搶快模式下，如果是他人答對，禁用輸入框
    if (data.username !== myUsername && data.mode === 'first') {
        document.getElementById('answer-input').disabled = true;
        document.getElementById('submit-button').disabled = true;
    }
    
    // 在搶快模式下，停止計時器 - 新增的部分
    if (data.stop_timer) {
        clearInterval(countdownInterval);
        document.getElementById('timer').textContent = '有人答對！等待下一題...';
    }
});

socket.on('someone_answered_incorrectly', function(data) {
    console.log('有人回答錯誤:', data);
    // 標記答錯的玩家 - 使用更可靠的方法
    const playerCards = document.querySelectorAll('.player-card');
    for (const card of playerCards) {
        // 查找所有文本元素
        const textElements = card.querySelectorAll('span');
        let found = false;
        
        // 檢查每個文本元素是否包含玩家名稱
        for (const element of textElements) {
            if (element.textContent.includes(data.username)) {
                card.classList.remove('answered-starbrust');
                card.classList.add('answered-wrong');
                found = true;
                break;
            }
        }
        
        if (found) break;
    }
});

// 答案被拒絕
socket.on('answer_rejected', function(data) {
    console.log('答案被拒絕:', data);
    alert(data.message);
});

// 答案結果
socket.on('answer_result', function(data) {
    console.log('答案結果:', data);
    isAnswered = true;

    // 尋找自己的卡片
    const playerCards = document.querySelectorAll('.player-card');
    let myCard = null;
    
    for (const card of playerCards) {
        const textElements = card.querySelectorAll('span');
        for (const element of textElements) {
            if (element.textContent.includes(myUsername)) {
                myCard = card;
                break;
            }
        }
        if (myCard) break;
    }

    if (myCard) {
        myCard.classList.remove('answered-starbrust');
        if (data.correct) {
            myCard.classList.add('answered-correctly');
        } else {
            myCard.classList.add('answered-wrong');
        }
    }
    
    const resultContainer = document.getElementById('result-container');
    resultContainer.style.display = 'block';
    
    if (data.correct) {
        resultContainer.className = 'result-container correct';
        if (data.points > 0) {
            resultContainer.innerHTML = `<strong>回答正確！</strong><br>獲得 ${data.points} 分！`;
        } else {
            resultContainer.innerHTML = `<strong>回答正確！</strong><br>但本題未得分。`;
        }
    } else {
        resultContainer.className = 'result-container incorrect';
        resultContainer.innerHTML = `<strong>回答錯誤！</strong><br>正確答案是: ${data.correct_answer}`;
    }
    
    document.getElementById('answer-input').disabled = true;
    document.getElementById('submit-button').disabled = true;
});

// 更新分數
socket.on('update_scores', function(data) {
    console.log('更新分數:', data);
    updatePlayerScores(data.scores);
});

// 遊戲結束
// 修改 socket.on('game_over') 事件處理函數
// 在 static/js/game.js 中找到此函數並替換

// 修改 socket.on('game_over') 事件處理函數
// 修改積分模式遊戲結束處理，突出顯示積分變化
socket.on('game_over', function(data) {
    console.log('遊戲結束:', data);
    gameInProgress = false;
    
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    
    const gameOverContainer = document.getElementById('game-over');
    gameOverContainer.style.display = 'block';
    document.getElementById('game-screen').style.display = 'none';
    
    let contentHTML = '';
    
    // 檢查是否為積分模式
    const isRanked = data.is_ranked;
    const ratingChanges = data.rating_changes || {};
    const oldRatings = data.old_ratings || {};
    
    if (data.tie) {
        contentHTML = `
            <h2>遊戲結束</h2>
            <div class="winner">平局！</div>
            <p>平手玩家: ${data.tied_players.join(', ')}</p>
            <div class="final-scores">
                ${Object.entries(data.scores).map(([player, score]) => {
                    let ratingHTML = '';
                    if (isRanked) {
                        const oldRating = oldRatings[player] || 1500;
                        const ratingChange = ratingChanges[player] || 0;
                        const newRating = oldRating + ratingChange;
                        const changeClass = ratingChange > 0 ? 'positive' : (ratingChange < 0 ? 'negative' : '');
                        const changePrefix = ratingChange > 0 ? '+' : '';
                        
                        ratingHTML = `<span class="rating-change ${changeClass}">${changePrefix}${ratingChange}</span>
                                     <span class="new-rating">(${oldRating} → ${newRating})</span>`;
                    }
                    
                    return `<div>${player}: ${score}分 ${ratingHTML}</div>`;
                }).join('')}
            </div>
            <div id="redirect-message">${isRanked ? '積分模式' : '普通模式'} - 30秒後返回主頁...</div>
            <div class="game-over-buttons">
                <button onclick="backToHomepage()">立即返回主頁</button>
                <button onclick="window.location.href='/leaderboard'" class="leaderboard-button">查看排行榜</button>
            </div>
        `;
    } else {
        contentHTML = `
            <h2>遊戲結束</h2>
            <div class="winner">贏家: ${data.winner}</div>
            <div class="final-scores">
                ${Object.entries(data.scores).map(([player, score]) => {
                    let ratingHTML = '';
                    if (isRanked) {
                        const oldRating = oldRatings[player] || 1500;
                        const ratingChange = ratingChanges[player] || 0;
                        const newRating = oldRating + ratingChange;
                        const changeClass = ratingChange > 0 ? 'positive' : (ratingChange < 0 ? 'negative' : '');
                        const changePrefix = ratingChange > 0 ? '+' : '';
                        
                        ratingHTML = `<span class="rating-change ${changeClass}">${changePrefix}${ratingChange}</span>
                                     <span class="new-rating">(${oldRating} → ${newRating})</span>`;
                    }
                    
                    return `<div>${player}: ${score}分 ${ratingHTML}</div>`;
                }).join('')}
            </div>
            <div id="redirect-message">${isRanked ? '積分模式' : '普通模式'} - 30秒後返回主頁...</div>
            <div class="game-over-buttons">
                <button onclick="backToHomepage()">立即返回主頁</button>
                <button onclick="window.location.href='/leaderboard'" class="leaderboard-button">查看排行榜</button>
            </div>
        `;
    }
    
    gameOverContainer.innerHTML = contentHTML;
    
    // 縮短積分模式的自動返回時間
    let countdown = isRanked ? 30 : 100;
    const redirectMessage = document.getElementById('redirect-message');
    
    redirectTimer = setInterval(function() {
        countdown--;
        redirectMessage.textContent = `${isRanked ? '積分模式' : '普通模式'} - ${countdown}秒後返回主頁...`;
        
        if (countdown <= 0) {
            clearInterval(redirectTimer);
            backToHomepage();
        }
    }, 1000);
});

socket.on('game_countdown', function(data) {
    console.log('遊戲即將開始，倒數:', data.countdown);
    const countdownOverlay = document.getElementById('game-countdown');
    const countdownNumber = document.getElementById('countdown-number');
    let countdown = data.countdown;
    
    countdownOverlay.style.display = 'flex';
    countdownNumber.textContent = countdown;
    
    const countdownInterval = setInterval(() => {
        countdown--;
        countdownNumber.textContent = countdown;
        
        if (countdown <= 0) {
            clearInterval(countdownInterval);
            countdownOverlay.style.display = 'none';
        }
    }, 1000);
});

// 添加下一題倒數計時功能
socket.on('next_question_countdown', function(data) {
    console.log('下一題即將開始，倒數:', data.countdown);
    const nextQuestionCountdown = document.getElementById('next-question-countdown');
    const nextQuestionNumber = document.getElementById('next-question-number');
    let countdown = data.countdown;
    
    nextQuestionCountdown.style.display = 'block';
    nextQuestionNumber.textContent = countdown;
    
    const countdownInterval = setInterval(() => {
        countdown--;
        nextQuestionNumber.textContent = countdown;
        
        if (countdown <= 0) {
            clearInterval(countdownInterval);
            nextQuestionCountdown.style.display = 'none';
        }
    }, 1000);
});

// 用戶離開
socket.on('user_left', function(data) {
    console.log('用戶離開:', data);
});

// 初始化
function init() {
    // 從URL參數中獲取用戶名和房間ID
    const params = new URLSearchParams(window.location.search);
    myUsername = params.get('username') || '';
    
    if (myUsername) {
        localStorage.setItem('username', myUsername);
    } else {
        myUsername = localStorage.getItem('username') || '';
    }
    
    // 獲取房間ID
    fetchRoomInfo();
}

// 更新玩家列表 - 完全重寫
function updatePlayerList(players, scores, readyStatus, ratings, gameStarted) {
    const container = document.getElementById('player-list');
    container.innerHTML = '';

    players.forEach(name => {
        const card = document.createElement('div');
        card.className = 'player-card';
        if (name === myUsername) card.classList.add('current-player');
        if (readyStatus[name]) card.classList.add('ready');

        // 玩家名稱 + (你)
        const nameContainer = document.createElement('div');
        nameContainer.className = 'username';
        
        const nameSpan = document.createElement('span');
        nameSpan.className = 'player-name ' + getRatingClass(ratings[name] || 1500);
        nameSpan.textContent = name + (name === myUsername ? ' (你)' : '');
        nameContainer.appendChild(nameSpan);

        // R 值
        const ratingSpan = document.createElement('div');
        ratingSpan.className = 'player-rating';
        ratingSpan.textContent = `R: ${ratings[name] || 1500}`;

        // 分數
        const scoreSpan = document.createElement('div');
        scoreSpan.className = 'player-score';
        scoreSpan.textContent = `分數: ${scores[name] || 0}`;

        // 組起來
        card.appendChild(nameContainer);
        card.appendChild(ratingSpan);
        card.appendChild(scoreSpan);

        container.appendChild(card);
    });
}

// 更新玩家分數
function updatePlayerScores(scores) {
    const playerCards = document.querySelectorAll('.player-card');
    
    playerCards.forEach(card => {
        // 查找所有文本元素，找到匹配玩家名稱的元素
        const nameElements = card.querySelectorAll('span');
        let playerName = null;
        
        for (const element of nameElements) {
            const text = element.textContent.replace(' (你)', '');
            if (scores.hasOwnProperty(text)) {
                playerName = text;
                break;
            }
        }
        
        if (playerName) {
            // 找到分數元素並更新內容
            const scoreElements = card.querySelectorAll('div');
            for (const element of scoreElements) {
                if (element.className === 'player-score') {
                    element.textContent = `分數: ${scores[playerName] || 0}`;
                    break;
                }
            }
        }
    });
}

// 標記準備開始
function markReady() {
    socket.emit('player_ready');
    document.getElementById('ready-button').disabled = true;
    document.getElementById('ready-button').textContent = '已準備';
}

// 提交答案
function submitAnswer() {
    if (isAnswered) return;
    
    const answerInput = document.getElementById('answer-input');
    const answer = answerInput.value.trim();
    
    if (!answer || !answer.match(/^-?\d+$/)) {
        alert('請輸入有效的整數');
        return;
    }

    // 轉換為數字並驗證範圍 (0 ≤ answer < p) - 新增這部分
    const numAnswer = parseInt(answer, 10);
    if (numAnswer < 0 || numAnswer >= currentPValue) {
        alert(`請輸入 0 到 ${currentPValue-1} 之間的整數`);
        return;
    }

    // 找到自己的卡片
    const playerCards = document.querySelectorAll('.player-card');
    let myCard = null;
    
    for (const card of playerCards) {
        if (card.classList.contains('current-player')) {
            myCard = card;
            break;
        }
    }

    if (myCard) {
        myCard.classList.add('answered-starbrust');
        myCard.classList.remove('answered-wrong', 'answered-correctly');
    }
    
    socket.emit('submit_answer', { answer: answer });
    document.getElementById('submit-button').disabled = true;
}

// 返回主頁
function backToHomepage() {
    // 清除所有計時器
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    if (redirectTimer) {
        clearInterval(redirectTimer);
    }
    
    // 清除會話並返回主頁
    fetch('/leave_room', {
        method: 'POST'
    })
    .then(() => {
        window.location.href = '/';
    })
    .catch(error => {
        console.error('離開房間出錯:', error);
        window.location.href = '/';
    });
}

// 添加按鍵事件監聽器，按Enter可提交答案
document.getElementById('answer-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        submitAnswer();
    }
});

// 初始化頁面
window.onload = init;

// 添加beforeunload事件監聽器，確保在頁面關閉時清理
window.addEventListener('beforeunload', function() {
    fetch('/leave_room', { method: 'POST' });
});

// 取消準備函數
function cancelReady() {
    socket.emit('player_cancel_ready');
}

// 處理取消準備的回應
socket.on('cancel_ready_response', function(data) {
    if (data.success) {
        // 取消準備成功
        document.getElementById('ready-button').disabled = false;
        document.getElementById('ready-button').textContent = '準備開始';
        document.getElementById('cancel-ready-button').style.display = 'none';
    } else {
        // 取消準備失敗
        alert(data.message);
    }
});

// 修改現有的 markReady 函數
function markReady() {
    socket.emit('player_ready');
    document.getElementById('ready-button').disabled = true;
    document.getElementById('ready-button').textContent = '已準備';
    document.getElementById('cancel-ready-button').style.display = 'inline-block';
}

// 修改 player_ready_status 事件處理
socket.on('player_ready_status', function(data) {
    console.log('準備狀態:', data);
    document.querySelector('.waiting-message').textContent = 
        `等待玩家準備... (${data.ready_count}/${data.total_players})`;
        
    // 更新玩家準備狀態
    const playerCards = document.querySelectorAll('.player-card');
    playerCards.forEach(card => {
        // 獲取玩家卡片中的玩家名稱
        const playerNameElement = card.querySelector('.player-name');
        if (playerNameElement) {
            const playerName = playerNameElement.textContent.replace(' (你)', '');
            if (playerName === data.username) {
                if (data.canceled) {
                    // 如果是取消準備，則移除準備標記
                    card.classList.remove('ready');
                } else {
                    // 否則添加準備標記
                    card.classList.add('ready');
                }
            }
        }
    });
});

// 添加「人數不足」事件監聽器
socket.on('not_enough_players', function(data) {
    console.log('人數不足:', data);
    document.querySelector('.waiting-message').innerHTML = 
        `<span style="color: red;">人數不足！${data.game_mode === 'first' ? '搶快' : '比速度'}模式需要至少 ${data.min_players} 名玩家，目前只有 ${data.current_players} 名。請等待更多玩家加入。</span>`;
});

// 修改房間狀態更新處理，添加練習模式信息
// 在 socket.on('room_status') 事件處理函數中添加自動準備代碼
// 修改 socket.on('room_status') 事件處理函數
socket.on('room_status', function(data) {
    console.log('房間狀態:', data);
    
    // 更新玩家列表
    updatePlayerList(data.players, data.scores, data.ready || {}, data.ratings, data.game_started);
    
    // 檢測是否為練習模式
    if (data.game_mode === 'practice') {
        document.querySelector('.waiting-message').innerHTML = 
            '練習模式：只需點擊「準備開始」即可開始遊戲';
    }
    
    // 檢測是否為自動開始的積分模式
    if (data.game_mode === 'ranked' || data.is_ranked) {
        // 顯示積分模式標記
        if (document.getElementById('ranked-badge')) {
            document.getElementById('ranked-badge').style.display = 'inline-block';
        }
        
        if (data.auto_start && !data.game_started) {
            document.querySelector('.waiting-message').innerHTML = 
                '積分模式：遊戲即將自動開始...';
            
            // 自動標記為準備
            if (data.players.includes(myUsername) && (!data.ready || !data.ready[myUsername])) {
                console.log('自動準備開始');
                setTimeout(function() {
                    markReady();
                }, 1000);
            }
        }
    }
});

// 修改初始化函數，處理積分模式
function init() {
    // 從URL參數中獲取用戶名和房間ID
    const params = new URLSearchParams(window.location.search);
    myUsername = params.get('username') || '';
    
    if (myUsername) {
        localStorage.setItem('username', myUsername);
    } else {
        myUsername = localStorage.getItem('username') || '';
    }
    
    // 獲取房間ID和遊戲模式
    fetchRoomInfo();
    
    // 檢查是否為積分模式
    fetch('/get_room_details')
        .then(response => {
            if (!response.ok) {
                throw new Error('請求失敗');
            }
            return response.json();
        })
        .then(data => {
            if (!data.error) {
                // 檢查是否為積分模式
                if (data.game_mode === 'ranked' || data.is_ranked) {
                    // 顯示積分賽標記
                    if (document.getElementById('ranked-badge')) {
                        document.getElementById('ranked-badge').style.display = 'inline-block';
                    }
                    
                    // 更新提示訊息
                    document.querySelector('.waiting-message').innerHTML = 
                        '積分模式：等待雙方連接，遊戲將自動開始...';
                }
            }
        })
        .catch(error => {
            console.error('獲取房間信息出錯:', error);
        });
}

// 添加積分模式全部玩家已連接事件處理
socket.on('ranked_all_connected', function(data) {
    console.log('積分模式：所有玩家已連接，倒數開始');
    const rankedInfo = document.getElementById('ranked-countdown-info');
    if (rankedInfo) {
        rankedInfo.style.display = 'block';
    }
    
    // 顯示玩家名稱
    const playerStatus = document.getElementById('ranked-player-status');
    if (playerStatus) {
        playerStatus.textContent = `玩家 ${data.players.join(' 和 ')} 已連接`;
    }
    
    // 開始倒數
    let countdown = data.countdown;
    const countdownTimer = document.getElementById('ranked-countdown-timer');
    if (countdownTimer) {
        countdownTimer.textContent = countdown;
        
        const countdownInterval = setInterval(function() {
            countdown--;
            countdownTimer.textContent = countdown;
            
            if (countdown <= 0) {
                clearInterval(countdownInterval);
                // 倒數結束，等待服務器啟動遊戲
            }
        }, 1000);
    }
});