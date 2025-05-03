function openTab(evt, tabName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}

function createRoom() {
    const difficulty = document.getElementById('create-difficulty').value;
    const mode = document.getElementById('create-mode').value;
    const questionCount = document.getElementById('create-question-count').value;
    const gameTime = document.getElementById('game-time').value;
    const formData = new FormData();
    formData.append('difficulty', difficulty);
    formData.append('game_mode', mode);
    formData.append('question_count', questionCount);
    formData.append('game_time', gameTime);  // 將 'game-time' 改為 'game_time'
    const roomId = document.getElementById('create-room-id').value.trim();
    const errorElement = document.getElementById('create-error');
    
    if (roomId) {
        formData.append('room_id', roomId);
    }

    // 新增檢查房間 ID 格式
    const roomIdPattern = /^[a-zA-Z0-9]+$/; // 僅允許大小寫英文與數字
    if (roomId && !roomIdPattern.test(roomId)) {
        errorElement.textContent = "僅能輸入大小寫英文或數字";
        return;
    }
    
    fetch('/create_room', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            errorElement.textContent = data.error;
        } else {
            window.location.href = '/game';
        }
    })
    .catch(error => {
        errorElement.textContent = "發生錯誤，請稍後再試";
        console.error('Error:', error);
    });
}

function joinRoom() {
    const roomId = document.getElementById('join-room-id').value.trim();
    const errorElement = document.getElementById('join-error');
    
    if (!roomId) {
        errorElement.textContent = "請輸入房間號碼";
        return;
    }

    // 檢查房間 ID 格式
    const roomIdPattern = /^[a-zA-Z0-9]+$/; // 僅允許大小寫英文與數字
    if (!roomIdPattern.test(roomId)) {
        errorElement.textContent = "僅能輸入大小寫英文或數字";
        return;
    }
    
    const formData = new FormData();
    formData.append('room_id', roomId);
    
    fetch('/join_room', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            errorElement.textContent = data.error;
        } else {
            window.location.href = '/game';
        }
    })
    .catch(error => {
        errorElement.textContent = "發生錯誤，請稍後再試";
        console.error('Error:', error);
    });
}

// 在 document.ready 或等效的位置添加以下代碼
document.addEventListener('DOMContentLoaded', function() {
    // 監聽遊戲模式選擇變化
    const modeSelect = document.getElementById('create-mode');
    if (modeSelect) {
        modeSelect.addEventListener('change', function() {
            updateGameModeInfo(this.value);
        });
        
        // 初始化時更新一次
        updateGameModeInfo(modeSelect.value);
    }
});

// 更新遊戲模式信息顯示
function updateGameModeInfo(mode) {
    let infoText = '';
    let infoColor = '#f0f0f0';
    
    if (mode === 'practice') {
        infoText = '練習模式：單人練習，無需等待其他玩家加入';
        infoColor = '#e8f5e9';
    } else if (mode === 'first') {
        infoText = '搶快模式：需要至少兩名玩家，第一個答對的玩家獲得分數';
        infoColor = '#e3f2fd';
    } else if (mode === 'speed') {
        infoText = '比速度模式：需要至少兩名玩家，根據回答速度獲得不同分數';
        infoColor = '#fff3e0';
    }
    
    // 檢查是否已存在信息元素，如果不存在則創建
    let infoElement = document.getElementById('mode-info');
    if (!infoElement) {
        infoElement = document.createElement('div');
        infoElement.id = 'mode-info';
        infoElement.style.padding = '10px';
        infoElement.style.marginTop = '10px';
        infoElement.style.borderRadius = '4px';
        
        // 插入到適當位置
        const createTab = document.getElementById('CreateRoom');
        if (createTab) {
            const buttonElement = createTab.querySelector('button');
            if (buttonElement) {
                createTab.insertBefore(infoElement, buttonElement);
            } else {
                createTab.appendChild(infoElement);
            }
        }
    }
    
    // 更新信息
    infoElement.textContent = infoText;
    infoElement.style.backgroundColor = infoColor;
}

// 全局變數
let rankedQueueInterval = null;
let rankedQueueStatus = 'none'; // 'none', 'waiting', 'matched'

// 重置隊列狀態
function resetQueueStatus() {
    // 停止輪詢
    if (rankedQueueInterval) {
        clearInterval(rankedQueueInterval);
        rankedQueueInterval = null;
    }
    
    // 重置狀態
    rankedQueueStatus = 'none';
    
    // 重置UI
    document.getElementById('ranked-status').className = 'ranked-status';
    document.getElementById('ranked-status').textContent = '您目前未在積分模式隊列中';
    document.getElementById('join-ranked-button').style.display = 'inline-block';
    document.getElementById('cancel-ranked-button').style.display = 'none';
    document.getElementById('ranked-match-info').style.display = 'none';
}

// 加入積分模式隊列
function joinRankedQueue() {
    // 顯示等待中UI
    rankedQueueStatus = 'waiting';
    document.getElementById('ranked-status').className = 'ranked-status waiting';
    document.getElementById('ranked-status').innerHTML = '正在等待對手中 <span class="waiting-animation">...</span>';
    document.getElementById('join-ranked-button').style.display = 'none';
    document.getElementById('cancel-ranked-button').style.display = 'inline-block';
    
    // 發送加入隊列請求
    fetch('/join_ranked_queue', {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('請求失敗');
        }
        return response.json();
    })
    .then(data => {
        console.log('Join queue response:', data);
        
        if (data.status === 'waiting') {
            // 啟動輪詢
            if (!rankedQueueInterval) {
                rankedQueueInterval = setInterval(checkMatchStatus, 1000);
            }
        } else if (data.status === 'matched') {
            // 匹配成功，處理匹配結果
            handleMatchSuccess(data);
        } else if (data.error) {
            // 顯示錯誤
            alert('錯誤: ' + data.error);
            resetQueueStatus();
        }
    })
    .catch(error => {
        console.error('加入積分模式隊列出錯:', error);
        alert('加入積分模式隊列失敗，請稍後再試');
        resetQueueStatus();
    });
}

