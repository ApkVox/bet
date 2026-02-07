"""
Backfill missing history for Feb 4-6, 2026
Generates predictions and updates results in history.db
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
from pathlib import Path
from datetime import date, datetime
import json

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "Data" / "history.db"
RESULTS_CACHE = BASE_DIR / "nba_results_cache.json"

# Load results cache
def load_results_cache():
    if RESULTS_CACHE.exists():
        with open(RESULTS_CACHE, 'r') as f:
            return json.load(f)
    return {}

# Games to backfill - hardcoded from known NBA schedule
GAMES_BY_DATE = {
    "2026-02-04": [
        {"home": "Miami Heat", "away": "Brooklyn Nets"},
        {"home": "Atlanta Hawks", "away": "Chicago Bulls"},
        {"home": "Houston Rockets", "away": "Memphis Grizzlies"},
        {"home": "Milwaukee Bucks", "away": "Detroit Pistons"},
        {"home": "New Orleans Pelicans", "away": "Sacramento Kings"},
        {"home": "Oklahoma City Thunder", "away": "Dallas Mavericks"},
        {"home": "Phoenix Suns", "away": "Cleveland Cavaliers"},
        {"home": "LA Clippers", "away": "Portland Trail Blazers"},
    ],
    "2026-02-05": [
        {"home": "Toronto Raptors", "away": "New York Knicks"},
        {"home": "Boston Celtics", "away": "Philadelphia 76ers"},
        {"home": "Orlando Magic", "away": "Washington Wizards"},
        {"home": "Indiana Pacers", "away": "Charlotte Hornets"},
        {"home": "Denver Nuggets", "away": "Minnesota Timberwolves"},
        {"home": "San Antonio Spurs", "away": "Los Angeles Lakers"},
        {"home": "Golden State Warriors", "away": "Utah Jazz"},
    ],
    "2026-02-06": [
        {"home": "New York Knicks", "away": "Miami Heat"},
        {"home": "Atlanta Hawks", "away": "Boston Celtics"},
        {"home": "Cleveland Cavaliers", "away": "Chicago Bulls"},
        {"home": "Memphis Grizzlies", "away": "Detroit Pistons"},
        {"home": "Oklahoma City Thunder", "away": "Houston Rockets"},
        {"home": "Dallas Mavericks", "away": "New Orleans Pelicans"},
        {"home": "Phoenix Suns", "away": "LA Clippers"},
        {"home": "Portland Trail Blazers", "away": "Sacramento Kings"},
    ]
}

def backfill_date(date_str: str, games: list):
    """Generate predictions and save to history for a date"""
    from prediction_api import predict_game, load_models
    from history_db import save_historical_prediction
    
    print(f"\n{'='*50}")
    print(f"Processing {date_str}")
    print(f"{'='*50}")
    
    # Load models once
    load_models()
    
    game_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    saved = 0
    for game in games:
        home = game["home"]
        away = game["away"]
        
        try:
            # Get prediction
            pred = predict_game(home, away, game_date=game_date)
            if not pred:
                print(f"  [SKIP] {home} vs {away}: No prediction")
                continue
            
            match_id = f"{home} vs {away}"
            
            # For historical data, we don't have real results - mark as PENDING
            # The update-history endpoint will fetch and update real results
            pred_data = {
                'date': date_str,
                'match_id': match_id,
                'home_team': home,
                'away_team': away,
                'winner': pred['winner'],
                'win_probability': pred['win_probability'],
                'market_odds': pred.get('market_odds_home', -110) if pred['winner'] == home else pred.get('market_odds_away', -110),
                'ev_value': pred.get('ev_value', 0),
                'kelly_stake_pct': pred.get('kelly_stake_pct', 0),
                'warning_level': pred.get('warning_level', 'NORMAL'),
                'result': 'PENDING',
                'profit': 0.0
            }
            
            save_historical_prediction(pred_data)
            saved += 1
            print(f"  ✅ {match_id}: {pred['winner']} ({pred['win_probability']}%)")
            
        except Exception as e:
            print(f"  [ERROR] {home} vs {away}: {e}")
    
    print(f"[OK] Saved {saved}/{len(games)} predictions for {date_str}")

def main():
    print("="*60)
    print("NBA PREDICTOR - HISTORY BACKFILL")
    print("="*60)
    
    for date_str, games in GAMES_BY_DATE.items():
        backfill_date(date_str, games)
    
    # Verify
    print("\n" + "="*60)
    print("VERIFICATION")
    print("="*60)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT date, COUNT(*) as games
            FROM predictions
            WHERE date IN ('2026-02-04', '2026-02-05', '2026-02-06')
            GROUP BY date
            ORDER BY date
        """)
        
        for row in cursor.fetchall():
            date, games = row
            print(f"{date}: {games} games")
    
    print("\n[DONE] Backfill complete!")
    print("Run the server and visit /update-history to fetch real results.")

if __name__ == "__main__":
    main()
