import sqlite3
import threading
from pathlib import Path
from typing import Optional, Literal
import logging

from .models import BankrollState, TransactionType

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BankrollService")

class BankrollService:
    """
    Singleton Service for Centralized Bankroll Management.
    Implements State Machine for Risk Control (Active -> Degraded -> Paused).
    Thread-safe database access.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: Optional[str] = None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BankrollService, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: Optional[str] = None):
        if self._initialized:
            return
            
        if db_path is None:
            # Default to Data/Bankroll.sqlite relative to project root
            base_dir = Path(__file__).resolve().parents[2]
            db_path = base_dir / "Data" / "Bankroll.sqlite"
        
        self.db_path = Path(db_path)
        self._init_db()
        self._initialized = True
        logger.info(f"BankrollService initialized at {self.db_path}")

    def _init_db(self):
        """Initialize database schema if not exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        schema_path = Path(__file__).parent / "schema.sql"
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found at {schema_path}")
            
        with open(schema_path, "r") as f:
            schema_script = f.read()
            
        with sqlite3.connect(self.db_path) as con:
            con.executescript(schema_script)
            
            # Ensure singleton row exists
            cursor = con.execute("SELECT COUNT(*) FROM bankroll_state")
            if cursor.fetchone()[0] == 0:
                con.execute("""
                    INSERT INTO bankroll_state (id, current_units, initial_units, peak_bankroll, max_drawdown, kelly_fraction, status)
                    VALUES (1, 100.0, 100.0, 100.0, 0.0, 0.25, 'ACTIVE')
                """)

    def get_state(self) -> BankrollState:
        """Get current financial metrics and status."""
        with sqlite3.connect(self.db_path) as con:
            con.row_factory = sqlite3.Row
            row = con.execute("SELECT * FROM bankroll_state WHERE id = 1").fetchone()
            if not row:
                raise RuntimeError("Bankroll state missing!")
            return BankrollState(**dict(row))

    def _update_status(self, current_drawdown: float, consecutive_losses: int) -> tuple[str, float]:
        """
        State Machine Logic.
        Returns (new_status, new_kelly_fraction)
        """
        current_state = self.get_state()
        status = current_state.status
        kelly = current_state.kelly_fraction
        
        # 1. Check for Critical Failure (Pause)
        if consecutive_losses >= 10:
            return "PAUSED", 0.0
        
        if current_drawdown > 0.40: # 40% Drawdown -> Pause
            return "PAUSED", 0.0
            
        # 2. Check for Degradation
        if status == "ACTIVE":
            if current_drawdown > 0.20:
                return "DEGRADED", 0.10
        elif status == "DEGRADED":
            if current_drawdown < 0.15: # Recovery
                return "ACTIVE", 0.25
                
        # 3. Default: Maintain current
        return status, kelly

    def _count_consecutive_losses(self, con) -> int:
        """Count consecutive BET_LOSS transactions from tail."""
        rows = con.execute("""
            SELECT type FROM transactions 
            WHERE type IN ('BET_WIN', 'BET_LOSS') 
            ORDER BY id DESC LIMIT 20
        """).fetchall()
        
        count = 0
        for row in rows:
            if row[0] == 'BET_LOSS':
                count += 1
            else:
                break
        return count

    def update_bankroll(self, result: Literal["WIN", "LOSS", "PUSH"], stake_units: float, profit_units: float = 0.0, note: Optional[str] = None, expected_value: float = 0.0):
        """
        Transactional update of bankroll with State Machine evaluation.
        """
        # Fail-safe: Check status first (in memory/read)
        state = self.get_state()
        if state.status == "PAUSED":
            logger.warning("Attempted update while PAUSED. Ignoring.")
            return state.current_units

        result = result.upper()
        
        with sqlite3.connect(self.db_path) as con:
            con.row_factory = sqlite3.Row  # Ensure index-based access works
            # Re-read inside transaction for consistency
            row = con.execute("SELECT * FROM bankroll_state WHERE id = 1").fetchone()
            current = row['current_units']
            peak = row['peak_bankroll']
            max_dd = row['max_drawdown']
            
            # 1. Application Logic
            if result == "WIN":
                change = profit_units
                tx_type = TransactionType.BET_WIN.value
            elif result == "LOSS":
                change = -stake_units
                tx_type = TransactionType.BET_LOSS.value
            else: # PUSH
                change = 0.0
                tx_type = TransactionType.ADJUSTMENT.value
            
            new_balance = current + change
            
            # 2. Metrics Update
            new_peak = max(peak, new_balance)
            current_drawdown = (new_peak - new_balance) / new_peak if new_peak > 0 else 0.0
            new_max_drawdown = max(max_dd, current_drawdown)
            
            # Log Transaction first to allow counting losses
            con.execute("""
                INSERT INTO transactions (type, amount, balance_after, note, expected_value)
                VALUES (?, ?, ?, ?, ?)
            """, (tx_type, change, new_balance, note, expected_value))
            
            # 3. State Machine Elevation
            losses = self._count_consecutive_losses(con)
            new_status, new_kelly = self._update_status(current_drawdown, losses)
            
            if new_status != state.status:
                logger.warning(f"State Transition: {state.status} -> {new_status} (Kelly: {new_kelly})")

            # 4. Persistence
            con.execute("""
                UPDATE bankroll_state
                SET current_units = ?,
                    peak_bankroll = ?,
                    max_drawdown = ?,
                    kelly_fraction = ?,
                    status = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (new_balance, new_peak, new_max_drawdown, new_kelly, new_status))
            
            return new_balance

    @property
    def kelly_fraction(self) -> float:
        return self.get_state().kelly_fraction

    @property
    def operational_status(self) -> str:
        return self.get_state().status

    def get_observability_metrics(self) -> dict:
        """
        Get aggregated metrics for observability dashboard.
        """
        with sqlite3.connect(self.db_path) as con:
            # Blocked Bets Count (from shadow or risk logs??)
            # RiskGuard blocks are "shadow" decisions usually if rejected?
            # Actually shadow_bettor logs ALL decisions.
            # So we count decision='BLOCKED' in shadow_bets.
            
            # Check if shadow_bets exists first
            row = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shadow_bets'").fetchone()
            if not row:
                blocked_count = 0
                avg_ev = 0.0
            else:
                row_blocked = con.execute("SELECT COUNT(*) FROM shadow_bets WHERE decision = 'BLOCKED'").fetchone()
                blocked_count = row_blocked[0] if row_blocked else 0
                
                row_ev = con.execute("SELECT AVG(ev) FROM shadow_bets").fetchone()
                avg_ev = row_ev[0] if row_ev and row_ev[0] is not None else 0.0

            state = self.get_state()
            
            return {
                "drawdown": state.max_drawdown,
                "kelly_fraction": state.kelly_fraction,
                "status": state.status,
                "blocked_bets": blocked_count,
                "avg_ev": avg_ev,
                "peak_bankroll": state.peak_bankroll,
                "current_units": state.current_units
            }

# Global Accessor
def get_bankroll_service():
    return BankrollService()
