const TOKEN_KEY = "admin_token";
let authToken = localStorage.getItem(TOKEN_KEY) || "";
let settings = {};
let promoDebounce = null;

const COLOR_LABELS = {
    "--accent": "Color Acento",
    "--accent-hover": "Acento Hover",
    "--bg-primary": "Fondo Principal",
    "--bg-secondary": "Fondo Secundario",
    "--bg-card": "Fondo Tarjeta",
    "--bg-card-hover": "Tarjeta Hover",
    "--text-primary": "Texto Principal",
    "--text-secondary": "Texto Secundario",
    "--success": "Color Exito",
    "--danger": "Color Peligro",
    "--warning": "Color Alerta",
};

const PANEL_TITLES = {
    theme: "Tema y Colores",
    branding: "Branding",
    features: "Funcionalidades",
    announcement: "Anuncio",
    ads: "Publicidad",
    promo: "Editor Promo",
    security: "Seguridad",
};

const PROMO_FIELDS = [
    "logo_cy", "logo_left_cx", "logo_right_offset", "logo_max",
    "names_y", "names_font_size", "names_max_w", "names_color",
    "box_y0", "box_y1", "box_pad_x", "box_radius", "box_border_w", "box_border_color",
    "label_offset_y", "label_font_size", "label_color",
    "winner_offset_y", "winner_font_size", "winner_color",
    "prob_offset_y", "prob_font_size", "prob_color",
    "footer_y", "footer_font_size", "footer_color",
];

const PROMO_TOGGLES = [
    "show_logos", "show_names", "show_box_border", "show_label", "show_winner", "show_prob", "show_footer",
];

const PROMO_DEFAULTS = {
    logo_cy: 240, logo_left_cx: 88, logo_right_offset: 88, logo_max: 68,
    names_y: 308, names_font_size: 11, names_max_w: 120, names_color: "#373737",
    box_y0: 405, box_y1: 590, box_pad_x: 28, box_radius: 14, box_border_w: 2, box_border_color: "#beb9aa",
    label_offset_y: 18, label_font_size: 11, label_color: "#9b968c",
    winner_offset_y: 50, winner_font_size: 20, winner_color: "#0069e1",
    prob_offset_y: 100, prob_font_size: 52, prob_color: "#1e1e1e",
    footer_y: 642, footer_font_size: 10, footer_color: "#b9b4aa",
    show_logos: true, show_names: true, show_box_border: true,
    show_label: true, show_winner: true, show_prob: true, show_footer: true,
};

function getEl(id) {
    return document.getElementById(id);
}

