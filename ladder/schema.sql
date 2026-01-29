-- =============================================
-- AUTONOMOUS LADDER CHALLENGE - DATABASE SCHEMA
-- =============================================
-- Version: 2.0 (Groq-Optimized)
-- Purpose: Track ladder progress, tickets, and bankroll

-- Table: Ladder State (Current progress)
CREATE TABLE IF NOT EXISTS ladder_state (
    id INTEGER PRIMARY KEY DEFAULT 1,
    current_capital REAL NOT NULL DEFAULT 10000.0,
    starting_capital REAL NOT NULL DEFAULT 10000.0,
    goal_capital REAL NOT NULL DEFAULT 100000.0,
    step_number INTEGER NOT NULL DEFAULT 1,
    max_step_reached INTEGER NOT NULL DEFAULT 1,
    strategy_mode TEXT NOT NULL DEFAULT 'FENIX', -- 'SAFE', 'FENIX', 'AGGRESSIVE'
    consecutive_wins INTEGER DEFAULT 0,
    consecutive_losses INTEGER DEFAULT 0,
    last_update_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: Daily Tickets (Parlays generated each day)
CREATE TABLE IF NOT EXISTS ladder_tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    ticket_json TEXT NOT NULL,           -- Full ticket details as JSON
    strategy_used TEXT NOT NULL,         -- 'SAFE', 'FENIX', 'AGGRESSIVE'
    num_legs INTEGER NOT NULL,           -- Number of parlay legs (1-3)
    stake_amount REAL NOT NULL,          -- Amount wagered
    potential_payout REAL,               -- Expected return if win
    combined_odds REAL,                  -- Combined decimal odds
    combined_probability REAL,           -- Combined win probability
    status TEXT NOT NULL DEFAULT 'PENDING', -- 'PENDING', 'WIN', 'LOSS', 'PUSH', 'CANCELLED'
    actual_result_json TEXT,             -- Actual scores after resolution
    profit_loss REAL DEFAULT 0.0,
    groq_validation_log TEXT,            -- Log of Groq safety checks
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date)                         -- One ticket per day
);

-- Table: Individual Bet Legs (For detailed tracking)
CREATE TABLE IF NOT EXISTS ticket_legs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL,
    match_id TEXT NOT NULL,              -- e.g., "Lakers:Warriors"
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    bet_type TEXT NOT NULL,              -- 'MONEYLINE', 'OVER', 'UNDER', 'SPREAD'
    pick TEXT NOT NULL,                  -- Team name or "OVER 225.5"
    probability REAL NOT NULL,
    decimal_odds REAL NOT NULL,
    groq_safety_check TEXT,              -- 'SAFE', 'RISK', 'UNKNOWN'
    actual_winner TEXT,                  -- Filled after resolution
    leg_result TEXT DEFAULT 'PENDING',   -- 'WIN', 'LOSS', 'PUSH', 'PENDING'
    FOREIGN KEY (ticket_id) REFERENCES ladder_tickets(id)
);

-- Table: Bankroll History (For charts and analysis)
CREATE TABLE IF NOT EXISTS bankroll_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    capital_before REAL NOT NULL,
    capital_after REAL NOT NULL,
    daily_change REAL NOT NULL,
    daily_change_pct REAL NOT NULL,
    step_number INTEGER NOT NULL,
    ticket_result TEXT,                  -- 'WIN', 'LOSS', 'NO_BET'
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: Groq Agent Logs (For debugging and learning)
CREATE TABLE IF NOT EXISTS groq_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    match_id TEXT NOT NULL,
    prompt_sent TEXT NOT NULL,
    response_received TEXT,
    safety_verdict TEXT,                 -- 'SAFE', 'RISK', 'ERROR'
    latency_ms INTEGER,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: Bad Beats Memory (AI Learning)
CREATE TABLE IF NOT EXISTS bad_beats_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    match_id TEXT NOT NULL,
    predicted_winner TEXT NOT NULL,
    actual_winner TEXT NOT NULL,
    probability_was REAL,
    learning_note TEXT,                  -- User or AI generated lesson
    pattern_tags TEXT,                   -- e.g., "back_to_back,injury_surprise"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Initialize default state if empty (values in COP - Colombian Pesos)
INSERT OR IGNORE INTO ladder_state (id, current_capital, starting_capital, goal_capital, step_number, strategy_mode)
VALUES (1, 100000.0, 100000.0, 1000000.0, 1, 'FENIX');

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tickets_date ON ladder_tickets(date);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON ladder_tickets(status);
CREATE INDEX IF NOT EXISTS idx_legs_ticket ON ticket_legs(ticket_id);
CREATE INDEX IF NOT EXISTS idx_bankroll_date ON bankroll_history(date);
