from datetime import datetime
from typing import Optional, Tuple
import logging

from src.BankrollEngine.service import get_bankroll_service
from src.RiskFilter.filter import RiskFilter, SeasonPhase, RiskDecision

logger = logging.getLogger("RiskGuard")

class RiskGuard:
    """
    Final Gatekeeper for betting operations.
    Enforces Phase 4 'Hard Rules' that cannot be bypassed via config.
    """
    
    def __init__(self):
        self.bankroll_service = get_bankroll_service()
        # Initialize RiskFilter with defaults, but we will enforce overrides here
        self.risk_filter = RiskFilter() 

    def _determine_phase(self, game_date: datetime) -> SeasonPhase:
        """
        Hard-coded season phases based on typical NBA calendar (Oct-April).
        Mid-season starts ~Dec 25. Pre-deadline ~Feb 1. Late ~Mar 15.
        """
        # Simplify: mapped by month for robustness
        # Early: Oct, Nov, Dec (start) -> 0 - 25%
        # Mid: Jan, Feb (start) -> 25 - 60%
        # Pre-Deadline: Feb (end) -> 60 - 75%
        # Late: Mar, Apr -> 75 - 100%
        
        m = game_date.month
        d = game_date.day
        
        if m in [10, 11]:
            return SeasonPhase.EARLY
        if m == 12:
            return SeasonPhase.EARLY if d < 25 else SeasonPhase.MID
        if m == 1:
            return SeasonPhase.MID
        if m == 2:
            return SeasonPhase.PRE_DEADLINE
        if m in [3, 4]:
            return SeasonPhase.LATE
            
        return SeasonPhase.MID # Default for playoffs/other

    def validate_bet(self, probability: float, ev: float, game_date: datetime) -> RiskDecision:
        """
        Main validation entry point.
        """
        # 1. Circuit Breaker Check (Bankroll Status)
        status = self.bankroll_service.operational_status
        if status == "PAUSED":
            return RiskDecision(
                allowed=False,
                reasons=["CIRCUIT BREAKER: System is PAUSED due to consecutive losses or severe drawdown."],
                aggressiveness=0.0
            )

        # 2. Hard Rule: Early Season Block
        phase = self._determine_phase(game_date)
        if phase == SeasonPhase.EARLY:
            # Overrule config: ALWAYS BLOCK
            return RiskDecision(
                allowed=False,
                reasons=["HARD RULE: Early Season bets are strictly prohibited (Oct-Dec 25)."],
                aggressiveness=0.0
            )

        # 3. Standard Risk Filter
        decision = self.risk_filter.validate(probability, ev, phase)
        
        # 4. Bankroll Degradation Logic
        if decision.allowed and status == "DEGRADED":
            # Force reduce aggressiveness logic if not already handled entirely by BankrollService kelly fraction
            # BankrollService.kelly_fraction gives the FRACTION.
            # Here we just pass the decision mostly.
            # But we can annotate the reason.
            decision.reasons.append("WARNING: Operating in DEGRADED mode (Drawdown > 20%).")
            
        return decision

# Function to get singleton/service
def get_risk_guard():
    return RiskGuard()
