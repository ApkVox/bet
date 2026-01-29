"""
=============================================
MAIN LADDER - Daily Cycle Orchestrator
=============================================
The brain of Project Phoenix. Runs the daily cycle:
1. Resolve yesterday's bets
2. Generate today's parlay
3. Update bankroll and progress
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Conditional imports for when run standalone vs as module
try:
    from .groq_agent import GroqAgent, get_groq_agent
    from .strategy_engine import BankrollManager, BetSelector, Strategy, create_strategy_engine
except ImportError:
    from groq_agent import GroqAgent, get_groq_agent
    from strategy_engine import BankrollManager, BetSelector, Strategy, create_strategy_engine


class DailyResolution:
    """
    Service that resolves pending bets by checking actual game results.
    Uses the history service to get real scores.
    """
    
    def __init__(self, db_path: str = "ladder_v2.db"):
        self.db_path = db_path
    
    def get_pending_tickets(self) -> list[dict]:
        """Get all tickets that need resolution across all ladders."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM ladder_tickets 
            WHERE status = 'PENDING' 
            AND date < ?
        """, (datetime.now().strftime("%Y-%m-%d"),))
        
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_ticket_legs(self, ticket_id: int) -> list[dict]:
        """Get all legs for a ticket."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM ticket_legs WHERE ticket_id = ?", (ticket_id,))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def resolve_ticket(self, ticket_id: int, results: dict[str, str]) -> dict:
        """
        Resolve a single ticket based on actual results.
        
        Args:
            ticket_id: The ticket to resolve
            results: Dict of match_id -> actual_winner
            
        Returns:
            Resolution summary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get ticket
        cursor.execute("SELECT * FROM ladder_tickets WHERE id = ?", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            conn.close()
            return {"error": "Ticket not found"}
            
        ladder_id = ticket[1] # ladder_id column
        stake = ticket[5]  # stake_amount
        combined_odds = ticket[7]  # combined_odds
        
        # Get and update legs
        cursor.execute("SELECT * FROM ticket_legs WHERE ticket_id = ?", (ticket_id,))
        legs = cursor.fetchall()
        
        all_legs_won = True
        leg_results = []
        
        for leg in legs:
            leg_id = leg[0]
            match_id = leg[2]
            pick = leg[5]  # Our predicted winner
            
            actual = results.get(match_id)
            leg_result = "PENDING"
            
            if actual:
                if actual == pick:
                    leg_result = "WIN"
                else:
                    leg_result = "LOSS"
                    all_legs_won = False
                
                cursor.execute("""
                    UPDATE ticket_legs 
                    SET actual_winner = ?, leg_result = ?
                    WHERE id = ?
                """, (actual, leg_result, leg_id))
            
            leg_results.append({
                "match_id": match_id,
                "pick": pick,
                "actual": actual,
                "result": leg_result
            })
        
        # Calculate profit/loss
        if all_legs_won:
            profit_loss = (stake * combined_odds) - stake
            ticket_status = "WIN"
        else:
            profit_loss = -stake
            ticket_status = "LOSS"
        
        # Update ticket
        cursor.execute("""
            UPDATE ladder_tickets
            SET status = ?, profit_loss = ?, actual_result_json = ?, resolved_at = ?
            WHERE id = ?
        """, (ticket_status, profit_loss, json.dumps(leg_results), datetime.now().isoformat(), ticket_id))
        
        conn.commit()
        conn.close()
        
        return {
            "ticket_id": ticket_id,
            "ladder_id": ladder_id,
            "status": ticket_status,
            "profit_loss": profit_loss,
            "legs": leg_results
        }
    
    def auto_resolve_from_history(self, history_db_path: str = "history.db") -> list[dict]:
        """
        Automatically resolve pending tickets using the history database.
        
        Args:
            history_db_path: Path to the predictions history database
            
        Returns:
            List of resolution results
        """
        pending = self.get_pending_tickets()
        if not pending:
            return []
        
        # Get actual results from history DB
        results_map = {}
        
        try:
            hist_conn = sqlite3.connect(history_db_path)
            hist_cursor = hist_conn.cursor()
            
            for ticket in pending:
                ticket_date = ticket["date"]
                
                # Query actual results
                hist_cursor.execute("""
                    SELECT match_id, actual_winner 
                    FROM predictions 
                    WHERE date = ? AND result != 'PENDING'
                """, (ticket_date,))
                
                for row in hist_cursor.fetchall():
                    match_id = row[0]
                    actual_winner = row[1]
                    if actual_winner:
                        results_map[match_id] = actual_winner
            
            hist_conn.close()
        except Exception as e:
            print(f"[DailyResolution] Error reading history: {e}")
        
        # Resolve each pending ticket
        resolutions = []
        for ticket in pending:
            result = self.resolve_ticket(ticket["id"], results_map)
            resolutions.append(result)
        
        return resolutions


class LadderOrchestrator:
    """
    Main orchestrator that runs the daily ladder cycle.
    """
    
    def __init__(self, db_path: str = "ladder_v2.db", ladder_id: int = 1):
        self.db_path = Path(db_path)
        self.ladder_id = ladder_id
        self.bankroll_manager, self.bet_selector = create_strategy_engine(str(self.db_path), ladder_id)
        self.resolution_service = DailyResolution(str(self.db_path))
        self.groq = get_groq_agent()
    
    def switch_ladder(self, ladder_id: int):
        """Switch context to another ladder."""
        self.ladder_id = ladder_id
        self.bankroll_manager, self.bet_selector = create_strategy_engine(str(self.db_path), ladder_id)
    
    def run_daily_cycle(self, predictions: list[dict]) -> dict:
        """
        Execute the full daily cycle.
        
        1. Resolve yesterday's bets
        2. Update bankroll based on results
        3. Generate today's ticket
        
        Args:
            predictions: Today's match predictions
            
        Returns:
            Summary of the day's actions
        """
        today = datetime.now().strftime("%Y-%m-%d")
        summary = {
            "date": today,
            "phase": "INIT",
            "resolutions": [],
            "ticket": None,
            "state": {}
        }
        
        # Phase 1: Resolve pending bets
        print(f"[Phoenix] Phase 1: Resolving pending bets...")
        resolutions = self.resolution_service.auto_resolve_from_history()
        summary["resolutions"] = resolutions
        
        # Update bankroll for each resolution
        for res in resolutions:
            # IMPORTANT: Verify this resolution belongs to the current ladder
            if res.get("ladder_id") != self.ladder_id:
                continue
                
            if res.get("status") in ["WIN", "LOSS"]:
                is_win = res["status"] == "WIN"
                profit_loss = res["profit_loss"]
                update = self.bankroll_manager.update_after_result(is_win, profit_loss)
                
                # If it was a loss, record the bad beat
                if not is_win:
                    self._record_bad_beat(res)
        
        summary["phase"] = "RESOLVED"
        
        # Phase 2: Check if we already have a ticket for today
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM ladder_tickets WHERE date = ? AND ladder_id = ?", (today, self.ladder_id))
        existing = cursor.fetchone()
        conn.close()
        
        if existing:
            print(f"[Phoenix] Ticket already exists for today. Skipping generation.")
            summary["phase"] = "EXISTING_TICKET"
            summary["state"] = self.bankroll_manager.get_state()
            return summary
        
        # Phase 3: Generate today's ticket
        print(f"[Phoenix] Phase 2: Generating today's ticket...")
        
        if not predictions:
            print(f"[Phoenix] No predictions available. Skipping ticket generation.")
            summary["phase"] = "NO_PREDICTIONS"
            summary["state"] = self.bankroll_manager.get_state()
            return summary
        
        # Strategy selection - ALWAYS AUTO
        print(f"[Phoenix] Mode AUTO: Analyzing market for best strategy...")
        strategy = self.bet_selector.select_strategy_automatically(predictions)
        print(f"[Phoenix] AI Selected Strategy: {strategy.value}")
        
        # Update state to reflect the AI's choice for this cycle
        self.bankroll_manager.set_strategy(strategy)
        
        ticket = self.bet_selector.select_parlay(predictions, strategy)
        
        if ticket:
            ticket_id = self.bet_selector.save_ticket(ticket)
            summary["ticket"] = {
                "id": ticket_id,
                **ticket.to_dict()
            }
            print(f"[Phoenix] Ticket generated: {len(ticket.legs)} legs, ${ticket.stake_amount:.2f} stake")
            summary["phase"] = "TICKET_GENERATED"
        else:
            print(f"[Phoenix] Could not generate a valid ticket.")
            summary["phase"] = "NO_VALID_TICKET"
        
        summary["state"] = self.bankroll_manager.get_state()
        return summary
    
    def _record_bad_beat(self, resolution: dict):
        """Record a loss for AI learning."""
        try:
            for leg in resolution.get("legs", []):
                if leg.get("result") == "LOSS":
                    learning = self.groq.analyze_loss(
                        match_id=leg.get("match_id", ""),
                        predicted=leg.get("pick", ""),
                        actual=leg.get("actual", ""),
                        probability=60.0  # Could be fetched from DB
                    )
                    
                    conn = sqlite3.connect(str(self.db_path))
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO bad_beats_memory (date, match_id, predicted_winner, actual_winner, learning_note)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        datetime.now().strftime("%Y-%m-%d"),
                        leg.get("match_id"),
                        leg.get("pick"),
                        leg.get("actual"),
                        learning
                    ))
                    conn.commit()
                    conn.close()
        except Exception as e:
            print(f"[Phoenix] Error recording bad beat: {e}")
    
    def get_today_status(self) -> dict:
        """Get the current status for display."""
        state = self.bankroll_manager.get_state()
        if not state:
            return {"error": "Ladder not found"}
            
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Get today's ticket if exists
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM ladder_tickets WHERE date = ? AND ladder_id = ?", (today, self.ladder_id))
        ticket_row = cursor.fetchone()
        
        # Get recent history
        cursor.execute("""
            SELECT date, daily_change, ticket_result, step_number
            FROM bankroll_history 
            WHERE ladder_id = ?
            ORDER BY date DESC LIMIT 7
        """, (self.ladder_id,))
        history = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            "state": state,
            "today_ticket": dict(ticket_row) if ticket_row else None,
            "recent_history": history,
            "progress_pct": ((state.get("current_capital", 0) / state.get("goal_capital", 100000)) * 100)
        }

    def get_ticket_by_date(self, date_str: str) -> dict:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM ladder_tickets WHERE date = ? AND ladder_id = ?", (date_str, self.ladder_id))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"error": "Ticket not found"}
            
        ticket = dict(row)
        
        # Get legs
        cursor.execute("SELECT * FROM ticket_legs WHERE ticket_id = ?", (ticket['id'],))
        legs = [dict(leg) for leg in cursor.fetchall()]
        ticket['legs'] = legs
        
        # Deserialize JSONs if needed (ticket_json might duplicate legs, but let's be safe)
        try:
            if ticket.get('ticket_json'):
                ticket_details = json.loads(ticket['ticket_json'])
                if 'phoenix_note' in ticket_details:
                    ticket['phoenix_note'] = ticket_details['phoenix_note']
        except:
            pass
            
        conn.close()
        return ticket

    def get_all_ladders(self) -> list[dict]:
        """List all available ladders."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ladders ORDER BY last_update_date DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def create_ladder(self, name: str, capital: float, goal: float) -> dict:
        """Create a new ladder challenge."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO ladders (name, current_capital, starting_capital, goal_capital, step_number, strategy_mode, last_update_date)
            VALUES (?, ?, ?, ?, 1, 'FENIX', ?)
        """, (name, capital, capital, goal, datetime.now().strftime("%Y-%m-%d")))
        
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"id": new_id, "name": name, "status": "created"}

    def update_ladder_config(self, capital: Optional[float] = None, goal: Optional[float] = None) -> dict:
        """
        Update ladder config if possible.
        """
        conn = sqlite3.connect(str(self.db_path)) # Fixed: use self.db_path string casting if needed, matching other methods
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if capital is not None:
            updates.append("current_capital = ?")
            # If current capital matches starting capital (i.e. we haven't started), 
            # allow updating starting capital too? 
            # For now, simplistic approach: just update current.
            # But user wants "capital inicial" to change.
            # Let's check status. If step=1, update starting_capital too?
            # Let's just update current_capital as that's what matters for next bet.
            params.append(capital)
            
        if goal is not None:
            updates.append("goal_capital = ?")
            params.append(goal)
            
        if not updates:
            conn.close()
            return {"status": "no_changes"}
            
        params.append(self.ladder_id)
        
        query = f"UPDATE ladders SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, tuple(params))
        
        conn.commit()
        conn.close()
        return {"status": "updated", "updates": updates}
    
    def set_strategy(self, strategy_name: str) -> dict:
        """Change the active betting strategy."""
        try:
            # Handle AUTO mode special case
            if strategy_name.upper() == "AUTO":
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                cursor.execute("UPDATE ladder_state SET strategy_mode = ? WHERE id = 1", ("AUTO",))
                conn.commit()
                conn.close()
                return {"status": "ok", "strategy": "AUTO"}
            
            # Handle standard strategies
            strategy = Strategy(strategy_name.upper())
            self.bankroll_manager.set_strategy(strategy)
            return {"status": "ok", "strategy": strategy.value}
        except ValueError:
            return {"status": "error", "message": f"Invalid strategy: {strategy_name}"}
    
    def reset_ladder(self, starting_capital: float = 10000.0, goal: float = 100000.0) -> dict:
        """Reset the ladder challenge to start fresh."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE ladders SET
                current_capital = ?,
                starting_capital = ?,
                goal_capital = ?,
                step_number = 1,
                max_step_reached = 1,
                consecutive_wins = 0,
                consecutive_losses = 0,
                last_update_date = ?
            WHERE id = ?
        """, (starting_capital, starting_capital, goal, datetime.now().strftime("%Y-%m-%d"), self.ladder_id))
        
        conn.commit()
        conn.close()
        
        return {"status": "reset", "capital": starting_capital, "goal": goal}


