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