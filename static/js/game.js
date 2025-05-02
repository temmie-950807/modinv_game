let gameMode = 'first';
const socket = io();
let myUsername = '';
let isAnswered = false;
let countdownInterval = null;
let timeLeft = 100;
let gameInProgress = false;
let correctAnswerUsername = null;
let redirectTimer = null;

// 當連接到服務器時
socket.on('connect', function() {
    console.log('已連接到服務器');
    fetchRoomInfo();
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
        
    // 更新玩家準備狀態
    const playerCards = document.querySelectorAll('.player-card');
    playerCards.forEach(card => {
        const playerName = card.querySelector('.player-name').textContent.replace(' (你)', '');
        if (playerName === data.username) {
            card.classList.add('ready');
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
    timeLeft = data.time_limit || 100;
    gameMode = data.game_mode;
    correctAnswerUsername = null;
    
    // 重置UI
    document.getElementById('opponent-answered').style.display = 'none';
    document.getElementById('result-container').style.display = 'none';
    document.getElementById('time-up-message').style.display = 'none';
    
    // 啟動新計時器
    clearInterval(countdownInterval);
    updateTimer();
    countdownInterval = setInterval(updateTimer, 1000);
    
    document.getElementById('question-progress').textContent = `問題 ${data.question_number}/7`;
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
    }
    
    timeLeft--;
}

// 玩家答題
socket.on('player_answered', function(data) {
    console.log('玩家答題:', data);
    const card = [...document.querySelectorAll('.player-card')]
        .find(c => c.querySelector('.player-name').textContent.replace(' (你)', '') === data.username);
    // if (card) {
    //     card.classList.add('answered-starbrust');
    // }
});

// 時間到
socket.on('time_up', function(data) {
    console.log('時間到:', data);
    clearInterval(countdownInterval);
    document.getElementById('timer').textContent = '時間到！';
    document.getElementById('time-up-message').style.display = 'block';
    document.getElementById('time-up-message').textContent = `時間到！正確答案是: ${data.correct_answer}`;
    document.getElementById('answer-input').disabled = true;
    document.getElementById('submit-button').disabled = true;
});

// 有人回答正確
socket.on('someone_answered_correctly', function(data) {
    console.log('有人回答正確:', data);
    correctAnswerUsername = data.username;
    
    // 標記答對的玩家
    const playerCards = document.querySelectorAll('.player-card');
    playerCards.forEach(card => {
        const playerName = card.querySelector('.player-name').textContent.replace(' (你)', '');
        if (playerName === data.username) {
            card.classList.add('answered-correctly');
        }
    });
    
    if (data.username !== myUsername && gameMode === 'first') {
        document.getElementById('answer-input').disabled = true;
        document.getElementById('submit-button').disabled = true;
    }
});

socket.on('someone_answered_incorrectly', function(data) {
    console.log('有人回答錯誤:', data);
    const playerCards = document.querySelectorAll('.player-card');
    playerCards.forEach(card => {
        const playerName = card.querySelector('.player-name').textContent.replace(' (你)', '');
        if (playerName === data.username) {
            card.classList.add('answered-wrong');
        }
    });
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

    const card = [...document.querySelectorAll('.player-card')].find(c => c.querySelector('.player-name').textContent.replace(' (你)', '') === data.username);
    if (!card) return;

    card.classList.remove('answered-starbrust');
    if (data.correct) {
        card.classList.add('answered-correctly');
    } else {
        card.classList.add('answered-wrong');
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
socket.on('game_over', function(data) {
    console.log('遊戲結束:', data);
    gameInProgress = false;
    
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    
    const gameOverContainer = document.getElementById('game-over');
    gameOverContainer.style.display = 'block';
    document.getElementById('game-screen').style.display = 'none';
    
    if (data.tie) {
        gameOverContainer.innerHTML = `
            <h2>遊戲結束</h2>
            <div class="winner">平局！</div>
            <p>平手玩家: ${data.tied_players.join(', ')}</p>
            <div class="final-scores">
                ${Object.entries(data.scores).map(([player, score]) => 
                    `<div>${player}: ${score}分</div>`).join('')}
            </div>
            <div id="redirect-message">100秒後返回主頁...</div>
            <button onclick="backToHomepage()">立即返回主頁</button>
        `;
    } else {
        gameOverContainer.innerHTML = `
            <h2>遊戲結束</h2>
            <div class="winner">贏家: ${data.winner}</div>
            <div class="final-scores">
                ${Object.entries(data.scores).map(([player, score]) => 
                    `<div>${player}: ${score}分</div>`).join('')}
            </div>
            <div id="redirect-message">100秒後返回主頁...</div>
            <button onclick="backToHomepage()">立即返回主頁</button>
        `;
    }
    
    // 設置5秒後自動返回主頁的計時器
    let countdown = 100;
    const redirectMessage = document.getElementById('redirect-message');
    
    redirectTimer = setInterval(function() {
        countdown--;
        redirectMessage.textContent = `${countdown}秒後返回主頁...`;
        
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

// 修改新問題處理，添加題目計數
socket.on('new_question', function(data) {
    console.log('新問題:', data);
    isAnswered = false;
    console.log("game_time", data.game_time)
    timeLeft = data.game_time || 30;
    gameMode = data.game_mode;
    correctAnswerUsername = null;
    
    // 重置UI
    document.getElementById('opponent-answered').style.display = 'none';
    
    // 重置計時器
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }
    
    // 啟動新計時器
    updateTimer();
    countdownInterval = setInterval(updateTimer, 1000);
    
    document.getElementById('question-progress').textContent = `問題 ${data.question_number}/${data.question_count}`;
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
    const playerCards = document.querySelectorAll('.player-card');
    playerCards.forEach(card => {
        card.classList.remove('answered-correctly',
                'answered-wrong',
                'answered-starbrust',
                'ready');
    });
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

// 更新玩家列表
function updatePlayerList(players, scores, readyStatus, ratings, gameStarted) {
    const container = document.getElementById('player-list');
    container.innerHTML = '';

    players.forEach(name => {
        const card = document.createElement('div');
        card.className = 'player-card';
        if (name === myUsername) card.classList.add('current-player');

        // 玩家名稱 + (你)
        const nameSpan = document.createElement('span');
        nameSpan.className = 'player-name';
        nameSpan.textContent = name + (name === myUsername ? ' (你)' : '');

        // R 值
        const ratingSpan = document.createElement('span');
        ratingSpan.className = 'player-rating';
        ratingSpan.textContent = ` R: ${ratings[name] || 1500}`;

        // 分數
        const scoreSpan = document.createElement('span');
        scoreSpan.className = 'player-score';
        scoreSpan.textContent = ` 分數: ${scores[name] || 0}`;

        // 準備狀態
        const readySpan = document.createElement('span');
        readySpan.className = 'player-ready';
        readySpan.textContent = readyStatus[name] ? ' 已準備' : '';

        // 組起來
        card.appendChild(nameSpan);
        card.appendChild(ratingSpan);
        card.appendChild(scoreSpan);
        card.appendChild(readySpan);

        container.appendChild(card);
    });
}

// 更新玩家分數
function updatePlayerScores(scores) {
    const playerCards = document.querySelectorAll('.player-card');
    playerCards.forEach(card => {
        const playerName = card.querySelector('.player-name').textContent.replace(' (你)', '');
        const scoreElement = card.querySelector('.player-score');
        if (scoreElement) {
            scoreElement.textContent = `分數: ${scores[playerName] || 0}`;
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
    
    if (!answer) {
        alert('請輸入答案');
        return;
    }

    const myCard = [...document.querySelectorAll('.player-card')].find(c => c.classList.contains('current-player'));
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