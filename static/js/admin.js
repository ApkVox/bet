const TOKEN_KEY = "admin_token";
let authToken = localStorage.getItem(TOKEN_KEY) || "";
let settings = {};

const COLOR_LABELS = {
    "--accent": "Acento",
    "--accent-hover": "Acento Hover",
    "--bg-primary": "Fondo Principal",
    "--bg-secondary": "Fondo Secundario",
    "--bg-card": "Fondo Tarjeta",
    "--bg-card-hover": "Tarjeta Hover",
    "--text-primary": "Texto Principal",
    "--text-secondary": "Texto Secundario",
    "--success": "Éxito",
    "--danger": "Peligro",
    "--warning": "Alerta",
};

const DEFAULT_THEME = {
    dark: {
        "--accent": "#0a84ff", "--accent-hover": "#409cff",
        "--bg-primary": "#0a0a0a", "--bg-secondary": "#141414",
        "--bg-card": "#1a1a1a", "--bg-card-hover": "#222222",
        "--text-primary": "#f5f5f7", "--text-secondary": "#8e8e93",
        "--success": "#30d158", "--danger": "#ff453a", "--warning": "#ff9f0a",
    },
    light: {
        "--accent": "#0071e3", "--accent-hover": "#0077ed",
        "--bg-primary": "#f5f5f7", "--bg-secondary": "#ffffff",
        "--bg-card": "#ffffff", "--bg-card-hover": "#fafafa",
        "--text-primary": "#1d1d1f", "--text-secondary": "#86868b",
        "--success": "#34c759", "--danger": "#ff3b30", "--warning": "#ff9500",
    },
};

function $(id) { return document.getElementById(id); }

function toast(msg, type = "info") {
    const box = $("toastBox");
    const t = document.createElement("div");
    t.className = `toast ${type}`;
    t.textContent = msg;
    box.appendChild(t);
    setTimeout(() => { t.style.opacity = "0"; t.style.transform = "translateX(16px)"; t.style.transition = "all 0.3s"; setTimeout(() => t.remove(), 300); }, 3200);
}

async function api(url, opts = {}) {
    const headers = {};
    if (opts.body) headers["Content-Type"] = "application/json";
    if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
    Object.assign(headers, opts.headers || {});

    const res = await fetch(url, { method: opts.method || "GET", headers, body: opts.body ? JSON.stringify(opts.body) : undefined });
    let data = null;
    try { data = await res.json(); } catch (_) {}

    if (res.status === 401) {
        logout();
        throw new Error("Sesión expirada. Inicia sesión de nuevo.");
    }
    if (!res.ok) {
        const detail = data && (data.detail || data.message);
        throw new Error(detail || `Error HTTP ${res.status}`);
    }
    return data;
}

/* ═══════ LOGIN ═══════ */

function setLoginTab(which) {
    const isCreate = which === "create";
    $("tabCreate").classList.toggle("active", isCreate);
    $("tabLogin").classList.toggle("active", !isCreate);
    $("panelCreate").classList.toggle("active", isCreate);
    $("panelLogin").classList.toggle("active", !isCreate);
}

function setLoginMsg(elId, text, isError) {
    const el = $(elId);
    el.textContent = text || "";
    el.style.color = isError ? "var(--danger)" : "var(--success)";
}

async function checkAdminStatus() {
    try {
        const data = await api("/api/admin/status", { headers: {} });
        if (data.has_admin) {
            $("statusText").innerHTML = 'Cuenta existente. Usa <span>Iniciar sesión</span>.';
            $("tabCreate").disabled = true;
            setLoginTab("login");
        } else {
            $("statusText").innerHTML = 'Primera vez. Crea la <span>cuenta inicial</span>.';
            $("tabLogin").disabled = true;
            setLoginTab("create");
        }
    } catch (err) {
        $("statusText").textContent = `Error: ${err.message}`;
    }
}

