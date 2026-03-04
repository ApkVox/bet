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
from typing import Optional

import bcrypt
import jwt

# ===========================================
# PATHS
# ===========================================
BASE_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = BASE_DIR / "admin_settings.json"
DEFAULT_SETTINGS_FILE = BASE_DIR / "admin_settings.default.json"
RESET_TOKENS_FILE = BASE_DIR / "password_reset_tokens.json"
_settings_path: Optional[Path] = None

# Email para recuperación (variable de entorno; por defecto el del administrador)
ADMIN_RECOVERY_EMAIL = (os.environ.get("ADMIN_RECOVERY_EMAIL") or "hasler9710@gmail.com").strip()
RESET_TOKEN_EXPIRE_MINUTES = 60

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
    """Load settings from JSON file. Si no hay permisos en el proyecto, usa /tmp (Render)."""
    settings_file = _get_settings_file()
    if not settings_file.exists():
        initial = DEFAULT_SETTINGS.copy()
        if DEFAULT_SETTINGS_FILE.exists():
            try:
                with open(DEFAULT_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    initial = _deep_merge(initial, json.load(f))
            except Exception:
                pass
        initial["password_hash"] = ""  # Sin contraseña; al entrar verá "Crear contraseña"
        save_config(initial)

    if settings_file.exists():
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            merged = _deep_merge(DEFAULT_SETTINGS.copy(), saved)
            # Forzar "primera vez" una sola vez: si ya hay contraseña, la vaciamos (Render: FORCE_INITIAL_PASSWORD=1, redeploy, crear contraseña, quitar variable)
            if os.environ.get("FORCE_INITIAL_PASSWORD", "").strip().lower() in ("1", "true", "yes") and (saved.get("password_hash") or "").strip():
                merged["password_hash"] = ""
                save_config(merged)
            # Reset directo de contraseña por env (RESET_ADMIN_PASSWORD=TuContraseña, redeploy, entrar, quitar variable)
            reset_pwd = (os.environ.get("RESET_ADMIN_PASSWORD") or "").strip()
            if reset_pwd and len(reset_pwd) >= 6:
                merged["password_hash"] = hash_password(reset_pwd)
                save_config(merged)
            return merged
        except Exception as e:
            print(f"[Admin] Error loading settings: {e}")
    return DEFAULT_SETTINGS.copy()


def save_config(config: dict):
    """Save settings to JSON file."""
    settings_file = _get_settings_file()
    with open(settings_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def _get_settings_file() -> Path:
    """Ruta del settings admin; usa /tmp si el proyecto no es escribible."""
    global _settings_path
    if _settings_path is not None:
        return _settings_path
    try:
        with open(SETTINGS_FILE, "a", encoding="utf-8"):
            pass
        _settings_path = SETTINGS_FILE
    except (OSError, PermissionError, IOError):
        _settings_path = Path("/tmp") / "lafija_admin_settings.json"
    return _settings_path


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
# PASSWORD RESET (token por correo)
# ===========================================
_reset_tokens_path: Optional[Path] = None


def _get_reset_tokens_file() -> Path:
    """Ruta al archivo de tokens; usa /tmp si el directorio del proyecto no es escribible (ej. Render)."""
    global _reset_tokens_path
    if _reset_tokens_path is not None:
        return _reset_tokens_path
    try:
        with open(RESET_TOKENS_FILE, "a"):
            pass
        _reset_tokens_path = RESET_TOKENS_FILE
    except (OSError, PermissionError, IOError):
        _reset_tokens_path = Path("/tmp") / "lafija_password_reset_tokens.json"
    return _reset_tokens_path


def _load_reset_tokens() -> dict:
    """Carga tokens de reset desde archivo."""
    path = _get_reset_tokens_file()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_reset_tokens(tokens: dict):
    """Guarda tokens de reset. Usa /tmp si el proyecto no es escribible."""
    path = _get_reset_tokens_file()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=0)
    except (OSError, PermissionError, IOError) as e:
        raise ValueError(f"No se puede guardar el token (permisos o disco): {e}")


def create_password_reset_token(email: str) -> str:
    """Crea un token de recuperación y lo guarda. Devuelve el token."""
    try:
        email = (email or "").strip().lower()
        if not email:
            raise ValueError("Email requerido")
        allowed = (os.environ.get("ADMIN_RECOVERY_EMAIL", "") or "").strip().lower()
        if allowed and email != allowed:
            raise ValueError("El correo no coincide con el configurado para recuperación")
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
        tokens = _load_reset_tokens()
        now = datetime.now(timezone.utc)
        tokens = {k: v for k, v in tokens.items() if datetime.fromisoformat(v["expires"].replace("Z", "+00:00")) > now}
        tokens[token] = {"email": email, "expires": expires.isoformat()}
        _save_reset_tokens(tokens)
        return token
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Error al crear token: {e}")


def get_and_consume_reset_token(token: str) -> str:
    """Si el token es válido, lo elimina y devuelve el email. Si no, lanza ValueError."""
    token = (token or "").strip()
    if not token:
        raise ValueError("Token inválido")
    tokens = _load_reset_tokens()
    data = tokens.get(token)
    if not data:
        raise ValueError("Token no encontrado o ya usado")
    expires = datetime.fromisoformat(data["expires"].replace("Z", "+00:00"))
    if datetime.now(timezone.utc) > expires:
        del tokens[token]
        _save_reset_tokens(tokens)
        raise ValueError("Token expirado")
    email = data["email"]
    del tokens[token]
    _save_reset_tokens(tokens)
    return email


def send_reset_email(to_email: str, token: str, base_url: str) -> None:
    """Envía el correo con el enlace de recuperación. Usa Resend (API HTTP) si está configurado, si no SMTP.
    En Render free solo funciona Resend: el plan free de Render bloquea puertos SMTP."""
    reset_url = f"{base_url.rstrip('/')}/admin?reset={token}"
    subject = "Recuperación de contraseña — Admin La Fija"
    body_plain = f"""Hola,\n\nHas solicitado restablecer la contraseña del panel de administración.\n\nEnlace (válido 1 hora):\n{reset_url}\n\nSi no fuiste tú, ignora este correo.\n"""
    body_html = f"""<p>Hola,</p><p>Has solicitado restablecer la contraseña del panel de administración.</p><p><a href="{reset_url}">Restablecer contraseña</a></p><p>O copia este enlace (válido 1 hora):<br><code>{reset_url}</code></p><p>Si no fuiste tú, ignora este correo.</p>"""

    # 1) Resend (API HTTP) — recomendado para Render free: no usa puertos SMTP
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    if resend_key:
        try:
            import requests as _req
        except ImportError:
            raise ValueError("Falta la librería 'requests'. Instálala para usar Resend.")
        try:
            from_addr = os.environ.get("RESEND_FROM", "La Fija <onboarding@resend.dev>").strip()
            payload = {
                "from": from_addr,
                "to": [to_email],
                "subject": subject,
                "html": body_html,
                "text": body_plain,
            }
            r = _req.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={"Authorization": f"Bearer {resend_key}"},
                timeout=25,
            )
            if r.status_code not in (200, 201, 202):
                try:
                    err_body = r.json()
                    msg = err_body.get("message") or err_body.get("name") or err_body.get("detail") or r.text[:300]
                except Exception:
                    msg = r.text[:300] or str(r.status_code)
                raise ValueError(f"Resend {r.status_code}: {msg}")
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"Resend: {e}")
        return

    # 2) SMTP (solo funciona en planes de pago de Render; free bloquea puertos 25/465/587)
    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    from_addr = os.environ.get("SMTP_FROM", user or "noreply@lafija.com")
    if host and user and password:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_email
        msg.attach(MIMEText(body_plain, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))
        with smtplib.SMTP(host, port) as s:
            if use_tls:
                s.starttls()
            s.login(user, password)
            s.sendmail(from_addr, [to_email], msg.as_string())
        return

    raise ValueError(
        "Configura envío de correo: en Render free usa Resend (RESEND_API_KEY y opcional RESEND_FROM). "
        "En servidor con SMTP: SMTP_HOST, SMTP_USER, SMTP_PASSWORD."
    )


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
    print(f"   Archivo: {_get_settings_file()}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "set-password":
        cli_set_password()
    else:
        print("Uso: python admin_config.py set-password")
        print("  Configura la contraseña del panel de administración.")
