-- Esquema completo de La Fija en Supabase (idempotente: se puede correr varias veces).
-- Supabase → SQL Editor → New query → pegar todo → Run.
--
-- Las tablas quedan con RLS activo y sin políticas: solo entra el backend
-- (SUPABASE_KEY debe ser la service_role / secret key, NUNCA la anon/publishable).

-- Config persistente (admin, tema, promo) — la lee config_store.py vía DATABASE_URL
CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Historial NBA — history_db.py (upsert por match_id)
CREATE TABLE IF NOT EXISTS predictions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date TEXT NOT NULL,
    match_id TEXT UNIQUE NOT NULL,
    home_team TEXT,
    away_team TEXT,
    predicted_winner TEXT,
    prob_model DOUBLE PRECISION,
    prob_final DOUBLE PRECISION,
    odds DOUBLE PRECISION,
    ev_value DOUBLE PRECISION,
    kelly_stake DOUBLE PRECISION,
    warning_level TEXT,
    odds_home DOUBLE PRECISION,
    odds_away DOUBLE PRECISION,
    result TEXT DEFAULT 'PENDING',          -- WIN | LOSS | PENDING
    profit DOUBLE PRECISION DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Historial fútbol (upsert por match_id)
CREATE TABLE IF NOT EXISTS football_predictions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date TEXT NOT NULL,
    league TEXT NOT NULL DEFAULT 'ENG-Premier League',
    match_id TEXT UNIQUE NOT NULL,
    home_team TEXT,
    away_team TEXT,
    prediction TEXT,                        -- 1 | X | 2
    prob_home DOUBLE PRECISION,
    prob_draw DOUBLE PRECISION,
    prob_away DOUBLE PRECISION,
    odd_home DOUBLE PRECISION,
    odd_draw DOUBLE PRECISION,
    odd_away DOUBLE PRECISION,
    status TEXT DEFAULT 'PENDING',
    result TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Noticias por partido (upsert por match_id)
CREATE TABLE IF NOT EXISTS match_news (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date TEXT NOT NULL,
    match_id TEXT UNIQUE NOT NULL,
    sport TEXT DEFAULT 'nba',
    headline TEXT,
    key_points JSONB DEFAULT '[]',
    injuries JSONB DEFAULT '[]',
    impact_assessment TEXT,
    confidence_modifier TEXT DEFAULT 'neutral',
    raw_response JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Recomendaciones / parlay diario (upsert por date)
CREATE TABLE IF NOT EXISTS daily_recommendations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date TEXT UNIQUE NOT NULL,
    sport TEXT DEFAULT 'nba',
    recommendations JSONB DEFAULT '[]',
    parlay_analysis TEXT,
    parlay_odds DOUBLE PRECISION,
    reasoning TEXT,
    result TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Marcadores NBA (alimentan el Elo del modelo) — los guarda el job diario
CREATE TABLE IF NOT EXISTS nba_games (
    date TEXT NOT NULL,
    home TEXT NOT NULL,
    away TEXT NOT NULL,
    home_score INTEGER NOT NULL,
    away_score INTEGER NOT NULL,
    ml_home DOUBLE PRECISION,                -- cuota americana
    ml_away DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (date, home, away)
);

ALTER TABLE nba_games             ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_config            ENABLE ROW LEVEL SECURITY;
ALTER TABLE predictions           ENABLE ROW LEVEL SECURITY;
ALTER TABLE football_predictions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE match_news            ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_recommendations ENABLE ROW LEVEL SECURITY;
-- Sin políticas: solo la clave secreta (service_role) lee y escribe. Render, GitHub Actions y .env usan esa.
