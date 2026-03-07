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

Persistencia: config_store (Supabase cuando DATABASE_URL está definida).
"""

from __future__ import annotations

from typing import Dict, Any

import config_store

CONFIG_KEY = "site_settings"

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
    Carga la configuración (Supabase o archivo), fusionada con DEFAULT_SETTINGS.
    Si no existe o está corrupto, retorna defaults.
    """
    data = config_store.get(CONFIG_KEY, {})
    if not data:
        save_settings(DEFAULT_SETTINGS.copy())
        return DEFAULT_SETTINGS.copy()
    return _deep_merge(DEFAULT_SETTINGS.copy(), data)


def save_settings(cfg: Dict[str, Any]) -> None:
    """Guarda la configuración (Supabase o archivo)."""
    config_store.set(CONFIG_KEY, cfg)


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