async function handleCreate() {
    const p1 = $("createPwd").value || "";
    const p2 = $("createPwd2").value || "";
    if (p1.length < 6) { setLoginMsg("createMsg", "Mínimo 6 caracteres.", true); return; }
    if (p1 !== p2) { setLoginMsg("createMsg", "Las contraseñas no coinciden.", true); return; }
    try {
        await api("/api/admin/create-initial", { method: "POST", body: { password: p1 }, headers: {} });
        setLoginMsg("createMsg", "Cuenta creada. Inicia sesión.", false);
        $("createPwd").value = ""; $("createPwd2").value = "";
        $("tabCreate").disabled = true; $("tabLogin").disabled = false;
        setLoginTab("login");
    } catch (err) { setLoginMsg("createMsg", err.message, true); }
}

async function handleLogin() {
    const pwd = $("loginPwd").value || "";
    if (!pwd) { setLoginMsg("loginMsg", "Ingresa tu contraseña.", true); return; }
    try {
        const data = await api("/api/admin/login", { method: "POST", body: { password: pwd }, headers: {} });
        if (!data.token) throw new Error("Respuesta inválida.");
        authToken = data.token;
        localStorage.setItem(TOKEN_KEY, authToken);
        $("loginPwd").value = "";
        enterDashboard();
    } catch (err) { setLoginMsg("loginMsg", err.message, true); }
}

/* ═══════ NAVIGATION ═══════ */

function showLogin() {
    $("loginScreen").style.display = "flex";
    $("app").classList.remove("active");
}

function enterDashboard() {
    $("loginScreen").style.display = "none";
    $("app").classList.add("active");
    loadAllSettings();
    loadDashboardStats();
}

function navTo(sec) {
    document.querySelectorAll(".nav-btn[data-sec]").forEach(b => b.classList.remove("active"));
    const btn = document.querySelector(`.nav-btn[data-sec="${sec}"]`);
    if (btn) btn.classList.add("active");
    document.querySelectorAll(".sec").forEach(s => s.classList.remove("active"));
    const panel = $(`sec-${sec}`);
    if (panel) panel.classList.add("active");

    if (sec === "promo") {
        const frame = $("promoFrame");
        const currentSrc = frame.getAttribute("src");
        if (!currentSrc || currentSrc === "" || currentSrc === "about:blank") {
            frame.src = "/promo-editor";
        }
    }
}

function logout() {
    authToken = "";
    localStorage.removeItem(TOKEN_KEY);
    showLogin();
    checkAdminStatus();
}

/* ═══════ LOAD SETTINGS ═══════ */

async function loadAllSettings() {
    try {
        settings = await api("/api/admin/settings");
        populateAll();
    } catch (err) {
        toast(err.message || "No se pudo cargar la configuración.", "err");
    }
}

function populateAll() {
    // Branding
    $("brandTitle").value = settings.branding?.title || "";
    $("brandEmoji").value = settings.branding?.emoji || "";
    $("brandSubtitle").value = settings.branding?.subtitle || "";

    // Theme
    renderColorInputs("darkColors", settings.theme?.dark || {}, "dark");
    renderColorInputs("lightColors", settings.theme?.light || {}, "light");

    // Features
    $("featFootball").checked = !!settings.features?.football;
    $("featPromo").checked = settings.features?.promo_download ?? true;
    $("featDark").checked = settings.features?.dark_default ?? true;
    $("featAI").checked = settings.features?.ai_analysis ?? true;

    // Announcement
    $("annEnabled").checked = !!settings.announcement?.enabled;
    $("annText").value = settings.announcement?.text || "";
    const annColor = settings.announcement?.color || "#0a84ff";
    $("annColorPick").value = annColor;
    $("annColorHex").value = annColor;
    updateAnnPreview();

    // Ads
    $("adsEnabled").checked = settings.ads?.enabled ?? true;
    $("adsLeft").value = settings.ads?.left_key || "";
    $("adsRight").value = settings.ads?.right_key || "";

    // Betting
    const bet = settings.betting || {};
    if ($("betCurrency")) $("betCurrency").value = bet.currency || "COP";
    if ($("betCurrencySymbol")) $("betCurrencySymbol").value = bet.currency_symbol || "$";
    if ($("betOddsFormat")) $("betOddsFormat").value = bet.odds_format || "decimal";
    if ($("betDefaultStake")) $("betDefaultStake").value = bet.default_stake || "50000";
}

