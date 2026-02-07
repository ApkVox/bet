const NBA_LOGOS = {
    "Atlanta Hawks": "https://cdn.nba.com/logos/nba/1610612737/global/L/logo.svg",
    "Boston Celtics": "https://cdn.nba.com/logos/nba/1610612738/global/L/logo.svg",
    "Brooklyn Nets": "https://cdn.nba.com/logos/nba/1610612751/global/L/logo.svg",
    "Charlotte Hornets": "https://cdn.nba.com/logos/nba/1610612766/global/L/logo.svg",
    "Chicago Bulls": "https://cdn.nba.com/logos/nba/1610612741/global/L/logo.svg",
    "Cleveland Cavaliers": "https://cdn.nba.com/logos/nba/1610612739/global/L/logo.svg",
    "Dallas Mavericks": "https://cdn.nba.com/logos/nba/1610612742/global/L/logo.svg",
    "Denver Nuggets": "https://cdn.nba.com/logos/nba/1610612743/global/L/logo.svg",
    "Detroit Pistons": "https://cdn.nba.com/logos/nba/1610612765/global/L/logo.svg",
    "Golden State Warriors": "https://cdn.nba.com/logos/nba/1610612744/global/L/logo.svg",
    "Houston Rockets": "https://cdn.nba.com/logos/nba/1610612745/global/L/logo.svg",
    "Indiana Pacers": "https://cdn.nba.com/logos/nba/1610612754/global/L/logo.svg",
    "LA Clippers": "https://cdn.nba.com/logos/nba/1610612746/global/L/logo.svg",
    "Los Angeles Lakers": "https://cdn.nba.com/logos/nba/1610612747/global/L/logo.svg",
    "Memphis Grizzlies": "https://cdn.nba.com/logos/nba/1610612763/global/L/logo.svg",
    "Miami Heat": "https://cdn.nba.com/logos/nba/1610612748/global/L/logo.svg",
    "Milwaukee Bucks": "https://cdn.nba.com/logos/nba/1610612749/global/L/logo.svg",
    "Minnesota Timberwolves": "https://cdn.nba.com/logos/nba/1610612750/global/L/logo.svg",
    "New Orleans Pelicans": "https://cdn.nba.com/logos/nba/1610612740/global/L/logo.svg",
    "New York Knicks": "https://cdn.nba.com/logos/nba/1610612752/global/L/logo.svg",
    "Oklahoma City Thunder": "https://cdn.nba.com/logos/nba/1610612760/global/L/logo.svg",
    "Orlando Magic": "https://cdn.nba.com/logos/nba/1610612753/global/L/logo.svg",
    "Philadelphia 76ers": "https://cdn.nba.com/logos/nba/1610612755/global/L/logo.svg",
    "Phoenix Suns": "https://cdn.nba.com/logos/nba/1610612756/global/L/logo.svg",
    "Portland Trail Blazers": "https://cdn.nba.com/logos/nba/1610612757/global/L/logo.svg",
    "Sacramento Kings": "https://cdn.nba.com/logos/nba/1610612758/global/L/logo.svg",
    "San Antonio Spurs": "https://cdn.nba.com/logos/nba/1610612759/global/L/logo.svg",
    "Toronto Raptors": "https://cdn.nba.com/logos/nba/1610612761/global/L/logo.svg",
    "Utah Jazz": "https://cdn.nba.com/logos/nba/1610612762/global/L/logo.svg",
    "Washington Wizards": "https://cdn.nba.com/logos/nba/1610612764/global/L/logo.svg"
};

const PL_LOGOS = {
    "Arsenal": "https://resources.premierleague.com/premierleague/badges/50/t3.png",
    "Aston Villa": "https://resources.premierleague.com/premierleague/badges/50/t7.png"
    // ... truncated but logic same
};

// Theme
function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    const icon = theme === 'dark' ? '☀️' : '🌙';
    document.getElementById('themeToggle').textContent = icon;
}

document.getElementById('themeToggle').addEventListener('click', () => {
    const current = document.documentElement.getAttribute('data-theme');
    setTheme(current === 'dark' ? 'light' : 'dark');
});

// Navigation
function switchSection(sectionId) {
    document.querySelectorAll('.nav-tab, .mobile-nav-btn').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll(`[data-section="${sectionId}"]`).forEach(t => t.classList.add('active'));
    document.getElementById(sectionId).classList.add('active');
}

document.querySelectorAll('[data-section]').forEach(btn => {
    btn.addEventListener('click', () => switchSection(btn.dataset.section));
});

// Predictions
let currentSport = 'nba';

document.querySelectorAll('.sport-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.sport-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentSport = btn.dataset.sport;
        loadPredictions();
        loadHistory();
    });
});

async function loadPredictions() {
    const grid = document.getElementById('predictionsGrid');
    if (currentSport === 'football') {
        grid.innerHTML = `<div class="empty-state"><h3>🚧 En Construcción</h3><p>Mejorando modelo de fútbol...</p></div>`;
        return;
    }
    grid.innerHTML = '<div class="loading">Cargando...</div>';
    try {
        const res = await fetch('/predict-today');
        const data = await res.json();
        renderPredictions(data.predictions || []);
    } catch (e) { grid.innerHTML = 'Error'; }
}

function renderPredictions(preds) {
    const grid = document.getElementById('predictionsGrid');
    document.getElementById('games-today').textContent = preds.length;
    grid.innerHTML = preds.map(p => `
        <div class="prediction-card">
            <div class="match-header">
                <span>${p.home_team} vs ${p.away_team}</span>
            </div>
            <div class="prediction-result">
                <strong>${p.winner}</strong>
                <div>${p.win_probability}%</div>
            </div>
        </div>
    `).join('');
}

// History
async function loadHistory() {
    const container = document.getElementById('historyContainer');
    if (currentSport === 'football') {
        container.innerHTML = '<p>No disponible</p>';
        return;
    }
    try {
        const res = await fetch('/history/full?days=30');
        const data = await res.json();
        renderHistory(data.history || []);
    } catch (e) { container.innerHTML = 'Error'; }
}

function renderHistory(history) {
    const container = document.getElementById('historyContainer');
    container.innerHTML = '<div class="history-cards">' + history.map(h => `
        <div class="history-card">
            <div>${h.match}</div>
            <div class="result-badge ${h.result?.toLowerCase()}">${h.result}</div>
        </div>
    `).join('') + '</div>';
}

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadPredictions();
    loadHistory();
});

function initTheme() {
    const saved = localStorage.getItem('theme') || 'light';
    setTheme(saved);
}
