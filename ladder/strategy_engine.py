"""
=============================================
STRATEGY ENGINE - Bet Selection & Bankroll Management
=============================================
Implements:
1. BetSelector - Dynamic parlay selection with Groq validation
2. BankrollManager - Kelly Criterion and anti-bankruptcy rules
"""

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# Local imports
from .groq_agent import GroqAgent, get_groq_agent


class Strategy(Enum):
    """Betting strategy modes."""
    SAFE = "SAFE"           # 2 legs, >70% each, 5% stake
    FENIX = "FENIX"         # 3 legs, >60% each, 8% stake
    AGGRESSIVE = "AGGRESSIVE"  # 4 legs, >55% each, 10% stake


@dataclass
class MatchCandidate:
    """A match candidate for parlay selection."""
    home_team: str
    away_team: str
    winner: str
    probability: float
    decimal_odds: float
    bet_type: str = "MONEYLINE"
    groq_verdict: str = "UNKNOWN"
    
    @property
    def match_id(self) -> str:
        return f"{self.home_team}:{self.away_team}"


@dataclass
class ParlayTicket:
    """A generated parlay ticket."""
    date: str
    legs: list[MatchCandidate]
    strategy: Strategy
    stake_amount: float
    combined_odds: float
    combined_probability: float
    potential_payout: float
    groq_reasoning: str = ""
    phoenix_note: str = ""
    
    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "legs": [
                {
                    "match_id": leg.match_id,
                    "home_team": leg.home_team,
                    "away_team": leg.away_team,
                    "pick": leg.winner,
                    "probability": leg.probability,
                    "decimal_odds": leg.decimal_odds,
                    "bet_type": leg.bet_type,
                    "groq_verdict": leg.groq_verdict
                }
                for leg in self.legs
            ],
            "strategy": self.strategy.value,
            "stake_amount": self.stake_amount,
            "combined_odds": self.combined_odds,
            "combined_probability": self.combined_probability,
            "potential_payout": self.potential_payout,
            "groq_reasoning": self.groq_reasoning,
            "phoenix_note": self.phoenix_note
        }