// 檢查匹配狀態
function checkMatchStatus() {
    if (rankedQueueStatus !== 'waiting') {
        return;
    }
    
    fetch('/check_match_status', {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('請求失敗');
        }
        return response.json();
    })
    .then(data => {
        console.log('Check match status response:', data);
        
        if (data.status === 'matched') {
            // 匹配成功，處理匹配結果
            handleMatchSuccess(data);
        } else if (data.status === 'not_in_queue') {
            // 不在隊列中，可能是系統清理了
            alert('您已經不在匹配隊列中，請重新加入');
            resetQueueStatus();
        }
        // 如果仍在等待中，繼續輪詢
    })
    .catch(error => {
        console.error('檢查匹配狀態出錯:', error);
        // 錯誤時不要重置狀態，繼續輪詢
    });
}

// 處理匹配成功
// 處理匹配成功
function handleMatchSuccess(data) {
    // 停止輪詢
    if (rankedQueueInterval) {
        clearInterval(rankedQueueInterval);
        rankedQueueInterval = null;
    }
    
    // 更新匹配狀態
    rankedQueueStatus = 'matched';
    
    // 更新UI
    document.getElementById('ranked-status').className = 'ranked-status matched';
    document.getElementById('ranked-status').textContent = '匹配成功！即將進入比賽...';
    document.getElementById('join-ranked-button').style.display = 'none';
    document.getElementById('cancel-ranked-button').style.display = 'none';
    
    // 顯示匹配信息
    const matchInfoElement = document.getElementById('ranked-match-info');
    matchInfoElement.style.display = 'block';
    
    document.getElementById('ranked-opponent').textContent = data.opponent || '未知對手';
    
    let difficultyText = '';
    if (data.difficulty === 'easy') {
        difficultyText = '簡單';
    } else if (data.difficulty === 'medium') {
        difficultyText = '中等';
    } else {
        difficultyText = '困難';
    }
    
    document.getElementById('ranked-difficulty').textContent = difficultyText;
    document.getElementById('ranked-question-count').textContent = data.question_count || '未知';
    
    // 自動跳轉到遊戲頁面
    setTimeout(function() {
        window.location.href = '/game';
    }, 2000);
}

// 檢查積分模式隊列狀態
function checkRankedQueue() {
    if (rankedQueueStatus === 'waiting') {
        fetch('/join_ranked_queue', {  // 直接使用同一個端點
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'matched') {
                handleMatchSuccess(data);
            } else if (data.status === 'check_again') {
                // 需要再次檢查
                setTimeout(function() {
                    joinRankedQueue();
                }, 500);
            }
            // 如果仍在等待，繼續輪詢
        })
        .catch(error => {
            console.error('檢查積分模式狀態出錯:', error);
        });
    }
}

// 取消積分模式匹配
// 取消匹配
function cancelRankedQueue() {
    fetch('/cancel_ranked_queue', {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('請求失敗');
        }
        return response.json();
    })
    .then(data => {
        console.log('Cancel queue response:', data);
        resetQueueStatus();
    })
    .catch(error => {
        console.error('取消匹配出錯:', error);
        alert('取消匹配失敗，請稍後再試');
    });
}

// 確認積分模式匹配並進入遊戲
function confirmRankedMatch() {
    fetch('/confirm_ranked_match', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
        } else {
            // 重置匹配狀態
            rankedQueueStatus = 'none';
            
            // 停止輪詢
            if (rankedQueueInterval) {
                clearInterval(rankedQueueInterval);
                rankedQueueInterval = null;
            }
            
            // 跳轉到遊戲頁面
            window.location.href = '/game';
        }
    })
    .catch(error => {
        console.error('確認積分模式出錯:', error);
        alert('確認積分模式失敗，請稍後再試');
    });
}

// 頁面離開時清理
window.addEventListener('beforeunload', function() {
    if (rankedQueueStatus === 'waiting') {
        // 嘗試取消匹配
        fetch('/cancel_ranked_queue', { 
            method: 'POST',
            keepalive: true // 確保在頁面關閉時仍能完成請求
        });
    }
    
    // 停止輪詢
    if (rankedQueueInterval) {
        clearInterval(rankedQueueInterval);
        rankedQueueInterval = null;
    }
});

// 添加到 index.js
function resetRankedMatch() {
    fetch('/reset_ranked_match', {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('請求失敗');
        }
        return response.json();
    })
    .then(data => {
        console.log('Reset ranked match response:', data);
        alert(data.message || '已重置積分模式匹配');
        resetQueueStatus();
    })
    .catch(error => {
        console.error('重置積分模式出錯:', error);
        alert('重置積分模式失敗，請稍後再試');
    });
}

// 修改頁面載入時的檢查
document.addEventListener('DOMContentLoaded', function() {
    // 檢查是否有卡住的積分模式
    fetch('/check_match_status', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'matched' && data.elapsed_time > 60) {
            // 如果匹配時間超過1分鐘，顯示重置按鈕
            document.getElementById('reset-ranked-button').style.display = 'inline-block';
        }
    })
    .catch(error => {
        console.error('檢查積分模式狀態出錯:', error);
    });
    
    // 其他初始化代碼...
});