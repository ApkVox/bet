from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import logging

# Services
from src.EVEngine.ev_calculator import calculate_ev, EVResult
from src.Services.risk_guard import get_risk_guard, RiskDecision
from src.BankrollEngine.service import get_bankroll_service
from src.StakeEngine.calculator import calculate_stake, StakeResult

# Configure logging
logger = logging.getLogger("BetPipeline")

class BetDecision(BaseModel):
    """Final decision output from the pipeline."""
    game_id: str
    decision: str = Field(..., description="BET, PASS, or BLOCKED")
    stake_units: float = 0.0
    ev_result: Optional[EVResult] = None
    risk_decision: Optional[RiskDecision] = None
    stake_result: Optional[StakeResult] = None
    reason: str = ""

class BetPipeline:
    """
    Immutable Decision Pipeline.
    Order: Prediction -> EV -> Risk Guard -> Bankroll Status -> Stake Engine -> Final Decision.
    """
    
    def __init__(self):
        self.risk_guard = get_risk_guard()
        self.bankroll_service = get_bankroll_service()
        
    def process_bet(self, game_id: str, probability: float, odds: float, game_date: datetime) -> BetDecision:
        """
        Execute the betting decision pipeline step-by-step.
        """
        logger.info(f"Processing Game {game_id} | Prob: {probability:.1%} | Odds: {odds:.2f}")
        
        # 1. Probability Gate (Sanity Check)
        if not (0.0 <= probability <= 1.0):
            return self._pass(game_id, f"Invalid probability: {probability}")
            
        if odds <= 1.0:
            return self._pass(game_id, f"Invalid odds: {odds}")

        # 2. EV Engine (Value Check)
        try:
            ev_res = calculate_ev(probability, odds)
        except ValueError as e:
            return self._pass(game_id, f"EV Error: {str(e)}")
            
        # Hard Rule: EV must be positive and meet minimum
        # Note: RiskGuard also checks min_ev, but we can fail fast here if needed.
        # However, RiskGuard is the central authority for thresholds. 
        # But user requirement says: EV Engine (EV >= 0.03) -> Risk Filter
        # Let's let RiskGuard enforce the 0.03 threshold to keep config central.
        # But we MUST reject if EV <= 0 strictly.
        if ev_res.ev <= 0:
             return self._pass(game_id, f"Negative Value: EV {ev_res.ev:.1%}", ev_res=ev_res)

        # 3. Risk Guard (Risk Filter + Circuit Breakers + Early Season)
        # This wraps RiskFilter and checks Bankroll Status (PAUSED) internally
        risk_decision = self.risk_guard.validate_bet(probability, ev_res.ev, game_date)
        
        if not risk_decision.allowed:
            return self._block(game_id, risk_decision.reasons, ev_res, risk_decision)

        # 4. Bankroll State & Stake Engine
        # Get current bankroll for sizing
        bankroll_state = self.bankroll_service.get_state()
        
        # Double check status just in case (redundant but safe)
        if bankroll_state.status == "PAUSED":
             return self._block(game_id, ["CIRCUIT BREAKER: Bankroll Paused"], ev_res, risk_decision)
             
        # Calculate Stake
        # Note: BankrollService handles the Kelly Fraction logic (Active vs Degraded)
        # But calculate_stake accepts fractional_kelly as arg.
        # We must pull the ACTIVE fraction from BankrollService state.
        
        active_kelly_fraction = bankroll_state.kelly_fraction
        
        stake_res = calculate_stake(
            probability=probability,
            odds=odds,
            bankroll=bankroll_state.current_units,
            fractional_kelly=active_kelly_fraction,
            aggressiveness=risk_decision.aggressiveness
        )
        
        # 5. Final validation of Stake
        if stake_res.recommended_stake <= 0:
            return self._pass(game_id, "Zero Stake Recommended (Min allowed or Kelly <= 0)", ev_res, risk_decision, stake_res)
            
        # 6. BET / GO
        return BetDecision(
            game_id=game_id,
            decision="BET",
            stake_units=stake_res.recommended_stake,
            ev_result=ev_res,
            risk_decision=risk_decision,
            stake_result=stake_res,
            reason=f"Approved. EV: {ev_res.ev:.1%}, Stake: {stake_res.recommended_stake}U"
        )

    def _pass(self, game_id, reason, ev_res=None, risk_decision=None, stake_res=None):
        return BetDecision(
            game_id=game_id,
            decision="PASS",
            reason=reason,
            ev_result=ev_res,
            risk_decision=risk_decision,
            stake_result=stake_res
        )

    def _block(self, game_id, reasons, ev_res=None, risk_decision=None):
        return BetDecision(
            game_id=game_id,
            decision="BLOCKED",
            reason=" | ".join(reasons),
            ev_result=ev_res,
            risk_decision=risk_decision
        )

# Global Accessor
def get_bet_pipeline():
    return BetPipeline()
