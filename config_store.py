"""
===========================================
Config Store - Persistencia en Supabase o archivos
===========================================
Almacena configuración en PostgreSQL (Supabase) cuando DATABASE_URL está definida.
Fallback a archivos JSON para desarrollo local sin base de datos.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import quote, unquote

BASE_DIR = Path(__file__).resolve().parent

# Mapeo clave -> nombre de archivo para fallback
_KEY_TO_FILE = {
    "admin_auth": "admin_auth.json",
    "site_settings": "site_settings.json",
    "promo_config": "promo_config.json",
}


def _fix_password_encoding(url: str) -> str:
    """
    Codifica la contraseña en la URL si contiene caracteres reservados ([, ], @, :, etc).
    Los corchetes en la contraseña rompen el parsing de la URI.
    """
    # Formato: postgresql://user:password@host:port/db o postgres://user:password@host:port/db
    match = re.match(r"^(postgresql|postgres)://([^:@]+):([^@]+)@(.+)$", url)
    if not match:
        return url
    protocol, user, password, rest = match.groups()
    # Si la contraseña ya está codificada o no tiene caracteres problemáticos, no tocar
    if "%" in password or any(c in password for c in "[]@:"):
        raw = unquote(password) if "%" in password else password
        encoded = quote(raw, safe="")
        return f"{protocol}://{user}:{encoded}@{rest}"
    return url


def _get_db_url() -> str | None:
    """Obtiene DATABASE_URL si está definida y no vacía.
    Codifica la contraseña si tiene caracteres reservados.
    Añade sslmode=require para Supabase si no está presente.
    """
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        return None
    url = _fix_password_encoding(url)
    # Supabase requiere SSL; añadir si no está
    if "supabase.co" in url and "sslmode=" not in url:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}sslmode=require"
    return url


def is_db_available() -> bool:
    """True si DATABASE_URL está configurada."""
    return _get_db_url() is not None


def _get_from_db(key: str) -> dict | None:
    """Lee un valor de la tabla app_config. None si no existe o hay error."""
    url = _get_db_url()
    if not url:
        return None

    try:
        import psycopg2
        conn = psycopg2.connect(url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT value FROM app_config WHERE key = %s",
                    (key,)
                )
                row = cur.fetchone()
                if row and row[0] is not None:
                    val = row[0]
                    if isinstance(val, dict):
                        return val
                    if isinstance(val, str):
                        return json.loads(val)
                    return dict(val)
                return None
        finally:
            conn.close()
    except Exception as e:
        print(f"[config_store] DB read error for key={key}: {e}")
        return None


class ConfigStoreError(Exception):
    """Error con mensaje amigable para el usuario."""
    pass


def _set_in_db(key: str, value: dict) -> None:
    """Escribe un valor en la tabla app_config."""
    url = _get_db_url()
    if not url:
        raise ValueError("DATABASE_URL no configurada")

    import psycopg2
    try:
        conn = psycopg2.connect(url)
    except Exception as e:
        err = str(e).lower()
        if "password" in err or "authentication" in err:
            raise ConfigStoreError(
                "Contraseña de Supabase incorrecta. Verifica en Project Settings → Database y usa Reset password si es necesario."
            ) from e
        if "connection" in err or "refused" in err or "timeout" in err:
            raise ConfigStoreError(
                "No se puede conectar a Supabase. Usa Connection pooler (Session mode) en lugar de Direct."
            ) from e
        raise ConfigStoreError(f"Error de conexión: {e}") from e

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO app_config (key, value, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (key) DO UPDATE SET
                    value = EXCLUDED.value,
                    updated_at = NOW()
                """,
                (key, json.dumps(value))
            )
        conn.commit()
    except Exception as e:
        err = str(e).lower()
        if "app_config" in err or "relation" in err or "does not exist" in err:
            raise ConfigStoreError(
                "La tabla app_config no existe. Ejecuta el SQL de scripts/init_app_config.sql en Supabase (SQL Editor)."
            ) from e
        raise ConfigStoreError(f"Error al guardar: {e}") from e
    finally:
        conn.close()


def _get_fallback_path(key: str) -> Path:
    """Ruta del archivo de fallback para la clave."""
    filename = _KEY_TO_FILE.get(key, f"{key}.json")
    project_path = BASE_DIR / filename
    try:
        with open(project_path, "a", encoding="utf-8"):
            pass
        return project_path
    except (OSError, PermissionError):
        return Path("/tmp") / f"lafija_{filename}"


def get(key: str, default: dict | None = None) -> dict:
    """
    Obtiene la configuración para la clave.
    Si DATABASE_URL está definida, lee de PostgreSQL.
    Si no, lee del archivo JSON de fallback.
    """
    default = default or {}

    if is_db_available():
        data = _get_from_db(key)
        if data is not None:
            return data
        # DB falló o no hay fila; intentar archivo
        path = _get_fallback_path(key)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default.copy()

    # Sin DB: usar archivos
    path = _get_fallback_path(key)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default.copy()


def set(key: str, value: dict) -> None:
    """
    Guarda la configuración para la clave.
    Si DATABASE_URL está definida, escribe en PostgreSQL.
    Si no, escribe en el archivo JSON de fallback.
    """
    if is_db_available():
        try:
            _set_in_db(key, value)
            return
        except ConfigStoreError:
            raise
        except Exception as e:
            print(f"[config_store] DB write failed for key={key}: {e}")
            raise ConfigStoreError(f"Error de base de datos: {e}") from e

    # Fallback a archivo
    path = _get_fallback_path(key)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
