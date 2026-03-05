"""
===========================================
Site Settings (branding / theme / features)
===========================================

Módulo ligero para manejar la configuración pública del sitio:
- branding: título, subtítulo, emoji
- theme: colores light / dark
- features: toggles de funcionalidades
- announcement: banner superior
- ads: configuración de anuncios

Optimizado para Render: si el proyecto no es escribible, usa /tmp.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "site_settings.json"
_settings_path: Optional[Path] = None


DEFAULT_SETTINGS: Dict[str, Any] = {
    "theme": {
        "light": {
            "--accent": "#0071e3",
            "--accent-hover": "#0077ed",
            "--bg-primary": "#f5f5f7",
            "--bg-secondary": "#ffffff",
            "--bg-card": "#ffffff",
            "--bg-card-hover": "#fafafa",
            "--text-primary": "#1d1d1f",
            "--text-secondary": "#86868b",
            "--success": "#34c759",
            "--danger": "#ff3b30",
            "--warning": "#ff9500",
        },
        "dark": {
            "--accent": "#0a84ff",
            "--accent-hover": "#409cff",
            "--bg-primary": "#0a0a0a",
            "--bg-secondary": "#141414",
            "--bg-card": "#1a1a1a",
            "--bg-card-hover": "#222222",
            "--text-primary": "#f5f5f7",
            "--text-secondary": "#8e8e93",
            "--success": "#30d158",
            "--danger": "#ff453a",
            "--warning": "#ff9f0a",
        },
    },
    "branding": {
        "title": "La Fija",
        "subtitle": "Predicciones deportivas con IA",
        "emoji": "🏀",
    },
    "features": {
        "football": False,
        "promo_download": True,
        "dark_default": True,
        "ai_analysis": True,
    },
    "announcement": {
        "enabled": False,
        "text": "",
        "color": "#0a84ff",
    },
    "ads": {
        "enabled": True,
        "left_key": "",
        "right_key": "",
    },
    "betting": {
        "currency": "COP",
        "currency_symbol": "$",
        "odds_format": "decimal",
        "default_stake": 50000,
    },
}


def _get_settings_file() -> Path:
    """Devuelve la ruta del archivo de settings, con fallback a /tmp en Render."""
    global _settings_path
    if _settings_path is not None:
        return _settings_path

    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "a", encoding="utf-8"):
            pass
        _settings_path = SETTINGS_FILE
    except (OSError, PermissionError):
        _settings_path = Path("/tmp") / "lafija_site_settings.json"

    return _settings_path


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Fusiona override dentro de base de forma profunda."""
    result = base.copy()
    for key, value in (override or {}).items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_settings() -> Dict[str, Any]:
    """
    Carga la configuración desde JSON, fusionada con DEFAULT_SETTINGS.
    Si el archivo no existe o está corrupto, retorna defaults.
    """
    path = _get_settings_file()

    if not path.exists():
        save_settings(DEFAULT_SETTINGS.copy())
        return DEFAULT_SETTINGS.copy()

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return _deep_merge(DEFAULT_SETTINGS.copy(), data or {})
    except Exception:
        # En caso de error, no rompemos la app.
        return DEFAULT_SETTINGS.copy()


def save_settings(cfg: Dict[str, Any]) -> None:
    """Guarda la configuración completa en disco."""
    path = _get_settings_file()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get_public_settings() -> Dict[str, Any]:
    """
    Devuelve solo la parte pública consumida por el frontend.
    Actualmente toda la configuración es pública, pero se mantiene
    esta función por claridad y para poder ocultar campos en el futuro.
    """
    cfg = load_settings()
    return {
        "theme": cfg.get("theme", {}),
        "branding": cfg.get("branding", {}),
        "features": cfg.get("features", {}),
        "announcement": cfg.get("announcement", {}),
        "ads": cfg.get("ads", {}),
        "betting": cfg.get("betting", {}),
    }

