from datetime import datetime
import json
import logging
import sqlite3
from pathlib import Path

from src.Services.bet_pipeline import get_bet_pipeline, BetDecision
from src.BankrollEngine.service import get_bankroll_service

logger = logging.getLogger("ShadowBettor")

class ShadowBettor:
    """
    Executes betting decisions in 'Paper Trading' mode.
    Uses BetPipeline to decide, but only logs to 'shadow_bets' table.
    """
    
    def __init__(self):
        self.pipeline = get_bet_pipeline()
        self.bankroll_service = get_bankroll_service() # Need DB access
        # Ensure DB is init
        self._db_path = self.bankroll_service.db_path

    def process_game(self, game_id: str, probability: float, odds: float, game_date: datetime) -> BetDecision:
        """
        Run pipeline and log result to shadow ledger.
        """
        # 1. Run Core Pipeline
        decision = self.pipeline.process_bet(game_id, probability, odds, game_date)
        
        # 2. Log to Shadow Table (Side Effect)
        self._log_shadow_bet(decision, probability, odds)
        
        return decision

    def _log_shadow_bet(self, d: BetDecision, prob: float, odds: float):
        """Persist decision to SQLite."""
        try:
            with sqlite3.connect(self._db_path) as con:
                # Extract EV if available
                ev = d.ev_result.ev if d.ev_result else 0.0
                
                # Extract Kelly from StakeResult if available, else infer/default
                kelly = 0.0
                if d.stake_result:
                    kelly = d.stake_result.kelly_fraction
                
                con.execute("""
                    INSERT INTO shadow_bets (
                        game_id, decision, probability, odds, ev, 
                        stake_units, kelly_fraction, status, reason
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    d.game_id, 
                    d.decision, 
                    prob, 
                    odds, 
                    ev,
                    d.stake_units,
                    kelly,
                    "PENDING", # Always pending until graded
                    d.reason
                ))
                logger.info(f"Shadow Bet Logged: {d.game_id} -> {d.decision}")
                
        except Exception as e:
            logger.error(f"Failed to log shadow bet for {d.game_id}: {str(e)}")

# Global Accessor
def get_shadow_bettor():
    return ShadowBettor()
