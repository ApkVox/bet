from typing import Dict, Any, Union
from pydantic import BaseModel, Field

class EVResult(BaseModel):
    probability: float = Field(..., ge=0.0, le=1.0, description="Predicted probability of winning (0-1)")
    odds: float = Field(..., gt=1.0, description="Decimal odds offered by the market")
    ev: float = Field(..., description="Expected Value (percentage as decimal, e.g., 0.05 for 5%)")
    is_value_bet: bool = Field(..., description="True if EV > 0")
    
    def __str__(self):
        return f"EV: {self.ev:.2%} | Value: {self.is_value_bet} (Prob: {self.probability:.1%}, Odds: {self.odds:.2f})"

def calculate_ev(probability: float, odds: float) -> EVResult:
    """
    Calculate Expected Value (EV) for a single bet.
    
    Formula: EV = (Probability * Odds) - 1
    
    Args:
        probability (float): Predicted probability of winning (0 to 1).
        odds (float): Decimal odds (e.g., 1.90, 2.50). Must be > 1.0.
        
    Returns:
        EVResult: Object containing calculations and value bet classification.
        
    Raises:
        ValueError: If probability is out of range or odds <= 1.0.
    """
    if not (0.0 <= probability <= 1.0):
        # Allow slight float precision errors if needed, but strict for now
        raise ValueError(f"Probability must be between 0 and 1. Got {probability}")
        
    if odds <= 1.0:
        raise ValueError(f"Odds must be greater than 1.0. Got {odds}")
        
    # EV Calculation
    # P(Win) * (Odds - 1) - P(Loss) * 1
    # = P * Odds - P - (1 - P)
    # = P * Odds - P - 1 + P
    # = P * Odds - 1
    ev = (probability * odds) - 1
    
    is_value_bet = ev > 0
    
    return EVResult(
        probability=probability,
        odds=odds,
        ev=ev,
        is_value_bet=is_value_bet
    )
