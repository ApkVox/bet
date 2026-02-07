from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from . import config

class SeasonPhase(str, Enum):
    EARLY = "early_season"           # 0-25% of season
    MID = "mid_season"               # 25-60%
    PRE_DEADLINE = "pre_trade_deadline"  # 60-75%
    LATE = "late_season"             # 75-100%

class RiskDecision(BaseModel):
    allowed: bool = Field(..., description="Whether the bet is permitted")
    reasons: List[str] = Field(default_factory=list, description="Reasons for denial or warnings")
    aggressiveness: float = Field(default=1.0, description="Suggested stake multiplier (0-1)")

class RiskFilter:
    """
    Paranoid risk validation layer.
    Decides if a bet is ALLOWED based on configurable rules.
    """
    
    def __init__(
        self,
        min_probability: float = config.MIN_PROBABILITY,
        min_ev: float = config.MIN_EV,
        block_early_season: bool = config.BLOCK_EARLY_SEASON,
        reduce_pre_deadline: bool = config.REDUCE_PRE_TRADE_DEADLINE,
    ):
        self.min_probability = min_probability
        self.min_ev = min_ev
        self.block_early_season = block_early_season
        self.reduce_pre_deadline = reduce_pre_deadline

    def validate(
        self,
        probability: float,
        ev: float,
        season_phase: Optional[SeasonPhase] = None,
    ) -> RiskDecision:
        """
        Validate if a bet is allowed.
        
        Args:
            probability: Predicted win probability (0-1)
            ev: Expected Value from EV Engine
            season_phase: Current phase of the NBA season
            
        Returns:
            RiskDecision with allowed flag and reasons
        """
        reasons = []
        allowed = True
        aggressiveness = config.AGGRESSIVENESS_NORMAL
        
        # Rule 1: Probability Dead Zone
        dead_zone_low, dead_zone_high = config.PROBABILITY_DEAD_ZONE
        if dead_zone_low <= probability < dead_zone_high:
            allowed = False
            reasons.append(f"BLOCKED: Probability {probability:.1%} in dead zone [{dead_zone_low:.0%}-{dead_zone_high:.0%})")
        
        # Rule 2: Min Probability
        if probability < self.min_probability:
            allowed = False
            reasons.append(f"BLOCKED: Probability {probability:.1%} < min {self.min_probability:.0%}")
        
        # Rule 3: Min EV
        if ev < self.min_ev:
            allowed = False
            reasons.append(f"BLOCKED: EV {ev:.1%} < min {self.min_ev:.0%}")
        
        # Rule 4: Seasonal Flags
        if season_phase:
            if season_phase == SeasonPhase.EARLY and self.block_early_season:
                allowed = False
                aggressiveness = config.AGGRESSIVENESS_EARLY_SEASON
                reasons.append("BLOCKED: Early season (volatile W_PCT)")
            
            elif season_phase == SeasonPhase.PRE_DEADLINE and self.reduce_pre_deadline:
                aggressiveness = config.AGGRESSIVENESS_PRE_DEADLINE
                reasons.append(f"WARNING: Pre-trade deadline (aggressiveness reduced to {aggressiveness*100:.0f}%)")
        
        # Rule 5: EV must be positive (hard rule)
        if ev <= 0:
            allowed = False
            reasons.append(f"BLOCKED: Negative or zero EV ({ev:.1%})")
        
        return RiskDecision(
            allowed=allowed,
            reasons=reasons,
            aggressiveness=aggressiveness if allowed else 0.0
        )
