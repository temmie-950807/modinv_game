// 獲取目前登入使用者名稱
const currentUsername = localStorage.getItem('username') || '';

// 定義一個函數來根據 rating 設定對應的 class
function getRatingClass(rating) {
    if (rating >= 1900) return 'candidate_master';
    if (rating >= 1600) return 'expert';
    if (rating >= 1400) return 'specialist';
    return 'normal';
}

// 載入排行榜數據
function loadLeaderboard() {
    fetch('/api/leaderboard')
        .then(response => {
            if (!response.ok) {
                throw new Error('網路連接異常');
            }
            return response.json();
        })
        .then(data => {
            displayLeaderboard(data.players);
            updateStatistics(data.players);
        })
        .catch(error => {
            console.error('載入排行榜失敗:', error);
            document.getElementById('leaderboard-body').innerHTML = `
                <tr>
                    <td colspan="3" style="text-align: center; color: red;">
                        載入失敗，請重新整理頁面。錯誤: ${error.message}
                    </td>
                </tr>
            `;
        });
}

// 顯示排行榜數據
function displayLeaderboard(players) {
    const tableBody = document.getElementById('leaderboard-body');
    tableBody.innerHTML = '';
    
    if (players.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="3" style="text-align: center;">目前沒有玩家資料</td></tr>';
        return;
    }
    
    players.forEach((player, index) => {
        const row = document.createElement('tr');
        const rankCell = document.createElement('td');
        const usernameCell = document.createElement('td');
        const ratingCell = document.createElement('td');
        
        // 設定排名
        const rank = index + 1;
        rankCell.textContent = rank;
        if (rank <= 3) {
            rankCell.classList.add(`rank-${rank}`);
        }
        
        // 設定用戶名及樣式
        const ratingClass = getRatingClass(player.rating);
        usernameCell.innerHTML = `<span class="${ratingClass}">${player.username}</span>`;
        
        // 設定 rating
        ratingCell.textContent = player.rating;
        
        // 如果是當前用戶，高亮顯示
        if (player.username === currentUsername) {
            row.classList.add('current-user');
        }
        
        row.appendChild(rankCell);
        row.appendChild(usernameCell);
        row.appendChild(ratingCell);
        tableBody.appendChild(row);
    });
}

// 更新統計資料
function updateStatistics(players) {
    const totalPlayers = players.length;
    document.getElementById('total-players').textContent = totalPlayers;
    
    if (totalPlayers > 0) {
        // 計算平均 rating
        const totalRating = players.reduce((sum, player) => sum + player.rating, 0);
        const averageRating = Math.round(totalRating / totalPlayers);
        document.getElementById('average-rating').textContent = averageRating;
        
        // 最高 rating
        const highestRating = players[0].rating;
        document.getElementById('highest-rating').textContent = highestRating;
    } else {
        document.getElementById('average-rating').textContent = 'N/A';
        document.getElementById('highest-rating').textContent = 'N/A';
    }
}

// 搜尋過濾功能
function setupSearchFilter() {
    const searchInput = document.getElementById('search-input');
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const rows = document.querySelectorAll('#leaderboard-body tr');
        
        rows.forEach(row => {
            const username = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
            if (username.includes(searchTerm)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
}

// 頁面載入時執行
document.addEventListener('DOMContentLoaded', function() {
    loadLeaderboard();
    setupSearchFilter();
});