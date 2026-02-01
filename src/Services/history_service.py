import sys
from pathlib import Path
from datetime import datetime, date

# Add parent directory to path to allow importing modules from root
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from sbrscrape import Scoreboard
import history_db
import sqlite3

def american_to_decimal(american_odds):
    if not american_odds: return 0.0
    if american_odds >= 100:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1

def update_pending_predictions():
    """
    Checks for pending predictions in the database and updates them 
    if the game has finished.
    """
    print("[History Service] Checking for pending predictions...")
    
    # 1. Get dates with pending predictions
    pending_dates = []
    with sqlite3.connect(history_db.DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT DISTINCT date FROM predictions 
            WHERE result = 'PENDING' 
            AND date <= date('now')
        """)
        pending_dates = [row[0] for row in cursor.fetchall()]
        
    print(f"[History Service] Found pending predictions for dates: {pending_dates}")
    
    updated_count = 0
    
    for date_str in pending_dates:
        print(f"[History Service] Updating results for {date_str}...")
        try:
            # 2. Fetch scores for that date
            sb = Scoreboard(sport="NBA", date=date_str)
            games = sb.games if hasattr(sb, 'games') else []
            
            if not games:
                print(f"[History Service] No games found for {date_str} in SBR.")
                continue
                
            # Create a map of actual results
            # Key: "HomeTeam vs AwayTeam", Value: WinnerName
            results_map = {}
            for game in games:
                if 'status' not in game or 'final' not in game['status'].lower():
                    continue
                    
                home = game.get('home_team')
                away = game.get('away_team')
                home_score = game.get('home_score')
                away_score = game.get('away_score')
                
                if home and away and home_score is not None and away_score is not None:
                    # Normalize names if needed (SBR <-> DB)
                    home = home.replace("Los Angeles Clippers", "LA Clippers")
                    away = away.replace("Los Angeles Clippers", "LA Clippers")
                    
                    winner = home if home_score > away_score else away
                    match_id = f"{home} vs {away}"
                    results_map[match_id] = winner
            
            # 3. Update DB
            history_db.update_results(date_str, results_map)
            updated_count += len(results_map)
            
        except Exception as e:
            print(f"[History Service] Error processing {date_str}: {e}")
            
    print(f"[History Service] Update complete. Updated {updated_count} matches.")
    return {"status": "success", "updated_count": updated_count}