function showToast(msg, type = "info") {
    const container = getEl("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    const icons = { success: "OK", error: "!", info: "i" };
    toast.innerHTML = `<span>${icons[type] || "i"}</span><span>${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateX(20px)";
        toast.style.transition = "all 0.3s";
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function setLoginError(msg) {
    const box = getEl("loginError");
    box.textContent = msg;
    box.style.display = msg ? "block" : "none";
}

function setResetError(msg) {
    const box = getEl("resetError");
    box.textContent = msg;
    box.style.display = msg ? "block" : "none";
}

async function parseApiError(res) {
    let msg = `Error HTTP ${res.status}`;
    try {
        const payload = await res.json();
        if (payload && payload.detail) msg = payload.detail;
    } catch (_) {
        try {
            const text = await res.text();
            if (text) msg = text;
        } catch (_) { }
    }
    return msg;
}

async function apiRequest(url, { method = "GET", body = null, auth = true } = {}) {
    const headers = {};
    if (body !== null) headers["Content-Type"] = "application/json";
    if (auth && authToken) headers["Authorization"] = `Bearer ${authToken}`;

    const res = await fetch(url, {
        method,
        headers,
        body: body !== null ? JSON.stringify(body) : undefined,
    });

    if (res.status === 401 && auth) {
        logout(false);
        throw new Error("Sesion expirada. Vuelve a iniciar sesion.");
    }
    if (!res.ok) throw new Error(await parseApiError(res));
    if (res.status === 204) return null;
    const contentType = res.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) return null;
    return await res.json();
}

function showLogin() {
    getEl("loginScreen").style.display = "flex";
    getEl("dashboard").classList.remove("active");
}

function showDashboard() {
    getEl("loginScreen").style.display = "none";
    getEl("dashboard").classList.add("active");
    getEl("sessionInfo").textContent = "Sesion activa";
}

function setAuthToken(token) {
    authToken = token || "";
    if (authToken) localStorage.setItem(TOKEN_KEY, authToken);
    else localStorage.removeItem(TOKEN_KEY);
}

async function loadSettings() {
    settings = await apiRequest("/api/admin/settings");
    populateAllFields();
}

function populateAllFields() {
    renderColorInputs("darkColorInputs", settings.theme?.dark || {}, "dark");
    renderColorInputs("lightColorInputs", settings.theme?.light || {}, "light");

    getEl("brandTitle").value = settings.branding?.title || "";
    getEl("brandEmoji").value = settings.branding?.emoji || "";
    getEl("brandSubtitle").value = settings.branding?.subtitle || "";

    getEl("featFootball").checked = !!settings.features?.football;
    getEl("featPromo").checked = settings.features?.promo_download ?? true;
    getEl("featDark").checked = settings.features?.dark_default ?? true;
    getEl("featAI").checked = settings.features?.ai_analysis ?? true;

    getEl("annEnabled").checked = !!settings.announcement?.enabled;
    getEl("annText").value = settings.announcement?.text || "";
    const annColor = settings.announcement?.color || "#0a84ff";
    getEl("annColorPicker").value = annColor;
    getEl("annColorText").value = annColor;
    updateAnnouncementPreview();

    getEl("adsEnabled").checked = settings.ads?.enabled ?? true;
    getEl("adsLeftKey").value = settings.ads?.left_key || "";
    getEl("adsRightKey").value = settings.ads?.right_key || "";
}

function renderColorInputs(containerId, colors, mode) {
    const container = getEl(containerId);
    container.innerHTML = "";
    for (const [varName, value] of Object.entries(colors)) {
        const label = COLOR_LABELS[varName] || varName;
        const div = document.createElement("div");
        div.className = "form-group";
        div.innerHTML = `
            <label>${label}</label>
            <div class="color-input-wrapper">
                <input type="color" value="${value}" data-mode="${mode}" data-var="${varName}" oninput="syncColorText(this)">
                <input type="text" value="${value}" data-mode="${mode}" data-var="${varName}" oninput="syncColorPicker(this)">
            </div>`;
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

function updateAnnouncementPreview() {
    const text = getEl("annText").value || "Vista previa del anuncio";
    const color = getEl("annColorText").value || "#0a84ff";
    const preview = getEl("annPreview");
    preview.textContent = text;
    preview.style.background = color;
}

function gatherSettings() {
    const theme = { dark: {}, light: {} };
    document.querySelectorAll('#darkColorInputs input[type="text"][data-var]').forEach((inp) => {
        theme.dark[inp.dataset.var] = inp.value;
    });
    document.querySelectorAll('#lightColorInputs input[type="text"][data-var]').forEach((inp) => {
        theme.light[inp.dataset.var] = inp.value;
    });

    return {
        theme,
        branding: {
            title: getEl("brandTitle").value,
            emoji: getEl("brandEmoji").value,
            subtitle: getEl("brandSubtitle").value,
        },
        features: {
            football: getEl("featFootball").checked,
            promo_download: getEl("featPromo").checked,
            dark_default: getEl("featDark").checked,
            ai_analysis: getEl("featAI").checked,
        },
        announcement: {
            enabled: getEl("annEnabled").checked,
            text: getEl("annText").value,
            color: getEl("annColorText").value,
        },
        ads: {
            enabled: getEl("adsEnabled").checked,
            left_key: getEl("adsLeftKey").value,
            right_key: getEl("adsRightKey").value,
        },
    };
}

async function saveSettings() {
    try {
        const payload = gatherSettings();
        await apiRequest("/api/admin/settings", { method: "POST", body: payload });
        settings = { ...settings, ...payload };
        showToast("Configuracion guardada correctamente", "success");
    } catch (err) {
        showToast(err.message || "No se pudo guardar", "error");
    }
}

function resetThemeDefaults() {
    settings.theme = {
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
    renderColorInputs("darkColorInputs", settings.theme.dark, "dark");
    renderColorInputs("lightColorInputs", settings.theme.light, "light");
    showToast("Colores restaurados. Pulsa Guardar para aplicar.", "info");
}

async function changePassword() {
    const current = getEl("secCurrent").value;
    const next = getEl("secNew").value;
    if (next.length < 6) {
        showToast("La nueva contrasena debe tener al menos 6 caracteres", "error");
        return;
    }
    try {
        await apiRequest("/api/admin/password", {
            method: "POST",
            body: { current_password: current, new_password: next },
        });
        getEl("secCurrent").value = "";
        getEl("secNew").value = "";
        showToast("Contrasena actualizada", "success");
    } catch (err) {
        showToast(err.message || "No se pudo actualizar", "error");
    }
}

function pSlider(el) {
    const valEl = getEl(el.id + "_v");
    if (valEl) valEl.textContent = el.value;
    clearTimeout(promoDebounce);
    promoDebounce = setTimeout(updatePromoPreview, 450);
}

function getPromoParams() {
    const p = {
        home_team: getEl("promo_test_home").value,
        away_team: getEl("promo_test_away").value,
        winner: getEl("promo_test_winner").value,
        probability: parseFloat(getEl("promo_test_prob").value),
    };
    PROMO_FIELDS.forEach((f) => {
        const el = getEl("p_" + f);
        if (!el) return;
        p[f] = el.type === "color" ? el.value : parseInt(el.value, 10);
    });
    PROMO_TOGGLES.forEach((f) => {
        const el = getEl("p_" + f);
        if (el) p[f] = el.checked;
    });
    return p;
}

function updatePromoPreview() {
    const params = getPromoParams();
    const qs = new URLSearchParams(params).toString();
    getEl("promoPreviewImg").src = `/api/promo-editor-preview?${qs}&_t=${Date.now()}`;
}

async function savePromoConfig() {
    const params = getPromoParams();
    const config = {};
    PROMO_FIELDS.forEach((f) => {
        if (params[f] !== undefined) config[f] = params[f];
    });
    PROMO_TOGGLES.forEach((f) => {
        if (params[f] !== undefined) config[f] = params[f];
    });
    try {
        await apiRequest("/api/promo-config", { method: "POST", body: config });
        showToast("Configuracion de promo guardada", "success");
    } catch (err) {
        showToast(err.message || "No se pudo guardar promo", "error");
    }
}

async function loadPromoConfig() {
    try {
        const config = await apiRequest("/api/promo-config");
        PROMO_FIELDS.forEach((f) => {
            const el = getEl("p_" + f);
            if (!el || config[f] === undefined) return;
            el.value = config[f];
            const valueEl = getEl("p_" + f + "_v");
            if (valueEl) valueEl.textContent = config[f];
        });
        PROMO_TOGGLES.forEach((f) => {
            const el = getEl("p_" + f);
            if (!el || config[f] === undefined) return;
            el.checked = config[f] === true || config[f] === "true";
        });
    } catch (_) {
        showToast("No se pudo cargar la configuracion de promo", "error");
    }
    updatePromoPreview();
}

function resetPromoDefaults() {
    PROMO_FIELDS.forEach((f) => {
        const el = getEl("p_" + f);
        if (!el || PROMO_DEFAULTS[f] === undefined) return;
        el.value = PROMO_DEFAULTS[f];
        const valueEl = getEl("p_" + f + "_v");
        if (valueEl) valueEl.textContent = PROMO_DEFAULTS[f];
    });
    PROMO_TOGGLES.forEach((f) => {
        const el = getEl("p_" + f);
        if (el) el.checked = true;
    });
    updatePromoPreview();
    showToast("Valores de promo restaurados", "info");
}

function logout(reload = true) {
    setAuthToken("");
    if (reload) window.location.href = "/admin";
    else showLogin();
}

async function handleLoginSubmit(ev) {
    ev.preventDefault();
    setLoginError("");
    const btn = getEl("loginBtn");
    btn.disabled = true;
    try {
        const password = getEl("loginPassword").value || "";
        const data = await apiRequest("/api/admin/login", {
            method: "POST",
            body: { password },
            auth: false,
        });
        if (!data?.token) throw new Error("Respuesta de login invalida");
        setAuthToken(data.token);
        await loadSettings();
        showDashboard();
    } catch (err) {
        const msg = err.message || "No se pudo iniciar sesion";
        setLoginError(msg);
    } finally {
        btn.disabled = false;
    }
}

async function handleSetInitialPassword() {
    const p1 = getEl("initialPassword").value || "";
    const p2 = getEl("initialPasswordConfirm").value || "";
    if (p1.length < 6) {
        setLoginError("La contrasena debe tener al menos 6 caracteres");
        return;
    }
    if (p1 !== p2) {
        setLoginError("Las contrasenas no coinciden");
        return;
    }
    try {
        await apiRequest("/api/admin/set-initial-password", {
            method: "POST",
            body: { password: p1 },
            auth: false,
        });
        setLoginError("");
        showToast("Contrasena inicial creada. Ya puedes iniciar sesion.", "success");
        getEl("setInitialPasswordBlock").style.display = "none";
        getEl("loginForm").style.display = "block";
    } catch (err) {
        setLoginError(err.message || "No se pudo crear la contrasena inicial");
    }
}

async function refreshInitialPasswordState() {
    try {
        const data = await apiRequest("/api/admin/needs-initial-password", { auth: false });
        const needs = !!data?.needs_initial_password;
        getEl("setInitialPasswordBlock").style.display = needs ? "block" : "none";
        getEl("loginForm").style.display = needs ? "none" : "block";
    } catch (_) {
        getEl("setInitialPasswordBlock").style.display = "none";
        getEl("loginForm").style.display = "block";
    }
}

function setupNavigation() {
    document.querySelectorAll(".nav-item[data-panel]").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".nav-item").forEach((n) => n.classList.remove("active"));
            btn.classList.add("active");
            document.querySelectorAll(".settings-panel").forEach((p) => p.classList.remove("active"));
            getEl(`panel-${btn.dataset.panel}`).classList.add("active");
            getEl("panelTitle").textContent = PANEL_TITLES[btn.dataset.panel] || "Panel";
            if (btn.dataset.panel === "promo") loadPromoConfig();
        });
    });
}

async function setupForgotPassword() {
    getEl("forgotPasswordLink").addEventListener("click", async (ev) => {
        ev.preventDefault();
        getEl("loginForm").style.display = "none";
        getEl("setInitialPasswordBlock").style.display = "none";
        getEl("forgotPasswordBlock").style.display = "block";
        try {
            const status = await apiRequest("/api/admin/email-recovery-status", { auth: false });
            const hint = getEl("emailRecoveryHint");
            if (status?.hint) {
                hint.style.display = "block";
                hint.textContent = status.hint;
            } else {
                hint.style.display = "none";
                hint.textContent = "";
            }
        } catch (_) { }
    });

    getEl("backToLoginLink").addEventListener("click", async (ev) => {
        ev.preventDefault();
        getEl("forgotPasswordBlock").style.display = "none";
        await refreshInitialPasswordState();
    });

    getEl("sendResetBtn").addEventListener("click", async () => {
        const email = (getEl("forgotEmail").value || "").trim();
        if (!email) {
            setLoginError("Debes indicar el correo del administrador");
            return;
        }
        try {
            await apiRequest("/api/admin/forgot-password", {
                method: "POST",
                body: { email },
                auth: false,
            });
            setLoginError("");
            showToast("Si el correo es valido, se envio un enlace de recuperacion", "success");
        } catch (err) {
            setLoginError(err.message || "No se pudo enviar el correo");
        }
    });
}

async function handleResetByTokenIfPresent() {
    const params = new URLSearchParams(window.location.search);
    const token = (params.get("reset") || "").trim();
    if (!token) return false;

    getEl("loginCard").style.display = "none";
    getEl("resetPasswordCard").style.display = "block";

    getEl("resetPasswordForm").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        setResetError("");
        const a = getEl("resetNewPassword").value || "";
        const b = getEl("resetConfirmPassword").value || "";
        if (a.length < 6) {
            setResetError("La contrasena debe tener al menos 6 caracteres");
            return;
        }
        if (a !== b) {
            setResetError("Las contrasenas no coinciden");
            return;
        }
        try {
            await apiRequest("/api/admin/reset-password", {
                method: "POST",
                body: { token, new_password: a },
                auth: false,
            });
            showToast("Contrasena restablecida. Inicia sesion.", "success");
            window.location.href = "/admin";
        } catch (err) {
            setResetError(err.message || "No se pudo restablecer la contrasena");
        }
    });
    return true;
}

async function bootstrap() {
    setupNavigation();

    getEl("loginForm").addEventListener("submit", handleLoginSubmit);
    getEl("setInitialPasswordBtn").addEventListener("click", handleSetInitialPassword);

    getEl("annColorPicker").addEventListener("input", function () {
        getEl("annColorText").value = this.value;
        updateAnnouncementPreview();
    });
    getEl("annColorText").addEventListener("input", function () {
        if (/^#[0-9a-fA-F]{6}$/.test(this.value)) getEl("annColorPicker").value = this.value;
        updateAnnouncementPreview();
    });
    getEl("annText").addEventListener("input", updateAnnouncementPreview);

    await setupForgotPassword();
    const inReset = await handleResetByTokenIfPresent();
    if (inReset) return;

    await refreshInitialPasswordState();

    if (!authToken) {
        showLogin();
        return;
    }

    try {
        await loadSettings();
        showDashboard();
    } catch (err) {
        showLogin();
        setLoginError(err.message || "No se pudo cargar el panel");
    }
}

window.logout = logout;
window.saveSettings = saveSettings;
window.resetThemeDefaults = resetThemeDefaults;
window.changePassword = changePassword;
window.syncColorText = syncColorText;
window.syncColorPicker = syncColorPicker;
window.pSlider = pSlider;
window.updatePromoPreview = updatePromoPreview;
window.savePromoConfig = savePromoConfig;
window.loadPromoConfig = loadPromoConfig;
window.resetPromoDefaults = resetPromoDefaults;

bootstrap();
