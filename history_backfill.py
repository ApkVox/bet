"""
===========================================
HISTORY BACKFILL SYSTEM
===========================================
Autonomous module that detects missing NBA game days in the prediction
history database and fills the gaps with retroactive predictions + results.

Uses point-in-time safe XGBoost predictions to avoid data leakage.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

BASE_DIR = Path(__file__).resolve().parent

# Ensure imports work
sys.path.insert(0, str(BASE_DIR))

import history_db
from prediction_api import predict_game, load_models


def _load_results_cache() -> dict:
    """Load the nba_results_cache.json file."""
    cache_path = BASE_DIR / "nba_results_cache.json"
    if not cache_path.exists():
        print("[BACKFILL] nba_results_cache.json not found")
        return {}
    with open(cache_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fetch_sbr_results(date_str: str) -> list:
    """
    Fetch game results from SBR for a specific date.
    Returns list of dicts with home, away, winner_real, scores.
    """
    try:
        from sbrscrape import Scoreboard
        sb = Scoreboard(sport="NBA", date=date_str)
        games = sb.games if hasattr(sb, 'games') else []
        
        results = []
        for game in games:
            status = game.get('status', '')
            if 'final' not in status.lower():
                continue
            
            home = game.get('home_team', '')
            away = game.get('away_team', '')
            home_score = game.get('home_score')
            away_score = game.get('away_score')
            
            if home and away and home_score is not None and away_score is not None:
                # Normalize team names
                home = home.replace("Los Angeles Clippers", "LA Clippers")
                away = away.replace("Los Angeles Clippers", "LA Clippers")
                
                winner = home if int(home_score) > int(away_score) else away
                results.append({
                    "home": home,
                    "away": away,
                    "home_score": int(home_score),
                    "away_score": int(away_score),
                    "winner_real": winner,
                    "fecha": date_str
                })
        return results
    except Exception as e:
        print(f"[BACKFILL] Error fetching SBR results for {date_str}: {e}")
        return []


def _get_all_game_dates() -> dict:
    """
    Build a complete map of all dates with games and their results.
    Sources: nba_results_cache.json + SBR for recent dates.
    
    Returns: {date_str: [game_dict, ...]}
    """
    all_games = {}
    
    # 1. Load from cache file
    cache = _load_results_cache()
    for date_key, games in cache.items():
        # Convert YYYYMMDD to YYYY-MM-DD
        date_str = f"{date_key[:4]}-{date_key[4:6]}-{date_key[6:8]}"
        all_games[date_str] = games
    
    # 2. Fill gap between cache end date and today using SBR
    if cache:
        last_cache_key = max(cache.keys())
        last_cache_date = datetime.strptime(last_cache_key, "%Y%m%d").date()
        today = date.today()
        yesterday = today - timedelta(days=1)
        
        # Fetch missing dates from SBR (day after last cache to yesterday)
        current = last_cache_date + timedelta(days=1)
        while current <= yesterday:
            date_str = current.strftime("%Y-%m-%d")
            if date_str not in all_games:
                print(f"[BACKFILL] Fetching SBR results for {date_str}...")
                sbr_results = _fetch_sbr_results(date_str)
                if sbr_results:
                    all_games[date_str] = sbr_results
                    print(f"[BACKFILL]   → Found {len(sbr_results)} finished games")
            current += timedelta(days=1)
    
    return all_games


def _update_results_cache(all_games: dict):
    """
    Update nba_results_cache.json with any newly fetched SBR results.
    This way next time the backfill runs, it doesn't need to re-fetch.
    """
    cache_path = BASE_DIR / "nba_results_cache.json"
    
    # Load existing cache
    existing = {}
    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
    
    updated = False
    for date_str, games in all_games.items():
        date_key = date_str.replace("-", "")
        if date_key not in existing and games:
            existing[date_key] = games
            updated = True
    
    if updated:
        # Sort by date key
        sorted_cache = dict(sorted(existing.items()))
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(sorted_cache, f, indent=2, ensure_ascii=False)
        print("[BACKFILL] Updated nba_results_cache.json with new results")


def run_backfill() -> dict:
    """
    Main backfill function. Autonomous and idempotent.
    
    1. Discovers all dates with NBA games (cache + SBR)
    2. Checks which dates/games are missing from history.db
    3. Generates retroactive predictions for missing games
    4. Saves predictions with resolved WIN/LOSS results
    
    Returns: Summary dict with stats
    """
    print("=" * 60)
    print("[BACKFILL] Starting autonomous history backfill...")
    print("=" * 60)
    
    # Ensure DB and models are ready
    history_db.init_history_db()
    load_models()
    
    # 1. Get all game dates with results
    all_games = _get_all_game_dates()
    print(f"[BACKFILL] Found {len(all_games)} dates with games")
    
    # Update the cache file with any new SBR results
    _update_results_cache(all_games)
    
    # 2. Get existing predictions from DB
    existing_predictions = history_db.get_all_prediction_dates()
    print(f"[BACKFILL] Existing predictions in DB for {len(existing_predictions)} dates")
    
    # 3. Find gaps
    total_added = 0
    total_skipped = 0
    total_errors = 0
    dates_processed = 0
    
    for date_str in sorted(all_games.keys()):
        games = all_games[date_str]
        if not games:
            continue
        
        # Get existing match_ids for this date
        existing_match_ids = history_db.get_match_ids_for_date(date_str)
        existing_count = len(existing_match_ids)
        
        # Check which games are missing
        missing_games = []
        for game in games:
            home = game.get("home", game.get("home_team", ""))
            away = game.get("away", game.get("away_team", ""))
            match_id = f"{home} vs {away}"
            
            if match_id not in existing_match_ids:
                missing_games.append(game)
        
        if not missing_games:
            total_skipped += len(games)
            continue
        
        print(f"[BACKFILL] {date_str}: {len(missing_games)}/{len(games)} games missing")
        dates_processed += 1
        
        # Parse date for prediction_api
        try:
            game_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"[BACKFILL]   ✗ Invalid date format: {date_str}")
            total_errors += len(missing_games)
            continue
        
        for game in missing_games:
            home = game.get("home", game.get("home_team", ""))
            away = game.get("away", game.get("away_team", ""))
            winner_real = game.get("winner_real", "")
            match_id = f"{home} vs {away}"
            
            try:
                # Generate prediction using point-in-time data
                pred = predict_game(
                    home_team=home,
                    away_team=away,
                    ou_line=220.0,
                    game_date=game_date
                )
                
                predicted_winner = pred.get("winner", home)
                win_prob = pred.get("win_probability", 50.0)
                is_mock = pred.get("is_mock", True)
                
                # Determine result
                if winner_real:
                    result = "WIN" if predicted_winner == winner_real else "LOSS"
                else:
                    result = "PENDING"
                
                # Calculate basic profit (simplified)
                if result == "WIN":
                    profit = 1.0  # Simplified: flat unit win
                elif result == "LOSS":
                    profit = -1.0
                else:
                    profit = 0.0
                
                # Save to DB
                history_db.save_historical_prediction({
                    'date': date_str,
                    'match_id': match_id,
                    'home_team': home,
                    'away_team': away,
                    'winner': predicted_winner,
                    'win_probability': win_prob,
                    'market_odds': 0,
                    'ev_value': 0.0,
                    'kelly_stake_pct': 0.0,
                    'warning_level': 'BACKFILL',
                    'result': result,
                    'profit': profit
                })
                
                status = "✓" if not is_mock else "⚠ mock"
                print(f"[BACKFILL]   {status} {match_id}: pred={predicted_winner} ({win_prob}%) | actual={winner_real} → {result}")
                total_added += 1
                
            except Exception as e:
                print(f"[BACKFILL]   ✗ Error for {match_id}: {e}")
                total_errors += 1
    
    summary = {
        "status": "completed",
        "dates_with_games": len(all_games),
        "dates_processed": dates_processed,
        "predictions_added": total_added,
        "predictions_skipped": total_skipped,
        "errors": total_errors,
        "timestamp": datetime.now().isoformat()
    }
    
    print("=" * 60)
    print(f"[BACKFILL] Complete!")
    print(f"  Dates processed: {dates_processed}")
    print(f"  Predictions added: {total_added}")
    print(f"  Already existed (skipped): {total_skipped}")
    print(f"  Errors: {total_errors}")
    print("=" * 60)
    
    return summary


if __name__ == "__main__":
    result = run_backfill()
    print(f"\nResult: {json.dumps(result, indent=2)}")