function renderColorInputs(containerId, colors, mode) {
    const container = $(containerId);
    container.innerHTML = "";
    for (const [varName, value] of Object.entries(colors)) {
        const label = COLOR_LABELS[varName] || varName;
        const div = document.createElement("div");
        div.className = "fg";
        div.innerHTML = `<label>${label}</label><div class="color-wrap"><input type="color" value="${value}" data-mode="${mode}" data-var="${varName}" oninput="syncColorText(this)"><input type="text" value="${value}" data-mode="${mode}" data-var="${varName}" oninput="syncColorPicker(this)"></div>`;
        container.appendChild(div);
    }
}

function syncColorText(picker) {
    const text = picker.parentElement.querySelector('input[type="text"]');
    text.value = picker.value;
}
function syncColorPicker(text) {
    const picker = text.parentElement.querySelector('input[type="color"]');
    if (/^#[0-9a-fA-F]{6}$/.test(text.value)) picker.value = text.value;
}

function updateAnnPreview() {
    const text = $("annText").value || "Vista previa del anuncio";
    const color = $("annColorHex").value || "#0a84ff";
    const preview = $("annPreview");
    preview.textContent = text;
    preview.style.background = color;
}

/* ═══════ GATHER & SAVE ═══════ */

function gatherSettings() {
    const theme = { dark: {}, light: {} };
    document.querySelectorAll('#darkColors input[type="text"][data-var]').forEach(i => { theme.dark[i.dataset.var] = i.value; });
    document.querySelectorAll('#lightColors input[type="text"][data-var]').forEach(i => { theme.light[i.dataset.var] = i.value; });

    return {
        theme,
        branding: { title: $("brandTitle").value, emoji: $("brandEmoji").value, subtitle: $("brandSubtitle").value },
        features: { football: $("featFootball").checked, promo_download: $("featPromo").checked, dark_default: $("featDark").checked, ai_analysis: $("featAI").checked },
        announcement: { enabled: $("annEnabled").checked, text: ($("annText").value || "").slice(0, 500), color: $("annColorHex").value },
        ads: { enabled: $("adsEnabled").checked, left_key: $("adsLeft").value, right_key: $("adsRight").value },
        betting: {
            currency: $("betCurrency")?.value || "COP",
            currency_symbol: $("betCurrencySymbol")?.value || "$",
            odds_format: $("betOddsFormat")?.value || "decimal",
            default_stake: parseInt($("betDefaultStake")?.value) || 50000,
        },
    };
}

async function saveSettings() {
    try {
        const payload = gatherSettings();
        await api("/api/admin/settings", { method: "POST", body: payload });
        settings = { ...settings, ...payload };
        toast("Configuración guardada.", "ok");
    } catch (err) { toast(err.message, "err"); }
}

function resetTheme() {
    settings.theme = JSON.parse(JSON.stringify(DEFAULT_THEME));
    renderColorInputs("darkColors", settings.theme.dark, "dark");
    renderColorInputs("lightColors", settings.theme.light, "light");
    toast("Colores restaurados. Pulsa Guardar para aplicar.", "info");
}

/* ═══════ DASHBOARD STATS ═══════ */

async function loadDashboardStats() {
    try {
        const health = await api("/api/health", { headers: {} });
        $("dHealthVal").textContent = health.status === "online" ? "Online" : "Error";
    } catch (_) { $("dHealthVal").textContent = "Error"; }

    $("dBrandVal").textContent = settings.branding?.title || "La Fija";
    $("dFootballVal").textContent = settings.features?.football ? "Activo" : "Inactivo";

    try {
        const st = await api("/api/admin/status", { headers: {} });
        $("dTtlVal").textContent = `${st.token_ttl_hours ?? 1}h`;
    } catch (_) {}
}

async function handleRefreshHistory() {
    const msg = $("refreshMsg");
    msg.textContent = "Refrescando… esto puede tardar unos segundos.";
    try {
        const res = await api("/history/refresh", { method: "POST" });
        msg.textContent = res.message || "Historial actualizado.";
        toast("Historial refrescado.", "ok");
    } catch (err) {
        msg.textContent = err.message || "Error al refrescar.";
        toast(err.message, "err");
    }
}

/* ═══════ CHANGE PASSWORD ═══════ */

async function handleChangePwd() {
    const current = $("secCurrent").value;
    const next = $("secNew").value;
    if (next.length < 6) { toast("La nueva contraseña debe tener al menos 6 caracteres.", "err"); return; }
    try {
        await api("/api/admin/change-password", { method: "POST", body: { current_password: current, new_password: next } });
        $("secCurrent").value = ""; $("secNew").value = "";
        toast("Contraseña actualizada.", "ok");
    } catch (err) { toast(err.message, "err"); }
}

/* ═══════ BOOTSTRAP ═══════ */

function bootstrap() {
    // Login tabs
    $("tabCreate").addEventListener("click", () => { if (!$("tabCreate").disabled) setLoginTab("create"); });
    $("tabLogin").addEventListener("click", () => { if (!$("tabLogin").disabled) setLoginTab("login"); });
    $("btnCreate").addEventListener("click", handleCreate);
    $("btnLogin").addEventListener("click", handleLogin);

    // Login enter key
    $("loginPwd").addEventListener("keydown", e => { if (e.key === "Enter") handleLogin(); });
    $("createPwd2").addEventListener("keydown", e => { if (e.key === "Enter") handleCreate(); });

    // Sidebar navigation
    document.querySelectorAll(".nav-btn[data-sec]").forEach(btn => {
        btn.addEventListener("click", () => navTo(btn.dataset.sec));
    });

    // Logout
    $("btnLogout").addEventListener("click", logout);
    $("btnLogout2").addEventListener("click", logout);

    // Announcement preview
    $("annColorPick").addEventListener("input", function () { $("annColorHex").value = this.value; updateAnnPreview(); });
    $("annColorHex").addEventListener("input", function () { if (/^#[0-9a-fA-F]{6}$/.test(this.value)) $("annColorPick").value = this.value; updateAnnPreview(); });
    $("annText").addEventListener("input", updateAnnPreview);

    // Dashboard actions
    $("btnRefreshHistory").addEventListener("click", handleRefreshHistory);

    // Security
    $("btnChangePwd").addEventListener("click", handleChangePwd);

    // Check if already logged in
    if (authToken) {
        enterDashboard();
    } else {
        showLogin();
        checkAdminStatus();
    }
}

async function saveDeepSeekKey() {
    const key = ($("betDeepSeekKey")?.value || "").trim();
    if (!key) { toast("Ingresa una API key.", "err"); return; }
    try {
        await api("/api/admin/deepseek-key", { method: "POST", body: { key } });
        $("betDeepSeekKey").value = "";
        toast("API Key de DeepSeek guardada.", "ok");
    } catch (err) { toast(err.message, "err"); }
}

// Expose functions used by inline onclick
window.saveSettings = saveSettings;
window.resetTheme = resetTheme;
window.navTo = navTo;
window.syncColorText = syncColorText;
window.syncColorPicker = syncColorPicker;
window.saveDeepSeekKey = saveDeepSeekKey;

window.addEventListener("DOMContentLoaded", bootstrap);