# Factory function for easy import
def create_ladder_orchestrator(db_path: str = "ladder_v2.db", ladder_id: int = 1) -> LadderOrchestrator:
    """Create and return a configured LadderOrchestrator."""
    return LadderOrchestrator(db_path, ladder_id)


if __name__ == "__main__":
    # CLI Mode
    import sys
    
    print("=" * 50)
    print("PROJECT PHOENIX - AUTONOMOUS LADDER SYSTEM")
    print("=" * 50)
    
    orchestrator = create_ladder_orchestrator()
    status = orchestrator.get_today_status()
    
    print(f"\n📊 Current Capital: ${status['state'].get('current_capital', 0):,.2f}")
    print(f"🎯 Goal: ${status['state'].get('goal_capital', 0):,.2f}")
    print(f"📈 Progress: {status['progress_pct']:.1f}%")
    print(f"🪜 Current Step: #{status['state'].get('step_number', 1)}")
    print(f"🎲 Strategy: {status['state'].get('strategy_mode', 'FENIX')}")
    
    if status['today_ticket']:
        print(f"\n✅ Today's ticket exists (Status: {status['today_ticket'].get('status')})")
    else:
        print(f"\n⏳ No ticket generated yet for today")
    
    print("\nRecent History:")
    for h in status['recent_history'][:5]:
        emoji = "✅" if h.get('ticket_result') == 'WIN' else ("❌" if h.get('ticket_result') == 'LOSS' else "➖")
        print(f"  {emoji} {h.get('date')}: {h.get('daily_change', 0):+.2f}")
