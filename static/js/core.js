// Capa de datos de la web pública: fetch, normalización y ajustes. index.html solo pinta.
const LF = (() => {
    // nombre -> [id NBA, sigla]
    const NBA = {
        "Atlanta Hawks": [1610612737, "ATL"], "Boston Celtics": [1610612738, "BOS"], "Brooklyn Nets": [1610612751, "BKN"],
        "Charlotte Hornets": [1610612766, "CHA"], "Chicago Bulls": [1610612741, "CHI"], "Cleveland Cavaliers": [1610612739, "CLE"],
        "Dallas Mavericks": [1610612742, "DAL"], "Denver Nuggets": [1610612743, "DEN"], "Detroit Pistons": [1610612765, "DET"],
        "Golden State Warriors": [1610612744, "GSW"], "Houston Rockets": [1610612745, "HOU"], "Indiana Pacers": [1610612754, "IND"],
        "LA Clippers": [1610612746, "LAC"], "Los Angeles Lakers": [1610612747, "LAL"], "Memphis Grizzlies": [1610612763, "MEM"],
        "Miami Heat": [1610612748, "MIA"], "Milwaukee Bucks": [1610612749, "MIL"], "Minnesota Timberwolves": [1610612750, "MIN"],
        "New Orleans Pelicans": [1610612740, "NOP"], "New York Knicks": [1610612752, "NYK"], "Oklahoma City Thunder": [1610612760, "OKC"],
        "Orlando Magic": [1610612753, "ORL"], "Philadelphia 76ers": [1610612755, "PHI"], "Phoenix Suns": [1610612756, "PHX"],
        "Portland Trail Blazers": [1610612757, "POR"], "Sacramento Kings": [1610612758, "SAC"], "San Antonio Spurs": [1610612759, "SAS"],
        "Toronto Raptors": [1610612761, "TOR"], "Utah Jazz": [1610612762, "UTA"], "Washington Wizards": [1610612764, "WAS"]
    };
    // nombre -> número de escudo de premierleague.com
    const PL = {
        "Arsenal": 3, "Aston Villa": 7, "AFC Bournemouth": 91, "Bournemouth": 91, "Brentford": 94, "Brighton & Hove Albion": 36,
        "Brighton": 36, "Burnley": 90, "Chelsea": 8, "Crystal Palace": 31, "Everton": 11, "Fulham": 54, "Ipswich Town": 40,
        "Ipswich": 40, "Leicester City": 13, "Leicester": 13, "Liverpool": 14, "Manchester City": 43, "Man City": 43,
        "Manchester United": 1, "Man United": 1, "Newcastle United": 4, "Newcastle": 4, "Nottingham Forest": 17,
        "Nott'm Forest": 17, "Southampton": 20, "Tottenham Hotspur": 6, "Tottenham": 6, "West Ham United": 21,
        "West Ham": 21, "Wolverhampton Wanderers": 39, "Wolves": 39
    };

    const state = { sport: 'nba', settings: { features: {}, ads: {}, branding: {}, betting: {}, announcement: {} } };
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;

    const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

    function logo(team, backendLogo) {
        if (backendLogo) return backendLogo;
        if (state.sport === 'nba') return NBA[team] ? `https://cdn.nba.com/logos/nba/${NBA[team][0]}/global/L/logo.svg` : '';
        return PL[team] ? `https://resources.premierleague.com/premierleague/badges/50/t${PL[team]}.png` : '';
    }
    const abbr = team => NBA[team]?.[1] || String(team || '').replace(/[^A-Za-zÀ-ÿ]/g, '').slice(0, 3).toUpperCase();
    const short = team => String(team || '').split(' ').slice(-1)[0]; // "Oklahoma City Thunder" -> "Thunder"

    async function getJSON(url) {
        const r = await fetch(url);
        if (!r.ok) throw new Error(`${url}: ${r.status}`);
        return r.json();
    }

    // ---------- Predicciones ----------
    function normPrediction(p, i) {
        const base = {
            i, id: p.match_id || '', home: p.home_team, away: p.away_team,
            homeLogo: logo(p.home_team, p.home_logo), awayLogo: logo(p.away_team, p.away_logo),
            homeAbbr: abbr(p.home_team), awayAbbr: abbr(p.away_team),
            oddsHome: p.odds_home ? Number(p.odds_home) : null, oddsAway: p.odds_away ? Number(p.odds_away) : null,
            ev: Number(p.ev_score) || 0, risk: p.warning_level === 'HIGH', analysis: p.ai_analysis || '',
            boost: p.confidence_modifier || null, date: p.date || null, raw: p
        };
        if (state.sport === 'football') {
            const probs = { home: p.probs?.home || 0, draw: p.probs?.draw || 0, away: p.probs?.away || 0 };
            const side = p.prediction === p.home_team || p.prediction === '1' ? 'home'
                : p.prediction === p.away_team || p.prediction === '2' ? 'away' : 'draw';
            return { ...base, probs, side, pick: side === 'home' ? p.home_team : side === 'away' ? p.away_team : 'Empate', prob: probs[side] };
        }
        const side = p.winner === p.home_team ? 'home' : 'away';
        return { ...base, side, pick: p.winner, prob: Number(p.win_probability) || 0 };
    }

    async function predictions() {
        const data = await getJSON(state.sport === 'football' ? '/predict-football' : '/predict-today');
        const list = (data.predictions || []).map(normPrediction);
        return { date: data.date || null, list };
    }

    // ---------- Historial ----------
    function normHistory(h) {
        let home = h.home_team, away = h.away_team;
        if (!home || !away) {
            const parts = String(h.match || h.match_id || '').split(' vs ');
            home = home || parts[0]?.trim() || 'Local';
            away = away || parts[1]?.trim() || 'Visita';
        }
        let pick = h.predicted_winner || h.winner || h.prediction || '-';
        let prob = h.prob_model ? h.prob_model * 100 : (h.win_probability || h.probability || 0);
        if (state.sport === 'football' && h.prediction) {
            const side = { '1': 'home', '2': 'away', 'X': 'draw' }[h.prediction];
            if (side) pick = side === 'home' ? home : side === 'away' ? away : 'Empate';
            if (side && h.probs && !h.prob_model) prob = h.probs[side] || 0;
        }
        const r = String(h.result || 'pending').toLowerCase();
        return {
            date: h.date, home, away, pick, prob: Number(prob) || 0,
            result: r === 'win' || r === 'loss' ? r : 'pending',
            homeScore: h.home_score ?? null, awayScore: h.away_score ?? null, ev: Number(h.ev) || 0,
            homeLogo: logo(home, h.home_logo), awayLogo: logo(away, h.away_logo),
            homeAbbr: abbr(home), awayAbbr: abbr(away)
        };
    }

    async function history() {
        const data = await getJSON(state.sport === 'football' ? '/history/football?days=60' : '/history/full?days=365');
        return (data.history || []).map(normHistory).sort((a, b) => (a.date < b.date ? 1 : -1));
    }

    // Récord, acierto, racha y forma reciente (lista ya ordenada de más nueva a más vieja)
    function stats(hist) {
        const settled = hist.filter(h => h.result !== 'pending');
        const wins = settled.filter(h => h.result === 'win').length;
        let streak = 0;
        for (const h of settled) { if (h.result === settled[0].result) streak++; else break; }
        return {
            wins, losses: settled.length - wins, pending: hist.length - settled.length,
            rate: settled.length ? wins / settled.length * 100 : 0,
            streak, streakType: settled[0]?.result || null,
            form: settled.slice(0, 20).map(h => h.result)
        };
    }

    // Acierto acumulado en orden cronológico, para dibujar una curva
    // (los primeros `skip` puntos se descartan: con pocos partidos el % salta de 0 a 100)
    function rateCurve(hist, points = 60, skip = 20) {
        const settled = hist.filter(h => h.result !== 'pending').reverse();
        let w = 0;
        const all = settled.map((h, n) => (w += h.result === 'win', w / (n + 1) * 100)).slice(Math.min(skip, Math.max(0, settled.length - 2)));
        const step = Math.max(1, Math.floor(all.length / points));
        return all.filter((_, n) => n % step === 0 || n === all.length - 1);
    }

    // ---------- Apuestas ----------
    async function recommendations() {
        const [today, hist] = await Promise.all([
            getJSON('/api/recommendations/today').catch(() => ({ recommendations: [] })),
            getJSON('/api/recommendations/history').catch(() => ({ history: [] }))
        ]);
        return { today, history: hist.history || [] };
    }

    const news = matchId => getJSON(`/api/news/${encodeURIComponent(matchId)}`).catch(() => ({ found: false }));

    // ---------- Ajustes públicos ----------
    async function loadSettings(onFootballOff) {
        try {
            state.settings = { ...state.settings, ...(await getJSON('/api/settings')) };
        } catch (e) { console.warn('Sin ajustes públicos:', e); }
        const b = state.settings.branding || {};
        const title = (b.title || '').trim() || 'La Fija';
        document.title = b.subtitle ? `${title} — ${b.subtitle}` : `${title} - Predicciones`;
        document.querySelectorAll('[data-brand]').forEach(el => el.textContent = title);
        document.querySelectorAll('[data-brand-emoji]').forEach(el => {
            const e = b.emoji != null ? String(b.emoji).trim() : '';
            el.textContent = e; el.hidden = !e;
        });
        const football = state.settings.features?.football === true;
        document.querySelectorAll('[data-sport="football"]').forEach(el => el.hidden = !football);
        if (!football && state.sport === 'football') { state.sport = 'nba'; onFootballOff?.(); }
        const ann = state.settings.announcement || {};
        const bar = document.querySelector('[data-announcement]');
        if (bar && ann.enabled && ann.text) {
            bar.textContent = ann.text;
            bar.style.setProperty('--ann', ann.color || '');
            bar.hidden = false;
        }
        if (!readTheme()) setTheme(state.settings.features?.dark_default ? 'dark' : 'light', false);
        const ads = state.settings.ads || {};
        if (ads.enabled) {
            for (const side of ['left', 'right']) {
                const key = (ads[`${side}_key`] || '').trim();
                if (key) await injectAd(document.querySelector(`[data-ad="${side}"]`), key);
            }
        }
        return state.settings;
    }

    // Adsterra usa un global atOptions por banner: hay que cargarlos uno detrás de otro
    function injectAd(slot, key) {
        if (!slot) return;
        slot.innerHTML = '';
        slot.classList.add('filled');
        return new Promise(resolve => {
            window.atOptions = { key, format: 'iframe', height: 600, width: 160, params: {} };
            const s = document.createElement('script');
            s.src = `https://www.highperformanceformat.com/${key}/invoke.js`;
            s.onload = s.onerror = resolve;
            slot.appendChild(s);
        });
    }

    const betting = () => ({ currency: 'COP', currency_symbol: '$', default_stake: 50000, ...(state.settings.betting || {}) });
    const promoEnabled = () => state.settings.features?.promo_download === true;

    function promoUrl(home, away, winner, probability, status) {
        const params = { home_team: home, away_team: away, winner, probability: String(probability) };
        if (status === 'win') params.status = 'GANADA';
        if (status === 'loss') params.status = 'PERDIDA';
        return '/api/promo-image?' + new URLSearchParams(params);
    }

    // ---------- Tema ----------
    function readTheme() { try { return localStorage.getItem('theme'); } catch { return null; } }
    function setTheme(theme, persist = true) {
        document.documentElement.setAttribute('data-theme', theme);
        if (persist) try { localStorage.setItem('theme', theme); } catch { }
    }
    const toggleTheme = () => setTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
    if (readTheme()) setTheme(readTheme(), false);

    // ---------- Formato ----------
    const money = n => `${betting().currency_symbol}${Number(n).toLocaleString('es-CO', { maximumFractionDigits: 0 })}`;
    const pct = (n, d = 1) => Number(n).toLocaleString('es-CO', { minimumFractionDigits: d, maximumFractionDigits: d });
    const day = (d, opts = { weekday: 'long', day: 'numeric', month: 'long' }) =>
        new Date(d + 'T12:00:00').toLocaleDateString('es-ES', opts);
    const cap = s => s.charAt(0).toUpperCase() + s.slice(1);
    const bogota = (opts = { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }) =>
        new Date().toLocaleTimeString('es-CO', { timeZone: 'America/Bogota', ...opts });
    const todayBogota = () => new Date().toLocaleDateString('en-CA', { timeZone: 'America/Bogota' });

    // ---------- Movimiento ----------
    // fmt devuelve HTML: solo pasarle números ya formateados, nunca texto externo
    function countUp(el, to, decimals = 0, ms = 1200, fmt = v => pct(v, decimals)) {
        if (reducedMotion) { el.innerHTML = fmt(to); return; }
        const t0 = performance.now();
        const tick = t => {
            const k = Math.min(1, (t - t0) / ms);
            el.innerHTML = fmt(to * (1 - Math.pow(1 - k, 4)));
            if (k < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
    }

    // Añade .in cuando el elemento entra en pantalla
    const io = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
        entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -8% 0px' }) : null;
    const reveal = root => (root || document).querySelectorAll('.rv:not(.in)').forEach(el => io ? io.observe(el) : el.classList.add('in'));

    return {
        state, esc, logo, abbr, short, predictions, history, stats, rateCurve, recommendations, news,
        loadSettings, betting, promoEnabled, promoUrl, setTheme, toggleTheme, money, pct, day, cap,
        bogota, todayBogota, countUp, reveal, reducedMotion
    };
})();
