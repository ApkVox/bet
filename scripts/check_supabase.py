#!/usr/bin/env python3
"""Verifica la conexión a Supabase (REST + PostgreSQL) y que existan las tablas.
Uso: python scripts/check_supabase.py
"""
import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

import config_store
import history_db

ok = True

# --- REST (supabase-py): historial ---
key = os.environ.get("SUPABASE_KEY", "")
try:
    seg = key.split(".")[1]
    role = json.loads(base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))).get("role")
except Exception:
    role = None
if role == "anon" or key.startswith("sb_publishable_"):
    print("⚠ SUPABASE_KEY es la clave pública: con RLS activo verá todo vacío. Usa la service_role/secret key.")
    ok = False

client = history_db._get_supabase()
if not client:
    print("✗ SUPABASE_URL / SUPABASE_KEY: faltan o son inválidas")
    ok = False
else:
    for t in ("predictions", "football_predictions", "match_news", "daily_recommendations"):
        try:
            n = client.table(t).select("id", count="exact").limit(1).execute().count
            print(f"✓ {t}: {n} filas")
        except Exception as e:
            print(f"✗ {t}: {e}")
            ok = False

# --- PostgreSQL (psycopg2): config del admin/tema/promo ---
if not config_store.is_db_available():
    print("✗ DATABASE_URL: no definida")
    ok = False
else:
    try:
        import psycopg2

        with psycopg2.connect(config_store._get_db_url()) as c, c.cursor() as cur:
            cur.execute("SELECT count(*) FROM app_config")
            print(f"✓ app_config: {cur.fetchone()[0]} filas")
    except Exception as e:
        print(f"✗ app_config: {e}")
        ok = False

print("\nTodo conectado." if ok else "\nHay problemas: revisa docs/SERVICIOS_Y_APIS.md (sección Supabase).")
sys.exit(0 if ok else 1)
