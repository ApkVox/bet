"""
Audit Logger Service
====================
Immutable append-only behavior log for Phase 6 observability.
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

from src.BankrollEngine.service import get_bankroll_service

class AuditLogger:
    """Append-only behavior log."""
    
    def __init__(self):
        self._db_path = get_bankroll_service().db_path

    def log(self, event_type: str, game_id: str = None, details: str = "", old_state: str = None, new_state: str = None):
        """
        Log an event. Append-only.
        
        event_type: BET_TAKEN, BET_BLOCKED, RISK_TRIGGER, STATE_CHANGE
        """
        with sqlite3.connect(self._db_path) as con:
            con.execute("""
                INSERT INTO audit_log (event_type, game_id, details, old_state, new_state)
                VALUES (?, ?, ?, ?, ?)
            """, (event_type, game_id, details, old_state, new_state))

    def log_bet_taken(self, game_id: str, stake: float, ev: float):
        self.log("BET_TAKEN", game_id, json.dumps({"stake": stake, "ev": ev}))

    def log_bet_blocked(self, game_id: str, reason: str):
        self.log("BET_BLOCKED", game_id, reason)

    def log_risk_trigger(self, trigger: str, details: str):
        self.log("RISK_TRIGGER", None, f"{trigger}: {details}")

    def log_state_change(self, old: str, new: str, reason: str):
        self.log("STATE_CHANGE", None, reason, old, new)

def get_audit_logger():
    return AuditLogger()
