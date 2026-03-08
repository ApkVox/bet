import sys
from pathlib import Path
from datetime import datetime, date

# Add parent directory to path to allow importing modules from root
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from sbrscrape import Scoreboard
import history_db
import difflib

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
    
    # Supabase version
    client = history_db._get_supabase()
    if client:
        try:
            today_str = datetime.now().strftime('%Y-%m-%d')
            res = client.table('predictions').select('date').eq('result', 'PENDING').lte('date', today_str).execute()
            pending_dates = list(set([row['date'] for row in res.data]))
        except Exception as e:
            print(f"[History Service DB Error] {e}")
        
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
            
            # 2.5 Get pending match_ids for this specific date from Supabase
            # to use for fuzzy matching
            db_matches = []
            try:
                res = history_db._get_supabase().table('predictions').select('match_id').eq('date', date_str).eq('result', 'PENDING').execute()
                db_matches = [r['match_id'] for r in res.data]
            except:
                pass
                
            # Create a map of actual results
            # Key: mismo formato que la DB (date_away_home con espacios -> _)
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
                    
                    # Try the explicit format used by recent updates (with ' vs ')
                    match_id_new = f"{date_str} {away} vs {home}"
                    # Try the legacy underscored format just in case
                    match_id_legacy = f"{date_str}_{away}_{home}".replace(" ", "_")
                    
                    # Exact matches
                    results_map[match_id_new] = winner
                    results_map[match_id_legacy] = winner
                    
                    # Fuzzy Match against real pending DB matches
                    for db_m in db_matches:
                        # If both teams are somehow mentioned in the DB match_id string, it's a match
                        # We use difflib or simple containment
                        away_parts = away.split()[-1] # Usually the mascot e.g., 'Thunder'
                        home_parts = home.split()[-1]
                        if away_parts.lower() in db_m.lower() and home_parts.lower() in db_m.lower():
                            results_map[db_m] = winner
                            
            # 3. Update DB
            history_db.update_results(date_str, results_map)
            updated_count += len(results_map)
            
        except Exception as e:
            print(f"[History Service] Error processing {date_str}: {e}")
            
    print(f"[History Service] Update complete. Updated {updated_count} matches.")
    return {"status": "success", "updated_count": updated_count}
