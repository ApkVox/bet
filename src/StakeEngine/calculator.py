from typing import Optional
from pydantic import BaseModel, Field

from . import config

class StakeResult(BaseModel):
    kelly_fraction: float = Field(..., description="Raw Kelly fraction (f*)")
    recommended_stake: float = Field(..., description="Final stake in units after all adjustments")
    stake_percent: float = Field(..., description="Stake as percentage of bankroll")
    was_capped: bool = Field(default=False, description="True if stake was capped by max limit")
    was_zeroed: bool = Field(default=False, description="True if stake was forced to 0 due to negative edge")

def calculate_kelly(probability: float, odds: float) -> float:
    """
    Calculate raw Kelly fraction.
    
    Formula: f* = (P * odds - 1) / (odds - 1)
    
    This represents the optimal fraction of bankroll to wager.
    """
    if odds <= 1.0:
        return 0.0
    
    numerator = (probability * odds) - 1
    denominator = odds - 1
    
    kelly = numerator / denominator
    return kelly

def calculate_stake(
    probability: float,
    odds: float,
    bankroll: float,
    fractional_kelly: float = config.FRACTIONAL_KELLY,
    max_stake_percent: float = config.MAX_STAKE_PERCENT,
    aggressiveness: float = 1.0,
) -> StakeResult:
    """
    Calculate stake using Fractional Kelly Criterion.
    
    Args:
        probability: Predicted win probability (0-1)
        odds: Decimal odds (e.g., 1.90, 2.50)
        bankroll: Current bankroll in units
        fractional_kelly: Fraction of Kelly to use (0.25 = quarter Kelly)
        max_stake_percent: Maximum stake as % of bankroll (e.g., 0.05 = 5%)
        aggressiveness: Multiplier from Risk Filter (0-1)
        
    Returns:
        StakeResult with recommended stake and metadata
    """
    # Calculate raw Kelly
    kelly = calculate_kelly(probability, odds)
    
    was_zeroed = False
    was_capped = False
    
    # Hard rule: Negative or zero Kelly = no bet
    if kelly <= 0:
        was_zeroed = True
        return StakeResult(
            kelly_fraction=kelly,
            recommended_stake=0.0,
            stake_percent=0.0,
            was_capped=False,
            was_zeroed=True
        )
    
    # Apply fractional Kelly
    fractional_stake = kelly * fractional_kelly
    
    # Apply aggressiveness from Risk Filter
    adjusted_stake = fractional_stake * aggressiveness
    
    # Convert to units
    stake_units = bankroll * adjusted_stake
    
    # Apply max cap
    max_stake_units = bankroll * max_stake_percent
    if stake_units > max_stake_units:
        stake_units = max_stake_units
        was_capped = True
    
    # Apply minimum threshold
    if stake_units < config.MIN_STAKE_UNITS:
        stake_units = 0.0
        was_zeroed = True
    
    # Ensure non-negative
    stake_units = max(0.0, stake_units)
    
    # Calculate final percentage
    stake_percent = stake_units / bankroll if bankroll > 0 else 0.0
    
    return StakeResult(
        kelly_fraction=kelly,
        recommended_stake=round(stake_units, 4),
        stake_percent=round(stake_percent, 6),
        was_capped=was_capped,
        was_zeroed=was_zeroed
    )
