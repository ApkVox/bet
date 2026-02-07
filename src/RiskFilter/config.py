# Risk Filter Configuration
# Centralized settings for bet validation rules

# Probability thresholds
MIN_PROBABILITY = 0.55  # Minimum predicted probability to consider a bet
PROBABILITY_DEAD_ZONE = (0.50, 0.55)  # Range where bets are BLOCKED

# EV thresholds
MIN_EV = 0.03  # Minimum Expected Value (3%) to allow a bet

# Seasonal risk flags
BLOCK_EARLY_SEASON = True  # Completely block bets in early season (volatile W_PCT)
REDUCE_PRE_TRADE_DEADLINE = True  # Reduce aggressiveness near trade deadline

# Aggressiveness modifiers (multiplier for Kelly stake)
AGGRESSIVENESS_NORMAL = 1.0
AGGRESSIVENESS_PRE_DEADLINE = 0.5  # 50% reduction during uncertainty
AGGRESSIVENESS_EARLY_SEASON = 0.0  # Complete block

# Max single bet exposure (as % of bankroll, optional future use)
MAX_SINGLE_BET_EXPOSURE = 0.05  # 5% of bankroll max
