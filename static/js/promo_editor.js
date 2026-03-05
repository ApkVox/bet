const TOKEN_KEY = "admin_token";

function $(id) {
    return document.getElementById(id);
}

function getAuthHeaders() {
    const token = localStorage.getItem(TOKEN_KEY);
    return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchJSONAuthed(url, options = {}) {
    const res = await fetch(url, {
        headers: {
            "Content-Type": "application/json",
            ...getAuthHeaders(),
            ...(options.headers || {}),
        },
        ...options,
    });

    if (res.status === 401) {
        $("statusMsg").textContent = "Sesión expirada o ausente. Redirigiendo a /admin…";
        const top = window.top || window;
        setTimeout(() => (top.location.href = "/admin"), 900);
        throw new Error("No autenticado");
    }

    let data = null;
    try {
        data = await res.json();
    } catch (_) {
        data = null;
    }
    if (!res.ok) {
        const detail = data && (data.detail || data.message);
        throw new Error(detail || `Error HTTP ${res.status}`);
    }
    return data;
}

function updateSliderValue(id) {
    const el = $(id);
    const valEl = $(id + "_val");
    if (el && valEl) {
        valEl.textContent = el.value;
    }
}

function getParams() {
    return {
        home_team: $("test_home").value,
        away_team: $("test_away").value,
        winner: $("test_winner").value,
        probability: parseFloat($("test_prob").value) || 0,
        logo_cy: parseInt($("logo_cy").value),
        logo_left_cx: parseInt($("logo_left_cx").value),
        logo_right_offset: parseInt($("logo_right_offset").value),
        logo_max: parseInt($("logo_max").value),
        names_y: parseInt($("names_y").value),
        names_font_size: parseInt($("names_font_size").value),
        names_max_w: parseInt($("names_max_w").value),
        names_color: $("names_color").value,
        box_y0: parseInt($("box_y0").value),
        box_y1: parseInt($("box_y1").value),
        box_pad_x: parseInt($("box_pad_x").value),
        box_radius: parseInt($("box_radius").value),
        box_border_w: parseInt($("box_border_w").value),
        box_border_color: $("box_border_color").value,
        label_offset_y: parseInt($("label_offset_y").value),
        label_font_size: parseInt($("label_font_size").value),
        label_color: $("label_color").value,
        winner_offset_y: parseInt($("winner_offset_y").value),
        winner_font_size: parseInt($("winner_font_size").value),
        winner_color: $("winner_color").value,
        prob_offset_y: parseInt($("prob_offset_y").value),
        prob_font_size: parseInt($("prob_font_size").value),
        prob_color: $("prob_color").value,
        footer_y: parseInt($("footer_y").value),
        footer_font_size: parseInt($("footer_font_size").value),
        footer_color: $("footer_color").value,
        show_logos: $("show_logos").checked,
        show_names: $("show_names").checked,
        show_box_border: $("show_box_border").checked,
        show_label: $("show_label").checked,
        show_winner: $("show_winner").checked,
        show_prob: $("show_prob").checked,
        show_footer: $("show_footer").checked,
    };
}

function updatePreview() {
    const params = getParams();
    const qs = new URLSearchParams(params).toString();
    $("preview-img").src = `/api/promo-editor-preview?${qs}&_t=${Date.now()}`;
}

async function saveConfig() {
    const params = getParams();
    const cfg = { ...params };
    delete cfg.home_team;
    delete cfg.away_team;
    delete cfg.winner;
    delete cfg.probability;

    try {
        $("statusMsg").textContent = "Guardando configuración…";
        await fetchJSONAuthed("/api/promo-config", {
            method: "POST",
            body: JSON.stringify(cfg),
        });
        $("statusMsg").textContent = "Configuración guardada correctamente.";
    } catch (err) {
        $("statusMsg").textContent = err.message || "No se pudo guardar la configuración.";
    }
}

function resetDefaults() {
    const defaults = {
        logo_cy: 240,
        logo_left_cx: 88,
        logo_right_offset: 88,
        logo_max: 68,
        names_y: 308,
        names_font_size: 11,
        names_max_w: 120,
        names_color: "#373737",
        box_y0: 405,
        box_y1: 590,
        box_pad_x: 28,
        box_radius: 14,
        box_border_w: 2,
        box_border_color: "#beb9aa",
        label_offset_y: 18,
        label_font_size: 11,
        label_color: "#9b968c",
        winner_offset_y: 50,
        winner_font_size: 20,
        winner_color: "#0069e1",
        prob_offset_y: 100,
        prob_font_size: 52,
        prob_color: "#1e1e1e",
        footer_y: 642,
        footer_font_size: 10,
        footer_color: "#b9b4aa",
        show_logos: true,
        show_names: true,
        show_box_border: true,
        show_label: true,
        show_winner: true,
        show_prob: true,
        show_footer: true,
    };

    Object.entries(defaults).forEach(([key, val]) => {
        const el = $(key);
        if (!el) return;
        if (typeof val === "boolean") {
            el.checked = val;
        } else {
            el.value = val;
        }
        if (el.type === "range") {
            updateSliderValue(key);
        }
    });
    updatePreview();
    $("statusMsg").textContent = "Valores restaurados a los defaults.";
}

async function loadConfig() {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
        $("authWarning").style.display = "block";
        $("statusMsg").textContent = "Inicia sesión en /admin para editar esta configuración.";
        return;
    }

    $("authWarning").style.display = "none";
    $("statusMsg").textContent = "Cargando configuración…";

    try {
        const cfg = await fetchJSONAuthed("/api/promo-config", { method: "GET" });
        const entries = Object.entries(cfg || {});
        entries.forEach(([key, val]) => {
            const el = $(key);
            if (!el) return;
            if (typeof val === "boolean") {
                el.checked = val;
            } else if (el.type === "range" || el.type === "number") {
                el.value = val;
            } else {
                el.value = val;
            }
            if (el.type === "range") {
                updateSliderValue(key);
            }
        });
        $("statusMsg").textContent = "Configuración cargada.";
        updatePreview();
    } catch (err) {
        $("statusMsg").textContent = err.message || "No se pudo cargar la configuración.";
    }
}

function wireSliders() {
    const ids = [
        "logo_cy", "logo_left_cx", "logo_right_offset", "logo_max",
        "names_y", "names_font_size", "names_max_w",
        "box_y0", "box_y1", "box_pad_x", "box_radius", "box_border_w",
        "label_offset_y", "label_font_size",
        "winner_offset_y", "winner_font_size",
        "prob_offset_y", "prob_font_size",
        "footer_y", "footer_font_size",
    ];
    ids.forEach((id) => {
        const el = $(id);
        if (!el) return;
        el.addEventListener("input", () => {
            updateSliderValue(id);
            updatePreview();
        });
        updateSliderValue(id);
    });

    const colors = ["names_color", "box_border_color", "label_color", "winner_color", "prob_color", "footer_color"];
    colors.forEach((id) => {
        const el = $(id);
        if (!el) return;
        el.addEventListener("input", updatePreview);
    });

    const toggles = [
        "show_logos",
        "show_names",
        "show_box_border",
        "show_label",
        "show_winner",
        "show_prob",
        "show_footer",
    ];
    toggles.forEach((id) => {
        const el = $(id);
        if (!el) return;
        el.addEventListener("change", updatePreview);
    });

    ["test_home", "test_away", "test_winner", "test_prob"].forEach((id) => {
        const el = $(id);
        if (!el) return;
        el.addEventListener("input", updatePreview);
    });
}

function bootstrap() {
    wireSliders();
    loadConfig();
}

window.addEventListener("DOMContentLoaded", bootstrap);

