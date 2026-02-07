# Stake Engine Configuration
# Kelly Criterion parameters for position sizing

# Fractional Kelly (reduces variance at cost of growth)
FRACTIONAL_KELLY = 0.25  # Use 25% of Kelly-optimal stake

# Maximum stake limits
MAX_STAKE_PERCENT = 0.05  # Max 5% of bankroll per bet
MIN_STAKE_UNITS = 0.01  # Minimum stake (ignore bets below this)

# Safety multiplier from Risk Filter (applied externally)
# This is just for reference, actual value comes from RiskFilter
DEFAULT_AGGRESSIVENESS = 1.0
