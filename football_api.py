"""
===========================================
FOOTBALL PREDICTION API - COURTSIDE AI
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

# Try to import Poisson predictor
try:
    from footy.poisson_predictor import PoissonScorelinePredictor
    POISSON_AVAILABLE = True
except ImportError as e:
    POISSON_AVAILABLE = False
    logger.warning(f"Poisson predictor not available: {e}")

# Constants
DATA_PATH = "Data/football/complete_features.csv"
LEAGUES = ['ENG-Premier League', 'ESP-La Liga', 'ITA-Serie A', 'GER-Bundesliga', 'FRA-Ligue 1']

# Sample upcoming fixtures (for MVP - replace with API later)
UPCOMING_FIXTURES = [
    {"home": "Arsenal", "away": "Man City", "league": "ENG-Premier League"},
    {"home": "Liverpool", "away": "Chelsea", "league": "ENG-Premier League"},
    {"home": "Real Madrid", "away": "Barcelona", "league": "ESP-La Liga"},
    {"home": "Juventus", "away": "AC Milan", "league": "ITA-Serie A"},
    {"home": "Bayern Munich", "away": "Dortmund", "league": "GER-Bundesliga"},
    {"home": "PSG", "away": "Lyon", "league": "FRA-Ligue 1"},
]


class FootballAPI:
    def __init__(self):
        self.predictor = None
        self.data = None
        self._initialize()
        
    def _initialize(self):
        """Load data and initialize Poisson predictor."""
        # Load historical data
        if os.path.exists(DATA_PATH):
            try:
                self.data = pd.read_csv(DATA_PATH)
                logger.info(f"Loaded football data: {len(self.data)} records")
                
                # Initialize Poisson predictor if available
                if POISSON_AVAILABLE:
                    self.predictor = PoissonScorelinePredictor()
                    self.predictor.calculate_team_strengths(self.data)
                    logger.info("Poisson predictor initialized successfully")
            except Exception as e:
                logger.error(f"Error loading football data: {e}")
        else:
            logger.warning(f"Football data not found at {DATA_PATH}")

    def get_fixtures(self, date_str: str = None) -> List[Dict]:
        """
        Get football fixtures for a specific date.
        MVP: Returns static fixtures. Replace with API call later.
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        logger.info(f"Getting football fixtures for {date_str}")
        
        # Return sample fixtures for MVP
        return UPCOMING_FIXTURES

    def predict_match(self, home_team: str, away_team: str, league: str) -> Dict:
        """
        Predict the outcome of a football match using Poisson distribution.
        Returns probabilities for Home Win, Draw, Away Win.
        """
        result = {
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "prediction": "Draw",
            "probs": {"home": 33.3, "draw": 33.4, "away": 33.3},
            "expected_goals": {"home": 1.5, "away": 1.5},
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
                    home_prob = outcome_probs.get('home_win', 33.3)
                    draw_prob = outcome_probs.get('draw', 33.4)
                    away_prob = outcome_probs.get('away_win', 33.3)
                    
                    # Determine prediction
                    max_prob = max(home_prob, draw_prob, away_prob)
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
        fixtures = self.get_fixtures()
        
        # Filter by league if specified
        if league:
            fixtures = [f for f in fixtures if league.lower() in f['league'].lower()]
        
        predictions = []
        for fixture in fixtures:
            pred = self.predict_match(fixture['home'], fixture['away'], fixture['league'])
            predictions.append(pred)
            
        return predictions


# Global instance
football_api = FootballAPI()
