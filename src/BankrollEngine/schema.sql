-- Bankroll Engine Schema (Enhanced for Performance Tracking)

-- Table: bankroll_state (Singleton)
CREATE TABLE IF NOT EXISTS bankroll_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    current_units REAL NOT NULL,
    initial_units REAL NOT NULL,
    peak_units REAL NOT NULL,
    max_drawdown REAL NOT NULL DEFAULT 0.0,
    kelly_fraction REAL NOT NULL DEFAULT 0.25,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: transactions (Ledger)
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    type TEXT NOT NULL CHECK(type IN ('RESET', 'BET_WIN', 'BET_LOSS', 'ADJUSTMENT')),
    amount REAL NOT NULL,
    balance_after REAL NOT NULL,
    note TEXT,
    expected_value REAL DEFAULT 0.0  -- Added for Performance EV vs Real
);

-- Table: performance_snapshots (Historical Daily Metrics)
CREATE TABLE IF NOT EXISTS performance_snapshots (
    date DATE PRIMARY KEY,
    total_bets INTEGER NOT NULL,
    win_rate REAL NOT NULL,
    roi_percent REAL NOT NULL,
    profit_units REAL NOT NULL,
    bankroll_growth REAL NOT NULL,
    expected_profit_units REAL NOT NULL,
    closing_balance REAL NOT NULL,
    drawdown REAL NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);

CREATE TABLE IF NOT EXISTS shadow_bets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    decision TEXT NOT NULL, -- BET, PASS, BLOCKED
    probability REAL NOT NULL,
    odds REAL NOT NULL,
    ev REAL NOT NULL,
    stake_units REAL NOT NULL,
    kelly_fraction REAL NOT NULL,
    status TEXT DEFAULT 'PENDING', -- PENDING, WON, LOST, PUSHED
    pnl REAL DEFAULT 0.0,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reason TEXT
);

-- Table: audit_log (Immutable Append-Only Behavior Log)
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT NOT NULL, -- BET_TAKEN, BET_BLOCKED, RISK_TRIGGER, STATE_CHANGE
    game_id TEXT,
    details TEXT NOT NULL, -- JSON or description
    old_state TEXT,
    new_state TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_event ON audit_log(event_type);

