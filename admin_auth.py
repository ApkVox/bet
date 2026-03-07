"""
===========================================
Admin Auth (v2, simplificado para Render)
===========================================
Maneja:
- Creación de la cuenta inicial de administrador
- Login con contraseña (bcrypt)
- Emisión y validación de JWT
- Rate limiting básico por IP

Persistencia: config_store (Supabase cuando DATABASE_URL está definida).
"""

from __future__ import annotations

import time
import secrets
from typing import Dict, Any

import bcrypt
import jwt

import config_store

# Clave en config_store
CONFIG_KEY = "admin_auth"


def _default_admin_config() -> Dict[str, Any]:
    return {
        "password_hash": "",
        "jwt_secret": "",
        "created_at": None,
    }


def load_admin_config() -> Dict[str, Any]:
    """
    Carga la configuración del admin (Supabase o archivo).
    Si no existe, devuelve un objeto por defecto (sin admin creado).
    """
    base = _default_admin_config()
    data = config_store.get(CONFIG_KEY, base)
    base.update(data or {})
    return base


def save_admin_config(cfg: Dict[str, Any]) -> None:
    """Guarda la configuración del admin (Supabase o archivo)."""
    config_store.set(CONFIG_KEY, cfg)


def has_admin() -> bool:
    """True si ya existe un admin (password_hash no vacío)."""
    cfg = load_admin_config()
    return bool((cfg.get("password_hash") or "").strip())


# ===========================================
# PASSWORD HASHING
# ===========================================

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ===========================================
# JWT
# ===========================================

TOKEN_EXPIRY_HOURS = 1


def _get_jwt_secret() -> str:
    cfg = load_admin_config()
    secret = (cfg.get("jwt_secret") or "").strip()
    if not secret:
        secret = secrets.token_hex(32)
        cfg["jwt_secret"] = secret
        save_admin_config(cfg)
    return secret


def create_token() -> str:
    now = int(time.time())
    payload = {
        "role": "admin",
        "iat": now,
        "exp": now + int(TOKEN_EXPIRY_HOURS * 3600),
    }
    secret = _get_jwt_secret()
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_token(token: str) -> bool:
    try:
        secret = _get_jwt_secret()
        jwt.decode(token, secret, algorithms=["HS256"])
        return True
    except jwt.ExpiredSignatureError:
        return False
    except jwt.InvalidTokenError:
        return False


# ===========================================
# RATE LIMIT (in-memory, process-local)
# ===========================================

_login_attempts: Dict[str, list[float]] = {}
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 900  # 15 minutos


def check_rate_limit(ip: str) -> bool:
    """
    True si la IP aún puede intentar login.
    Limita a MAX_ATTEMPTS por ventana de WINDOW_SECONDS.
    """
    now = time.time()
    if ip not in _login_attempts:
        _login_attempts[ip] = []

    # Limpiar intentos fuera de ventana
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < WINDOW_SECONDS]

    return len(_login_attempts[ip]) < MAX_ATTEMPTS


def record_attempt(ip: str) -> None:
    now = time.time()
    if ip not in _login_attempts:
        _login_attempts[ip] = []
    _login_attempts[ip].append(now)


# ===========================================
# API helpers
# ===========================================

def create_initial_admin(password: str) -> None:
    """
    Crea el admin inicial si aún no existe.
    Lanza ValueError si ya hay admin o si la contraseña es inválida.
    """
    if len(password or "") < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres")

    cfg = load_admin_config()
    if (cfg.get("password_hash") or "").strip():
        raise ValueError("Ya existe una cuenta de administrador")

    cfg["password_hash"] = hash_password(password.strip())
    cfg["created_at"] = int(time.time())
    # jwt_secret se generará on-demand cuando se cree el primer token
    save_admin_config(cfg)


def login_with_password(password: str) -> str:
    """
    Verifica la contraseña del admin y devuelve un JWT si es correcta.
    Lanza ValueError en caso de error.
    """
    cfg = load_admin_config()
    pwd_hash = (cfg.get("password_hash") or "").strip()
    if not pwd_hash:
        raise ValueError("No hay cuenta de administrador configurada")

    if not verify_password(password or "", pwd_hash):
        raise ValueError("Contraseña incorrecta")

    return create_token()


def change_password(current_password: str, new_password: str) -> None:
    """
    Cambia la contraseña del admin validando la actual.
    Lanza ValueError en caso de error.
    """
    cfg = load_admin_config()
    pwd_hash = (cfg.get("password_hash") or "").strip()
    if not pwd_hash:
        raise ValueError("No hay cuenta de administrador configurada")

    if not verify_password(current_password or "", pwd_hash):
        raise ValueError("La contraseña actual no es correcta")

    if len(new_password or "") < 6:
        raise ValueError("La nueva contraseña debe tener al menos 6 caracteres")

    if verify_password(new_password, pwd_hash):
        raise ValueError("La nueva contraseña no puede ser igual a la actual")

    cfg["password_hash"] = hash_password(new_password.strip())
    save_admin_config(cfg)

