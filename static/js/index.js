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
    formData.append('game-time', gameTime);
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