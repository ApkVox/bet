-- =============================================
-- AUTONOMOUS LADDER CHALLENGE - DATABASE SCHEMA V3
-- =============================================
-- Version: 3.0 (Multi-Ladder)
-- Purpose: Support multiple concurrent ladder challenges

-- Table: Ladders (Registry of all challenges)
CREATE TABLE IF NOT EXISTS ladders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    current_capital REAL NOT NULL,
    starting_capital REAL NOT NULL,
    goal_capital REAL NOT NULL,
    step_number INTEGER NOT NULL DEFAULT 1,
    max_step_reached INTEGER NOT NULL DEFAULT 1,
    strategy_mode TEXT NOT NULL DEFAULT 'FENIX', -- 'AUTO', 'SAFE', 'FENIX', 'AGGRESSIVE'
    consecutive_wins INTEGER DEFAULT 0,
    consecutive_losses INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'COMPLETED', 'BANKRUPT', 'ARCHIVED'
    last_update_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: Daily Tickets (Parlays generated each day)
CREATE TABLE IF NOT EXISTS ladder_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ladder_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    ticket_json TEXT NOT NULL,           -- Full ticket details as JSON
    strategy_used TEXT NOT NULL,
    num_legs INTEGER NOT NULL,
    stake_amount REAL NOT NULL,
    potential_payout REAL,
    combined_odds REAL,
    combined_probability REAL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    actual_result_json TEXT,
    profit_loss REAL DEFAULT 0.0,
    groq_validation_log TEXT,
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ladder_id) REFERENCES ladders(id),
    UNIQUE(ladder_id, date)              -- One ticket per ladder per day
);

-- Table: Individual Bet Legs (For detailed tracking)
CREATE TABLE IF NOT EXISTS ticket_legs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    match_id TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    bet_type TEXT NOT NULL,
    pick TEXT NOT NULL,
    probability REAL NOT NULL,
    decimal_odds REAL NOT NULL,
    groq_safety_check TEXT,
    actual_winner TEXT,
    leg_result TEXT DEFAULT 'PENDING',
    FOREIGN KEY (ticket_id) REFERENCES ladder_tickets(id)
);

-- Table: Bankroll History (For charts and analysis)
CREATE TABLE IF NOT EXISTS bankroll_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ladder_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    capital_before REAL NOT NULL,
    capital_after REAL NOT NULL,
    daily_change REAL NOT NULL,
    daily_change_pct REAL NOT NULL,
    step_number INTEGER NOT NULL,
    ticket_result TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ladder_id) REFERENCES ladders(id)
);

-- Table: Groq Agent Logs (Shared across ladders)
CREATE TABLE IF NOT EXISTS groq_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    match_id TEXT NOT NULL,
    prompt_sent TEXT NOT NULL,
    response_received TEXT,
    safety_verdict TEXT,
    latency_ms INTEGER,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: Bad Beats Memory (Shared AI Learning)
CREATE TABLE IF NOT EXISTS bad_beats_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    match_id TEXT NOT NULL,
    predicted_winner TEXT NOT NULL,
    actual_winner TEXT NOT NULL,
    probability_was REAL,
    learning_note TEXT,
    pattern_tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initialize default ladder if empty
INSERT OR IGNORE INTO ladders (id, name, current_capital, starting_capital, goal_capital, step_number, strategy_mode)
VALUES (1, 'Reto Principal', 100000.0, 100000.0, 1000000.0, 1, 'FENIX');

-- Indexes
CREATE INDEX IF NOT EXISTS idx_tickets_ladder_date ON ladder_tickets(ladder_id, date);
CREATE INDEX IF NOT EXISTS idx_bankroll_ladder_date ON bankroll_history(ladder_id, date);
