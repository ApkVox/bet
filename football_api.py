import pandas as pd
import numpy as np
import os
import json
import logging
from datetime import datetime, date
from typing import List, Dict, Optional
import xgboost as xgb

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import soccerdata, handle failure gracefully
try:
    import soccerdata as sd
    SOCCERDATA_AVAILABLE = True
except ImportError:
    SOCCERDATA_AVAILABLE = False
    logger.warning("soccerdata library not found. Football data features will be limited.")

# Constants
MODEL_PATH = "Models/XGBoost_Models/football_model_v1.json"
LEAGUES = ['ENG-Premier League', 'ESP-La Liga', 'ITA-Serie A', 'GER-Bundesliga', 'FRA-Ligue 1']

class FootballAPI:
    def __init__(self):
        self.model = self._load_model()
        
    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            model = xgb.Booster()
            model.load_model(MODEL_PATH)
            return model
        return None

    def get_fixtures(self, date_str: str = None) -> List[Dict]:
        """
        Get football fixtures for a specific date.
        If soccerdata is available, use it (or an odds API).
        For this MVP, we might need to fallback to a basic scraping method or mock data
        if we don't have a live odds API key.
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
            
        logger.info(f"Fetching football fixtures for {date_str}")
        
        # TODO: Implement actual fetching from an API (e.g. The Odds API or local scraper)
        # For now, return an empty list or mock data for testing UI
        return []

    def predict_match(self, home_team: str, away_team: str, league: str) -> Dict:
        """
        Predict the outcome of a football match (Home Win, Draw, Away Win).
        """
        # 1. Get features (mock for now)
        features = self._get_team_features(home_team, away_team, league)
        
        # 2. Predict
        if self.model:
            # DMatrix needs actual data
            # preds = self.model.predict(dtest)
            # return formatted preds
            pass
            
        # Mock prediction for UI testing
        return {
            "home_team": home_team,
            "away_team": away_team,
            "league": league,
            "prediction": "Draw", # 1, X, 2
            "probs": {
                "home": 33.3,
                "draw": 33.4,
                "away": 33.3
            },
            "status": "PENDING"
        }

    def _get_team_features(self, home: str, away: str, league: str):
        """
        Fetch stats from soccerdata for feature engineering.
        """
        if not SOCCERDATA_AVAILABLE:
            return None
            
        # Example using soccerdata to get recent form
        # fb = sd.FBref(leagues=league, seasons='2324')
        # stats = fb.read_team_match_stats()
        return None

football_api = FootballAPI()
