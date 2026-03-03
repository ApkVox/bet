"""
===========================================
Admin Configuration & Security Module
===========================================
Handles admin authentication (bcrypt + JWT),
settings storage, and rate limiting.
"""

import os
import json
import time
import secrets
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt

# ===========================================
# PATHS
# ===========================================
BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "admin_settings.json"
DEFAULT_SETTINGS_FILE = BASE_DIR / "admin_settings.default.json"

# ===========================================
# DEFAULT SETTINGS
# ===========================================
DEFAULT_SETTINGS = {
    "password_hash": "",
    "jwt_secret": "",
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
            "--warning": "#ff9500"
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
            "--warning": "#ff9f0a"
        }
    },
    "branding": {
        "title": "La Fija",
        "subtitle": "Predicciones NBA y Futbol con Inteligencia Artificial",
        "emoji": "\U0001F3C0"
    },
    "features": {
        "football": False,
        "promo_download": True,
        "dark_default": True,
        "ai_analysis": True
    },
    "announcement": {
        "enabled": False,
        "text": "",
        "color": "#0a84ff"
    },
    "ads": {
        "enabled": True,
        "left_key": "e2cbd291fd6e2e0a824862d3ff57a34f",
        "right_key": "e2cbd291fd6e2e0a824862d3ff57a34f"
    }
}

# ===========================================
# RATE LIMITING (in-memory)
# ===========================================
_login_attempts = {}  # ip -> [timestamp, timestamp, ...]
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 900  # 15 minutes


def check_rate_limit(ip: str) -> bool:
    """Returns True if the IP is allowed to attempt login."""
    now = time.time()
    if ip not in _login_attempts:
        _login_attempts[ip] = []

    # Clean old attempts
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < WINDOW_SECONDS]

    if len(_login_attempts[ip]) >= MAX_ATTEMPTS:
        return False
    return True


def record_attempt(ip: str):
    """Record a failed login attempt."""
    now = time.time()
    if ip not in _login_attempts:
        _login_attempts[ip] = []
    _login_attempts[ip].append(now)


# ===========================================
# SETTINGS I/O
# ===========================================
def load_config() -> dict:
    """Load settings from JSON file, creating from default file if missing."""
    if not SETTINGS_FILE.exists() and DEFAULT_SETTINGS_FILE.exists():
        import shutil
        shutil.copy2(DEFAULT_SETTINGS_FILE, SETTINGS_FILE)
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # Merge with defaults to ensure new keys exist
            merged = _deep_merge(DEFAULT_SETTINGS.copy(), saved)
            return merged
        except Exception as e:
            print(f"[Admin] Error loading settings: {e}")
    return DEFAULT_SETTINGS.copy()


def save_config(config: dict):
    """Save settings to JSON file."""
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_public_config() -> dict:
    """Return only the safe, public settings (no passwords/secrets)."""
    config = load_config()
    return {
        "theme": config.get("theme", {}),
        "branding": config.get("branding", {}),
        "features": config.get("features", {}),
        "announcement": config.get("announcement", {}),
        "ads": config.get("ads", {})
    }


# ===========================================
# PASSWORD HASHING (bcrypt)
# ===========================================
def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ===========================================
# JWT TOKENS
# ===========================================
TOKEN_EXPIRY_HOURS = 1


def _get_jwt_secret() -> str:
    """Get or generate JWT secret."""
    config = load_config()
    if not config.get("jwt_secret"):
        config["jwt_secret"] = secrets.token_hex(32)
        save_config(config)
    return config["jwt_secret"]


def create_token() -> str:
    """Create a JWT token for the admin."""
    import time
    secret = _get_jwt_secret()
    now = int(time.time())
    payload = {
        "role": "admin",
        "iat": now,
        "exp": now + int(TOKEN_EXPIRY_HOURS * 3600)
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_token(token: str) -> bool:
    """Verify a JWT token."""
    try:
        secret = _get_jwt_secret()
        jwt.decode(token, secret, algorithms=["HS256"])
        return True
    except jwt.ExpiredSignatureError:
        return False
    except jwt.InvalidTokenError:
        return False


# ===========================================
# CLI: Set initial password
# ===========================================
def cli_set_password():
    """Interactive CLI to set admin password."""
    import getpass
    print("=" * 40)
    print("  La Fija — Configurar contraseña admin")
    print("=" * 40)

    password = getpass.getpass("Nueva contraseña: ")
    if len(password) < 6:
        print("Error: La contraseña debe tener al menos 6 caracteres.")
        sys.exit(1)

    confirm = getpass.getpass("Confirmar contraseña: ")
    if password != confirm:
        print("Error: Las contraseñas no coinciden.")
        sys.exit(1)

    config = load_config()
    config["password_hash"] = hash_password(password)

    # Auto-generate JWT secret if missing
    if not config.get("jwt_secret"):
        config["jwt_secret"] = secrets.token_hex(32)

    save_config(config)
    print("✅ Contraseña de administrador configurada correctamente.")
    print(f"   Archivo: {SETTINGS_FILE}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "set-password":
        cli_set_password()
    else:
        print("Uso: python admin_config.py set-password")
        print("  Configura la contraseña del panel de administración.")