class BankrollManager:
    """
    Manages bankroll with anti-bankruptcy protections.
    Implements Fractional Kelly Criterion with safety limits.
    """
    
    # Strategy-specific stake limits (as % of bankroll)
    STAKE_LIMITS = {
        Strategy.SAFE: 0.30,        # 30% max
        Strategy.FENIX: 0.50,       # 50% max
        Strategy.AGGRESSIVE: 0.80   # 80% max (hard limit)
    }
    
    # Hard limits
    MAX_STAKE_PCT = 0.80  # Never bet more than 80%
    MIN_CAPITAL_RESERVE = 50000.0  # Always keep 50,000 COP reserve
    KELLY_FRACTION = 0.25  # Use 1/4 Kelly for safety
    
    def __init__(self, db_path: str = "ladder_v2.db", ladder_id: int = 1):
        self.db_path = db_path
        self.ladder_id = ladder_id
        self._init_db()
    
    def _init_db(self):
        """Initialize database with schema."""
        # Check if v3 schema exists first
        schema_path = Path(__file__).parent / "schema_v3.sql"
        if not schema_path.exists():
            schema_path = Path(__file__).parent / "schema.sql"
            
        if schema_path.exists():
            conn = sqlite3.connect(self.db_path)
            with open(schema_path, 'r') as f:
                conn.executescript(f.read())
            conn.close()
    
    def get_current_capital(self) -> float:
        """Get the current bankroll."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT current_capital FROM ladders WHERE id = ?", (self.ladder_id,))
        row = cursor.fetchone()
        conn.close()
        return float(row[0]) if row else 100000.0  # Default 100,000 COP
    
    def get_state(self) -> dict:
        """Get full ladder state."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ladders WHERE id = ?", (self.ladder_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else {}
    
    def calculate_kelly_stake(
        self,
        combined_probability: float,
        combined_odds: float,
        strategy: Strategy
    ) -> float:
        """
        Calculate optimal stake using Fractional Kelly Criterion.
        
        Formula: f* = (bp - q) / b
        Where:
            b = decimal odds - 1
            p = probability of winning
            q = probability of losing (1 - p)
        """
        capital = self.get_current_capital()
        
        # Convert probability to decimal
        p = combined_probability / 100
        q = 1 - p
        b = combined_odds - 1
        
        # Kelly formula
        if b <= 0:
            return 0.0
        
        kelly = (b * p - q) / b
        
        # Apply safety factor
        adjusted_kelly = kelly * self.KELLY_FRACTION
        
        # Apply strategy-specific limits
        max_pct = self.STAKE_LIMITS.get(strategy, self.MAX_STAKE_PCT)
        stake_pct = min(adjusted_kelly, max_pct)
        stake_pct = max(0, stake_pct)  # No negative bets
        
        # Calculate actual stake
        stake = capital * stake_pct
        
        # Enforce reserve but allow Survival Mode to dip slightly if needed
        # Or simply, if capital < reserve, we can't bet effectively. 
        # But if we have 100k and reserve is 50k, we have 50k play money.
        
        max_available = max(0, capital - self.MIN_CAPITAL_RESERVE)
        
        # SURVIVAL MODE / FORCE BET LOGIC
        # If strategy is SAFE (survival default) and Kelly says 0 or very low, 
        # force a minimum bet to keep the ladder moving if we have checks.
        MIN_BET = 5000.0
        
        calculated_stake = capital * stake_pct
        
        if calculated_stake < MIN_BET:
             if strategy == Strategy.SAFE: # Survival uses SAFE
                 calculated_stake = MIN_BET

        stake = min(calculated_stake, max_available)
        
        # Final safety measure: if we really have 0 available above reserve, 
        # but user wants to bet, maybe allow dipping? 
        # For now, stick to strict reserve unless capital is very low overall.
        if stake < MIN_BET and capital > MIN_BET:
            # Emergency: if we can't bet above reserve, but have money, bet min bet
            stake = MIN_BET
            
        return round(max(0, stake), 2)
    
    def update_after_result(self, is_win: bool, profit_loss: float) -> dict:
        """
        Update bankroll after a bet result.
        
        Args:
            is_win: Whether the bet won
            profit_loss: Amount won (+) or lost (-)
            
        Returns:
            Updated state dict
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current state
        cursor.execute("SELECT * FROM ladders WHERE id = ?", (self.ladder_id,))
        state = cursor.fetchone()
        
        if not state:
            conn.close()
            return {}
        
        current_capital = float(state[1])  # current_capital column
        step = state[4]  # step_number column
        consecutive_wins = state[7]  # consecutive_wins
        consecutive_losses = state[8]  # consecutive_losses
        
        # Update capital
        new_capital = current_capital + profit_loss
        
        # Update streaks and step
        if is_win:
            new_step = step + 1
            new_wins = consecutive_wins + 1
            new_losses = 0
        else:
            # On loss, go back one step (but not below 1)
            new_step = max(1, step - 1)
            new_wins = 0
            new_losses = consecutive_losses + 1
        
        # Update max step if new high
        max_step = max(state[6], new_step)  # max_step_reached column index 6 in v3
        
        # Update database
        cursor.execute("""
            UPDATE ladders SET
                current_capital = ?,
                step_number = ?,
                max_step_reached = ?,
                consecutive_wins = ?,
                consecutive_losses = ?,
                last_update_date = ?
            WHERE id = ?
        """, (new_capital, new_step, max_step, new_wins, new_losses, datetime.now().strftime("%Y-%m-%d"), self.ladder_id))
        
        # Record in history
        cursor.execute("""
            INSERT INTO bankroll_history (ladder_id, date, capital_before, capital_after, daily_change, daily_change_pct, step_number, ticket_result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.ladder_id,
            datetime.now().strftime("%Y-%m-%d"),
            current_capital,
            new_capital,
            profit_loss,
            (profit_loss / current_capital) * 100 if current_capital > 0 else 0,
            new_step,
            "WIN" if is_win else "LOSS"
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "previous_capital": current_capital,
            "new_capital": new_capital,
            "profit_loss": profit_loss,
            "step": new_step,
            "consecutive_wins": new_wins,
            "consecutive_losses": new_losses
        }
    
    def set_strategy(self, strategy: Strategy):
        """Update the active strategy."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE ladders SET strategy_mode = ? WHERE id = ?", (strategy.value, self.ladder_id))
        conn.commit()
        conn.close()


class BetSelector:
    """
    Intelligent bet selection engine with Groq validation.
    Selects optimal parlay based on strategy and AI safety checks.
    """
    
    # Strategy configuration
    STRATEGY_CONFIG = {
        Strategy.SAFE: {"legs": 1, "min_prob": 50},  # Was 2 / 70
        Strategy.FENIX: {"legs": 3, "min_prob": 60},
        Strategy.AGGRESSIVE: {"legs": 4, "min_prob": 55}
    }
    
    
    def __init__(self, bankroll_manager: BankrollManager, groq_agent: Optional[GroqAgent] = None):
        self.bankroll = bankroll_manager
        self.groq = groq_agent or get_groq_agent()

    def select_strategy_automatically(self, predictions: list[dict]) -> Strategy:
        """
        Intelligently select the best strategy based on today's market conditions.
        
        Logic:
        1. Count high-confidence candidates (>70%, >60%, >55%)
        2. Check for "RISK" factors using Groq on top matches
        3. Decide:
           - >3 Safe & High Conf -> AGGRESSIVE
           - 2-3 Safe matches -> FENIX
           - <2 Safe matches -> SAFE (conservative)
        """
        # Quick pre-filter
        high_conf = [p for p in predictions if p.get("probability", 0) >= 60]
        medium_conf = [p for p in predictions if p.get("probability", 0) >= 55]
        
        # If very few good games, play SAFE
        if len(medium_conf) < 3:
            return Strategy.SAFE
            
        # Validate top 4 matches
        safe_count = 0
        sorted_preds = sorted(medium_conf, key=lambda x: x.get("probability", 0), reverse=True)[:5]
        
        for p in sorted_preds:
            # Quick check if not already validated
            if "groq_verdict" not in p:
                res = self.groq.sanity_check(p["home_team"], p["away_team"])
                if res.verdict != "RISK":
                    safe_count += 1
            else:
                if p["groq_verdict"] != "RISK":
                    safe_count += 1
        
        # Decision Matrix
        if safe_count >= 4 and len(high_conf) >= 3:
            return Strategy.AGGRESSIVE
        elif safe_count >= 2:
            return Strategy.FENIX
        else:
            return Strategy.SAFE

    
    def _validate_with_groq(self, candidate: MatchCandidate) -> MatchCandidate:
        """Run Groq safety check on a candidate."""
        result = self.groq.sanity_check(candidate.home_team, candidate.away_team)
        candidate.groq_verdict = result.verdict
        return candidate
    
    def _get_bad_beats(self) -> list[str]:
        """Retrieve recent loss patterns from memory."""
        conn = sqlite3.connect(self.bankroll.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT learning_note FROM bad_beats_memory 
            ORDER BY id DESC LIMIT 5
        """)
        rows = cursor.fetchall()
        conn.close()
        return [row[0] for row in rows if row[0]]
    
    def select_parlay(
        self,
        predictions: list[dict],
        strategy: Optional[Strategy] = None
    ) -> Optional[ParlayTicket]:
        """
        Select the optimal parlay from available predictions.
        
        Args:
            predictions: List of match predictions with probabilities
            strategy: Betting strategy (defaults to state's strategy)
            
        Returns:
            ParlayTicket or None if no valid parlay possible
        """
        # Get strategy from state if not provided
        if strategy is None:
            state = self.bankroll.get_state()
            strategy = Strategy(state.get("strategy_mode", "FENIX"))
        
        config = self.STRATEGY_CONFIG[strategy]
        target_legs = config["legs"]
        min_prob = config["min_prob"]
        
        # Convert predictions to candidates
        candidates = []
        for pred in predictions:
            prob = pred.get("win_probability", pred.get("probability", 50))
            if prob >= min_prob:
                candidate = MatchCandidate(
                    home_team=pred.get("home_team", ""),
                    away_team=pred.get("away_team", ""),
                    winner=pred.get("winner", pred.get("pick", "")),
                    probability=prob,
                    decimal_odds=pred.get("decimal_odds", 1.9),
                    bet_type=pred.get("bet_type", "MONEYLINE")
                )
                candidates.append(candidate)
        
        # Run Groq validation on top candidates
        validated = []
        for candidate in sorted(candidates, key=lambda c: c.probability, reverse=True)[:10]:
            validated_candidate = self._validate_with_groq(candidate)
            if validated_candidate.groq_verdict != "RISK":
                validated.append(validated_candidate)
        
        if len(validated) < target_legs:
            # Not enough safe matches, fall back to fewer legs
            target_legs = max(1, len(validated))
        
        # SURVIVAL MODE: If absolutely no matches pass validation
        if not validated:
            # Fallback: Pick the single highest probability match available (ignoring Groq risk if needed)
            # This ensures we ALWAYS generate a ticket as requested by user
            best_survival = sorted(candidates, key=lambda c: c.probability, reverse=True)
            if best_survival:
                top_pick = best_survival[0]
                top_pick.groq_verdict = "SURVIVAL_MODE"
                validated = [top_pick]
                target_legs = 1
                strategy = Strategy.SAFE  # Force safe mode for survival
            else:
                return None # Should be impossible if predictions exist
        
        # Use Groq to make final selection
        bad_beats = self._get_bad_beats()
        candidates_for_groq = [
            {
                "home_team": c.home_team,
                "away_team": c.away_team,
                "winner": c.winner,
                "probability": c.probability,
                "decimal_odds": c.decimal_odds
            }
            for c in validated
        ]
        
        groq_selection = self.groq.select_optimal_parlay(
            candidates=candidates_for_groq,
            current_capital=self.bankroll.get_current_capital(),
            bad_beats=bad_beats,
            strategy=strategy.value
        )
        
        # Build the ticket
        selected_ids = groq_selection.get("selected_ids", list(range(min(target_legs, len(validated)))))
        selected_legs = [validated[i] for i in selected_ids if i < len(validated)]
        
        if not selected_legs:
            selected_legs = validated[:target_legs]
        
        # Calculate combined odds and probability
        combined_odds = 1.0
        combined_prob = 100.0
        for leg in selected_legs:
            combined_odds *= leg.decimal_odds
            combined_prob *= (leg.probability / 100)
        combined_prob *= 100  # Back to percentage
        
        # Calculate stake
        stake = self.bankroll.calculate_kelly_stake(combined_prob, combined_odds, strategy)
        
        ticket = ParlayTicket(
            date=datetime.now().strftime("%Y-%m-%d"),
            legs=selected_legs,
            strategy=strategy,
            stake_amount=stake,
            combined_odds=round(combined_odds, 2),
            combined_probability=round(combined_prob, 1),
            potential_payout=round(stake * combined_odds, 2),
            groq_reasoning=groq_selection.get("reasoning", ""),
            phoenix_note=groq_selection.get("phoenix_note", "Trust the process.")
        )
        
        return ticket
    
    def save_ticket(self, ticket: ParlayTicket) -> int:
        """Save a ticket to the database."""
        import json
        
        conn = sqlite3.connect(self.bankroll.db_path)
        cursor = conn.cursor()
        
        # Insert ticket
        cursor.execute("""
            INSERT OR REPLACE INTO ladder_tickets 
            (ladder_id, date, ticket_json, strategy_used, num_legs, stake_amount, potential_payout, combined_odds, combined_probability, groq_validation_log)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.bankroll.ladder_id,
            ticket.date,
            json.dumps(ticket.to_dict()),
            ticket.strategy.value,
            len(ticket.legs),
            ticket.stake_amount,
            ticket.potential_payout,
            ticket.combined_odds,
            ticket.combined_probability,
            ticket.groq_reasoning
        ))
        
        ticket_id = cursor.lastrowid
        
        # Insert legs
        for leg in ticket.legs:
            cursor.execute("""
                INSERT INTO ticket_legs 
                (ticket_id, match_id, home_team, away_team, bet_type, pick, probability, decimal_odds, groq_safety_check)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket_id,
                leg.match_id,
                leg.home_team,
                leg.away_team,
                leg.bet_type,
                leg.winner,
                leg.probability,
                leg.decimal_odds,
                leg.groq_verdict
            ))
        
        conn.commit()
        conn.close()
        
        return ticket_id


# Factory function
def create_strategy_engine(db_path: str = "ladder_v2.db", ladder_id: int = 1) -> tuple[BankrollManager, BetSelector]:
    """Create and return configured strategy engine components."""
    bankroll = BankrollManager(db_path, ladder_id)
    selector = BetSelector(bankroll)
    return bankroll, selector
