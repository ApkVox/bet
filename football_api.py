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

    def predict_match(self, home_team: str, away_team: str, league: str, news_data: Optional[Dict] = None) -> Dict:
        """
        Predict the outcome of a football match using Poisson distribution.
        Integrates optional news_data to adjust confidence.
        """
        self.ensure_initialized()
        
        result = {
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "prediction": "Draw",
            "probs": {"home": 33.3, "draw": 33.4, "away": 33.3},
            "expected_goals": {"home": 0.0, "away": 0.0},
            "top_scorelines": [],
            "status": "PENDING",
            "confidence_modifier": "neutral"
        }
        
        # Use Poisson predictor if available
        if self.predictor:
            try:
                insights = self.predictor.get_betting_insights(home_team, away_team)
                if insights:
                    outcome_probs = insights.get('outcome_probs', {})
                    home_prob = outcome_probs.get('home_win', 0) * 100
                    draw_prob = outcome_probs.get('draw', 0) * 100
                    away_prob = outcome_probs.get('away_win', 0) * 100
                    
                    # Ajustar según noticias (Confidence Modifier)
                    if news_data:
                        mod = news_data.get("confidence_modifier", "neutral")
                        result["confidence_modifier"] = mod
                        if mod == "higher":
                            # Reforzar el favorito
                            if home_prob > away_prob: home_prob += 5
                            else: away_prob += 5
                        elif mod == "lower":
                            # Debilitar al favorito
                            if home_prob > away_prob: home_prob -= 8
                            else: away_prob -= 8

                    # Normalizar tras ajuste
                    total = home_prob + draw_prob + away_prob
                    home_prob = (home_prob / total) * 100
                    draw_prob = (draw_prob / total) * 100
                    away_prob = (away_prob / total) * 100

                    # Determine prediction (1, X, 2)
                    max_prob = max(home_prob, draw_prob, away_prob)
                    if max_prob == home_prob: prediction = '1'
                    elif max_prob == draw_prob: prediction = 'X'
                    else: prediction = '2'
                    
                    result.update({
                        "prediction": prediction,
                        "probs": {
                            "home": round(home_prob, 1),
                            "draw": round(draw_prob, 1),
                            "away": round(away_prob, 1)
                        },
                        "expected_goals": insights.get('expected_goals', {}),
                        "top_scorelines": insights.get('top_scorelines', [])[:3]
                    })
            except Exception as e:
                logger.warning(f"Poisson prediction failed for {home_team} vs {away_team}: {e}")
        
        return result
        
        return result

    async def get_all_predictions(self, league: str = "Premier League") -> List[Dict]:
        """
        Fetch fixtures and generate predictions for all matches.
        """
        # get_fixtures does NOT need initialization (it hits OneFootball API)
        fixtures = self.get_fixtures()
        
        # Ensure initialized before predicting loop
        self.ensure_initialized()
        
        # Filter by league if specified
        if league:
            fixtures = [f for f in fixtures if league.lower() in f['league'].lower()]
        
        predictions = []
        
        # Assign match_id early so news agent can save to db without null constraint
        for fixture in fixtures:
            fixture['match_id'] = f"{fixture.get('date', datetime.now().date())}_{fixture['home_team']}_{fixture['away_team']}".replace(" ", "_")

        # Primero obtenemos noticias para todos los fixtures (opcional pero recomendado para EPL)
        # Esto nos permite ajustar las probabilidades de Poisson con IA
        from football_news_agent import fetch_football_news
        news_map = {}
        try:
            future_news = await fetch_football_news(datetime.now().strftime("%Y-%m-%d"), fixtures)
            news_map = {n['match_id']: n for n in future_news}
        except Exception as e:
            logger.warning(f"Could not fetch football news: {e}")

        for fixture in fixtures:
            match_id = fixture['match_id']
            
            # Pasar noticias al predictor
            news_data = news_map.get(match_id)
            pred = self.predict_match(fixture['home_team'], fixture['away_team'], fixture['league'], news_data=news_data)
            
            # Enrich with time and raw names
            pred['time'] = fixture.get('time', 'Coming Soon')
            pred['raw_home'] = fixture.get('home_raw', fixture['home_team'])
            pred['raw_away'] = fixture.get('away_raw', fixture['away_team'])
             
            # Save to history DB (Best effort)
            fixture_date = fixture.get('date', str(datetime.now().date()))
            pred['date'] = fixture_date
            pred['match_id'] = match_id
            
            try:
                import history_db
                history_db.save_football_prediction(pred, match_id, fixture_date)
            except Exception as e:
                logger.debug(f"Could not save prediction history: {e}")

            predictions.append(pred)
            
        return predictions


# Global instance
football_api = FootballAPI()
