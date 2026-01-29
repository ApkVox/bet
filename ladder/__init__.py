"""
Ladder - Autonomous Ladder Challenge System
============================================
A self-healing betting system that:
1. Selects optimal daily parlays using ML predictions
2. Validates bets using Groq AI
3. Automatically resolves bets and updates bankroll
"""

from .groq_agent import GroqAgent, get_groq_agent
from .strategy_engine import (
    BankrollManager,
    BetSelector,
    Strategy,
    MatchCandidate,
    ParlayTicket,
    create_strategy_engine
)
from .main_ladder import (
    LadderOrchestrator,
    DailyResolution,
    create_ladder_orchestrator
)

__all__ = [
    "GroqAgent",
    "get_groq_agent",
    "BankrollManager",
    "BetSelector",
    "Strategy",
    "MatchCandidate",
    "ParlayTicket",
    "create_strategy_engine",
    "LadderOrchestrator",
    "DailyResolution",
    "create_ladder_orchestrator"
]

__version__ = "2.0.0"
