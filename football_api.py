"""
===========================================
FOOTBALL PREDICTION API - LA FIJA
===========================================
Uses Poisson distribution for 1X2 predictions.
Integrated from all_leagues_prediction repo.
"""

import pandas as pd
import numpy as np
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Deferred import for Poisson predictor
# try:
#     from footy.poisson_predictor import PoissonScorelinePredictor
#     POISSON_AVAILABLE = True
# except ImportError as e:
#     POISSON_AVAILABLE = False
#     logger.warning(f"Poisson predictor not available: {e}")

# Import FootballProvider
from src.DataProviders.FootballProvider import FootballProvider

# Constants
DATA_PATH = "Data/football/complete_features.csv"
LEAGUES = ['ENG-Premier League', 'ESP-La Liga', 'ITA-Serie A', 'GER-Bundesliga', 'FRA-Ligue 1']

# Cache for fixtures to avoid spamming OneFootball
_FIXTURES_CACHE = {
    "data": [],
    "last_updated": None
}

def get_upcoming_fixtures() -> list:
    """
    Fetches real upcoming fixtures from FootballProvider.
    Uses simple in-memory caching (1 hour TTL).
    """
    global _FIXTURES_CACHE
    
    now = datetime.now()
    if _FIXTURES_CACHE["data"] and _FIXTURES_CACHE["last_updated"]:
        time_diff = (now - _FIXTURES_CACHE["last_updated"]).total_seconds()
        if time_diff < 3600: # 1 hour cache
            logger.info(f"Using cached football fixtures ({len(_FIXTURES_CACHE['data'])} games)")
            return _FIXTURES_CACHE["data"]
            
    logger.info("Fetching fresh football fixtures...")
    provider = FootballProvider()
    fixtures = provider.get_fixtures()
    
    if fixtures:
        _FIXTURES_CACHE["data"] = fixtures
        _FIXTURES_CACHE["last_updated"] = now
        
    return fixtures


class FootballAPI:
    def __init__(self):
        self.predictor = None
        self.data = None
        self._is_initialized = False
        # Do not initialize immediately to save startup memory
        # self._initialize()
        
    def ensure_initialized(self):
        """Lazy load data and predictor only when needed."""
        if self._is_initialized:
            return

        logger.info("Lazy loading FootballAPI resources...")
        
        # Load historical data
        if os.path.exists(DATA_PATH):
            try:
                self.data = pd.read_csv(DATA_PATH)
                logger.info(f"Loaded football data: {len(self.data)} records")
                
                # Initialize Poisson predictor if available
                try:
                    from footy.poisson_predictor import PoissonScorelinePredictor
                    self.predictor = PoissonScorelinePredictor()
                    self.predictor.calculate_team_strengths(self.data)
                    logger.info("Poisson predictor initialized successfully")
                except ImportError as e:
                    logger.warning(f"Poisson predictor not available (lazy load failed): {e}")
            except Exception as e:
                logger.error(f"Error loading football data: {e}")
        else:
            logger.warning(f"Football data not found at {DATA_PATH}")
            
        self._is_initialized = True

    def get_fixtures(self, date_str: str = None) -> List[Dict]:
        """
        Get football fixtures.
        Uses the FootballProvider via get_upcoming_fixtures.
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        # For now, we disregard date_str and just get whatever is upcoming/live
        # In a full valid implementation, we would filter by date.
        return get_upcoming_fixtures()

    def predict_match(self, home_team: str, away_team: str, league: str) -> Dict:
        """
        Predict the outcome of a football match using Poisson distribution.
        Returns probabilities for Home Win, Draw, Away Win.
        """
        self.ensure_initialized()  # Ensure models are loaded
        
        result = {
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "prediction": "Draw",
            "probs": {"home": 33.3, "draw": 33.4, "away": 33.3},
            "expected_goals": {"home": 0.0, "away": 0.0},
            "top_scorelines": [],
            "status": "PENDING"
        }
        
        # Use Poisson predictor if available
        if self.predictor:
            try:
                # Get betting insights (includes probabilities)
                insights = self.predictor.get_betting_insights(home_team, away_team)
                
                if insights:
                    # Extract outcome probabilities
                    outcome_probs = insights.get('outcome_probs', {})
                    home_prob = outcome_probs.get('home_win', 0) * 100
                    draw_prob = outcome_probs.get('draw', 0) * 100
                    away_prob = outcome_probs.get('away_win', 0) * 100
                    
                    # Determine prediction
                    max_prob = max(home_prob, draw_prob, away_prob)
                    prediction = "Draw"
                    if max_prob == home_prob:
                        prediction = home_team
                    elif max_prob == draw_prob:
                        prediction = "Draw"
                    else:
                        prediction = away_team
                    
                    result.update({
                        "prediction": prediction,
                        "probs": {
                            "home": round(home_prob, 1),
                            "draw": round(draw_prob, 1),
                            "away": round(away_prob, 1)
                        },
                        "expected_goals": insights.get('expected_goals', {}),
                        "top_scorelines": insights.get('top_scorelines', [])[:3],
                        "over_under": insights.get('goal_market_probs', {})
                    })
                    
                    logger.info(f"Predicted {home_team} vs {away_team}: {prediction} ({max_prob:.1f}%)")
                    
            except Exception as e:
                logger.warning(f"Poisson prediction failed for {home_team} vs {away_team}: {e}")
                # Falls back to default values already in result
        
        return result

    def get_all_predictions(self, league: Optional[str] = None) -> List[Dict]:
        """Get predictions for all upcoming fixtures."""
        # get_fixtures does NOT need initialization (it hits OneFootball API)
        fixtures = self.get_fixtures()
        
        # Ensure initialized before predicting loop
        self.ensure_initialized()
        
        # Filter by league if specified
        if league:
            fixtures = [f for f in fixtures if league.lower() in f['league'].lower()]
        
        predictions = []
        for fixture in fixtures:
            # We predict using the NORMALIZED names (home_team, away_team)
            # But we might want to preserve raw names for display if needed
            pred = self.predict_match(fixture['home_team'], fixture['away_team'], fixture['league'])
            
            # Enrich with time and raw names
            pred['time'] = fixture.get('time', 'Coming Soon')
            pred['raw_home'] = fixture.get('home_raw', fixture['home_team'])
            pred['raw_away'] = fixture.get('away_raw', fixture['away_team'])
             
            # Save to history DB (Best effort)
            fixture_date = fixture.get('date', str(datetime.now().date()))
            pred['date'] = fixture_date
            try:
                import history_db
                # We need a unique match_id. hash date+teams
                match_id = f"{fixture_date}_{fixture['home_team']}_{fixture['away_team']}"
                pred['match_id'] = match_id
                
                # We need to adapt the save function or create a new one for football
                # For now, let's assume we will implement save_football_prediction in history_db
                history_db.save_football_prediction(pred, match_id, fixture_date)
            except Exception as e:
                logger.debug(f"Could not save prediction history: {e}")

            predictions.append(pred)
            
        return predictions


# Global instance
football_api = FootballAPI()
