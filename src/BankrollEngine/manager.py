import sqlite3
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Literal

from .models import BankrollState, Transaction, TransactionType

class BankrollManager:
    """
    Decoupled Financial State Manager.
    
    Principles:
    1. Unit-based (all calculations in Units)
    2. Singleton (one active bankroll state)
    3. Transactional (ledger for all changes)
    """
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to Data/Bankroll.sqlite relative to project root
            base_dir = Path(__file__).resolve().parents[2]
            db_path = base_dir / "Data" / "Bankroll.sqlite"
        
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize database schema if not exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        schema_path = Path(__file__).parent / "schema.sql"
        with open(schema_path, "r") as f:
            schema_script = f.read()
            
        with sqlite3.connect(self.db_path) as con:
            con.executescript(schema_script)
            
            # Ensure singleton row exists
            cursor = con.execute("SELECT COUNT(*) FROM bankroll_state")
            if cursor.fetchone()[0] == 0:
                con.execute("""
                    INSERT INTO bankroll_state (id, current_units, initial_units, peak_units, max_drawdown)
                    VALUES (1, 100.0, 100.0, 100.0, 0.0)
                """)

    def reset(self, initial_units: float = 100.0):
        """Hard reset of the bankroll."""
        with sqlite3.connect(self.db_path) as con:
            # Clear transactions
            con.execute("DELETE FROM transactions")
            
            # Reset state
            con.execute("""
                UPDATE bankroll_state
                SET current_units = ?,
                    initial_units = ?,
                    peak_units = ?,
                    max_drawdown = 0.0,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (initial_units, initial_units, initial_units))
            
            # Log initial transaction
            con.execute("""
                INSERT INTO transactions (type, amount, balance_after, note)
                VALUES (?, ?, ?, ?)
            """, (TransactionType.RESET.value, initial_units, initial_units, "System Reset"))
            
        print(f"[BANKROLL] Reset to {initial_units}U")

    def get_state(self) -> BankrollState:
        """Get current financial metrics."""
        with sqlite3.connect(self.db_path) as con:
            # Use row factory to dict for Pydantic
            con.row_factory = sqlite3.Row
            row = con.execute("SELECT * FROM bankroll_state WHERE id = 1").fetchone()
            return BankrollState(**dict(row))

    def update_bankroll(self, result: Literal["WIN", "LOSS", "PUSH"], stake_units: float, profit_units: float = 0.0, note: Optional[str] = None, expected_value: float = 0.0):
        """
        Update bankroll based on a bet result.
        
        Args:
            result: 'WIN', 'LOSS', or 'PUSH'
            stake_units: Amount wagered
            profit_units: Net profit (excluding stake) for WINs. Ignored for LOSS.
            note: Context (e.g., game ID)
            expected_value: The EV of the bet (e.g. 0.05 for 5%)
        """
        result = result.upper()
        if result not in ["WIN", "LOSS", "PUSH"]:
            raise ValueError(f"Invalid result: {result}")
            
        with sqlite3.connect(self.db_path) as con:
            state = self.get_state()
            current = state.current_units
            peak = state.peak_units
            
            if result == "WIN":
                change = profit_units
                tx_type = TransactionType.BET_WIN.value
            elif result == "LOSS":
                change = -stake_units
                tx_type = TransactionType.BET_LOSS.value
            else: # PUSH
                change = 0.0
                tx_type = TransactionType.ADJUSTMENT.value
                note = f"PUSH - {note}" if note else "PUSH"

            new_balance = current + change
            
            # Update metrics
            new_peak = max(peak, new_balance)
            current_drawdown = (new_peak - new_balance) / new_peak if new_peak > 0 else 0.0
            new_max_drawdown = max(state.max_drawdown, current_drawdown)

            # DB Update
            con.execute("""
                UPDATE bankroll_state
                SET current_units = ?,
                    peak_units = ?,
                    max_drawdown = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (new_balance, new_peak, new_max_drawdown))
            
            con.execute("""
                INSERT INTO transactions (type, amount, balance_after, note, expected_value)
                VALUES (?, ?, ?, ?, ?)
            """, (tx_type, change, new_balance, note, expected_value))
            
            return new_balance

    def calculate_performance(self):
        """Calculate aggregate performance metrics from transactions."""
        with sqlite3.connect(self.db_path) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT * FROM transactions WHERE type IN ('BET_WIN', 'BET_LOSS')").fetchall()
            
            state = self.get_state()
            
            total_bets = len(rows)
            if total_bets == 0:
                return {
                    "roi": 0.0, "hit_rate": 0.0, "total_profit": 0.0, 
                    "ev_accumulated": 0.0, "realized_vs_ev": 0.0
                }
            
            wins = sum(1 for r in rows if r['type'] == 'BET_WIN')
            net_profit = sum(r['amount'] for r in rows)
            
            # Estimate turnover (sum of abs(amount) for losses + stake for wins)
            # Since we don't store stake explicitly in transactions yet (only net change),
            # we can approximate: Loss amount is stake. Win amount is profit.
            # To get accurate ROI, we need Total Staked.
            # For WIN: change = profit. We don't know stake unless we infer or store it.
            # CRITICAL: Transactions table stores 'amount' which is net change.
            # Loss: -Stake. Win: +Profit.
            # Total Staked = Sum(abs(amount) for Loss) + Sum(Stake for Win).
            # We don't have Stake for Win stored directly.
            # Assumption: For now, use purely net profit / initial bankroll as Growth.
            # For "Yield" we need turnover.
            # Workaround: Use inferred stake or update schema later. 
            # Given constraints, we'll calculate Bankroll Growth ROI.
            
            roi_growth = (state.current_units - state.initial_units) / state.initial_units
            hit_rate = wins / total_bets
            
            # EV Accumulation (Realized profit vs Expected profit)
            # This requires 'expected_value' * 'stake'.
            # Current 'expected_value' column stores the raw EV (e.g. 0.05).
            # We need standard unit stake or actual stake to sum EV in units.
            # We will assume unit-based EV summation or similar.
            
            return {
                "roi_growth": float(roi_growth),
                "hit_rate": float(hit_rate),
                "total_profit": float(net_profit),
                "max_drawdown": float(state.max_drawdown),
                "total_bets": total_bets
            }
