-- Crear tabla app_config para almacenar configuración persistente (Supabase)
-- Ejecutar en Supabase SQL Editor: New query → pegar → Run

CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
