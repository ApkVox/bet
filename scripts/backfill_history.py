import sys
import os
import requests
from datetime import datetime
import sqlite3
import logging

# Ensure local imports work outside package context
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from football_api import football_api
from history_db import DB_PATH, save_historical_prediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_URL = "https://fixturedownload.com/feed/json/epl-2025"

def run_backfill(start_date_str="2026-01-01"):
    """
    Downloads historical matches from start_date_str to today.
    Simulates predictions on those matches, compares with real scores, 
    and injects them into DB with status WIN or LOSS.
    """
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    today = datetime.now().date()
    
    logger.info(f"Fetching full season data from {API_URL}")
    r = requests.get(API_URL)
    all_matches = r.json()
    
    # Filter matches played between start_date and today that HAVE a result
    played_matches = []
    for m in all_matches:
        if m.get('HomeTeamScore') is None:
            continue
            
        raw_date = m.get('DateUtc', '')
        try:
            match_dt = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%SZ").date()
            if start_date <= match_dt <= today:
                played_matches.append((m, match_dt))
        except Exception as e:
            logger.warning(f"Could not parse date {raw_date}: {e}")
            
    logger.info(f"Found {len(played_matches)} completed matches between {start_date} and {today}")
    
    # Normalize team names and predict
    from src.DataProviders.FootballProvider import FootballProvider
    provider = FootballProvider()
    
    for m, match_dt in played_matches:
        home_raw = m['HomeTeam']
        away_raw = m['AwayTeam']
        home_score = m['HomeTeamScore']
        away_score = m['AwayTeamScore']
        
        home_team = provider.normalize_team_name(home_raw)
        away_team = provider.normalize_team_name(away_raw)
        
        # Who actually won?
        if home_score > away_score:
            actual_winner = home_team
        elif away_score > home_score:
            actual_winner = away_team
        else:
            actual_winner = "Draw"
            
        logger.info(f"Predicting match: {home_team} ( {home_score} ) vs ( {away_score} ) {away_team} on {match_dt}")
        
        pred = football_api.predict_match(home_team, away_team, "ENG-Premier League")
        predicted_winner = pred['prediction']
        
        is_win = (predicted_winner == actual_winner)
        result_str = "WIN" if is_win else "LOSS"
        
        logger.info(f"  -> Predicted: {predicted_winner} | Actual: {actual_winner} => {result_str}")
        
        # Reconstruct into history DB structure manually since save_football_prediction currently sets PENDING
        match_id = f"{match_dt.strftime('%Y-%m-%d')}_{home_team}_{away_team}"
        
        probs = pred.get('probs', {})
        
        # Insert straight to SQLite using exact fields from football_predictions table
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO football_predictions 
                (date, league, match_id, home_team, away_team, prediction, 
                 prob_home, prob_draw, prob_away, result)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_dt.strftime("%Y-%m-%d"),
                "ENG-Premier League",
                match_id,
                home_team,
                away_team,
                predicted_winner,
                probs.get('home', 0),
                probs.get('draw', 0),
                probs.get('away', 0),
                result_str
            ))
            conn.commit()

    logger.info(f"Backfill complete! Injected {len(played_matches)} history records into DB.")

if __name__ == "__main__":
    run_backfill("2026-01-01")
