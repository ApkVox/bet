"""
===========================================
NBA Prediction API Module
===========================================
Clean prediction module that properly uses XGBoost models.
This replaces the broken random-based predictions in main.py.
"""
import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xgboost as xgb
import joblib

from src.Utils.Dictionaries import team_index_current


# ===========================================
# PATHS AND CONSTANTS
# ===========================================
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "Models" / "XGBoost_Models"
TEAM_DB_PATH = BASE_DIR / "Data" / "TeamData.sqlite"
ACCURACY_PATTERN = re.compile(r"XGBoost_(\d+(?:\.\d+)?)%_")

# Drop columns when building features (same as training)
DROP_COLUMNS = [
    "index", "Score", "Home-Team-Win", "TEAM_NAME", "Date",
    "index.1", "TEAM_NAME.1", "Date.1", "OU-Cover", "OU",
    "TEAM_ID", "TEAM_ID.1"
]


# ===========================================
# MODEL CACHE
# ===========================================
_models_cache = {
    "ml_model": None,
    "ml_calibrator": None,
    "uo_model": None,
    "uo_calibrator": None,
    "ml_accuracy": "N/A",
    "uo_accuracy": "N/A"
}


def _select_model_path(kind: str) -> Path:
    """Select the best model (highest accuracy) for ML or UO."""
    candidates = list(MODEL_DIR.glob(f"*{kind}*.json"))
    if not candidates:
        raise FileNotFoundError(f"No XGBoost {kind} model found in {MODEL_DIR}")
    
    def score(path):
        match = ACCURACY_PATTERN.search(path.name)
        accuracy = float(match.group(1)) if match else 0.0
        return (path.stat().st_mtime, accuracy)
    
    return max(candidates, key=score)


def _get_model_accuracy(model_path: Path) -> str:
    """Extract accuracy from model filename."""
    match = ACCURACY_PATTERN.search(model_path.name)
    return f"{match.group(1)}%" if match else "N/A"


def _load_calibrator(model_path: Path):
    """Load the calibrator .pkl file if it exists."""
    calibration_path = model_path.with_name(f"{model_path.stem}_calibration.pkl")
    if not calibration_path.exists():
        return None
    try:
        return joblib.load(calibration_path)
    except Exception:
        return None


def load_models():
    """Load XGBoost ML and O/U models with their calibrators."""
    global _models_cache
    
    if _models_cache["ml_model"] is None:
        ml_path = _select_model_path("ML")
        _models_cache["ml_model"] = xgb.Booster()
        _models_cache["ml_model"].load_model(str(ml_path))
        _models_cache["ml_calibrator"] = _load_calibrator(ml_path)
        _models_cache["ml_accuracy"] = _get_model_accuracy(ml_path)
        print(f"[OK] ML Model loaded: {ml_path.name} (Accuracy: {_models_cache['ml_accuracy']})")
    
    if _models_cache["uo_model"] is None:
        uo_path = _select_model_path("UO")
        _models_cache["uo_model"] = xgb.Booster()
        _models_cache["uo_model"].load_model(str(uo_path))
        _models_cache["uo_calibrator"] = _load_calibrator(uo_path)
        _models_cache["uo_accuracy"] = _get_model_accuracy(uo_path)
        print(f"[OK] O/U Model loaded: {uo_path.name} (Accuracy: {_models_cache['uo_accuracy']})")


def get_model_accuracy() -> str:
    """Return ML model accuracy string."""
    if _models_cache["ml_model"] is None:
        load_models()
    return _models_cache["ml_accuracy"]


# ===========================================
# FEATURE EXTRACTION
# ===========================================
# Simple cache for team data
_team_data_cache = {
    "df": None,
    "date": None
}

def _get_latest_team_data(team_db_path: Path = TEAM_DB_PATH) -> Optional[pd.DataFrame]:
    """
    Get the most recent team statistics table from TeamData.sqlite.
    Tables are named by date (e.g. '2026-01-26').
    Cached to avoid repeated DB reads per request.
    """
    global _team_data_cache
    
    # Return cache if valid and recent (optional check, for now simple exists check)
    if _team_data_cache["df"] is not None:
        return _team_data_cache["df"]

    try:
        print(f"[DEBUG] Connecting to DB: {team_db_path}")
        with sqlite3.connect(team_db_path) as con:
            # Get all table names
            cursor = con.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = []
            for (name,) in cursor.fetchall():
                try:
                    table_date = pd.to_datetime(name).date()
                    tables.append((name, table_date))
                except ValueError:
                    continue
            
            if not tables:
                print("[WARN] No team data tables found in TeamData.sqlite")
                return None
            
            # Get the most recent table
            tables.sort(key=lambda x: x[1], reverse=True)
            latest_table = tables[0][0]
            
            df = pd.read_sql_query(f'SELECT * FROM "{latest_table}"', con)
            print(f"[DATA] Using team data from: {latest_table} ({len(df)} teams)")
            
            _team_data_cache["df"] = df
            return df
            
    except Exception as e:
        print(f"[ERROR] Error loading team data: {e}")
        return None


def _build_game_features(team_df: pd.DataFrame, home_team: str, away_team: str) -> Optional[np.ndarray]:
    """
    Build feature vector for a single game from team statistics.
    
    Args:
        team_df: DataFrame with 30 teams' statistics
        home_team: Home team full name (e.g. "Los Angeles Lakers")
        away_team: Away team full name (e.g. "Boston Celtics")
    
    Returns:
        NumPy array of features, or None if teams not found
    """
    home_index = team_index_current.get(home_team)
    away_index = team_index_current.get(away_team)
    
    if home_index is None:
        print(f"[WARN] Unknown home team: {home_team}")
        return None
    if away_index is None:
        print(f"[WARN] Unknown away team: {away_team}")
        return None
    
    if len(team_df) != 30:
        print(f"[WARN] Expected 30 teams, got {len(team_df)}")
        return None
    
    # Get team rows
    home_series = team_df.iloc[home_index]
    away_series = team_df.iloc[away_index]
    
    # Concatenate home + away features
    combined = pd.concat([
        home_series,
        away_series.rename(index={col: f"{col}.1" for col in team_df.columns.values})
    ])
    
    # Drop non-feature columns
    feature_cols = [c for c in combined.index if c not in DROP_COLUMNS and "TEAM" not in c and "Date" not in c]
    features = combined[feature_cols].values.astype(float)
    
    return features


# ===========================================
# PREDICTION FUNCTIONS
# ===========================================
def predict_game(home_team: str, away_team: str, ou_line: float = 220.0) -> dict:
    """
    Predict the outcome of a single NBA game using the trained XGBoost model.
    
    Args:
        home_team: Home team full name
        away_team: Away team full name
        ou_line: Over/Under line (default 220.0)
    
    Returns:
        Dictionary with prediction results
    """
    # Ensure models are loaded
    load_models()
    
    # Get team statistics
    team_df = _get_latest_team_data()
    if team_df is None:
        return {
            "error": "No team data available",
            "winner": home_team,
            "home_win_probability": 50.0,
            "away_win_probability": 50.0,
            "under_over": "OVER",
            "ou_probability": 50.0,
            "is_mock": True
        }
    
    # Build features
    features = _build_game_features(team_df, home_team, away_team)
    if features is None:
        return {
            "error": f"Cannot build features for {home_team} vs {away_team}",
            "winner": home_team,
            "home_win_probability": 50.0,
            "away_win_probability": 50.0,
            "under_over": "OVER",
            "ou_probability": 50.0,
            "is_mock": True
        }
    
    # ML Prediction (Moneyline)
    features_2d = features.reshape(1, -1)
    
    # Try calibrator first, fall back to raw XGBoost if sklearn version mismatch
    try:
        if _models_cache["ml_calibrator"] is not None:
            ml_probs = _models_cache["ml_calibrator"].predict_proba(features_2d)[0]
        else:
            raise ValueError("No calibrator")
    except Exception:
        # Sklearn version mismatch - use raw XGBoost
        dmatrix = xgb.DMatrix(features_2d)
        ml_probs = _models_cache["ml_model"].predict(dmatrix)[0]
    
    # ml_probs[0] = away win prob, ml_probs[1] = home win prob
    away_prob = float(ml_probs[0]) * 100
    home_prob = float(ml_probs[1]) * 100
    
    # Determine winner
    if home_prob > away_prob:
        winner = home_team
        win_prob = home_prob
    else:
        winner = away_team
        win_prob = away_prob
    
    # O/U Prediction
    # Need to add OU column to features for O/U model
    features_with_ou = np.append(features, ou_line).reshape(1, -1)
    
    try:
        if _models_cache["uo_calibrator"] is not None:
            ou_probs = _models_cache["uo_calibrator"].predict_proba(features_with_ou)[0]
        else:
            raise ValueError("No calibrator")
    except Exception:
        # Sklearn version mismatch - use raw XGBoost
        dmatrix_ou = xgb.DMatrix(features_with_ou)
        ou_probs = _models_cache["uo_model"].predict(dmatrix_ou)[0]
    
    # ou_probs[0] = under, ou_probs[1] = over
    under_prob = float(ou_probs[0]) * 100
    over_prob = float(ou_probs[1]) * 100
    
    if over_prob > under_prob:
        under_over = "OVER"
        ou_probability = over_prob
    else:
        under_over = "UNDER"
        ou_probability = under_prob
    
    return {
        "home_team": home_team,
        "away_team": away_team,
        "winner": winner,
        "home_win_probability": round(home_prob, 1),
        "away_win_probability": round(away_prob, 1),
        "win_probability": round(win_prob, 1),
        "under_over": under_over,
        "ou_line": ou_line,
        "ou_probability": round(ou_probability, 1),
        "model_accuracy": _models_cache["ml_accuracy"],
        "is_mock": False,
        "error": None
    }


def predict_games(games: list) -> list:
    """
    Predict outcomes for multiple games.
    
    Args:
        games: List of dicts with 'home_team', 'away_team', optional 'ou_line'
    
    Returns:
        List of prediction dictionaries
    """
    results = []
    for game in games:
        home = game.get("home_team")
        away = game.get("away_team")
        ou_line = game.get("ou_line", 220.0)
        
        if not home or not away:
            results.append({"error": "Missing team names"})
            continue
        
        prediction = predict_game(home, away, ou_line if ou_line else 220.0)
        results.append(prediction)
    
    return results


# ===========================================
# UTILITY FUNCTIONS
# ===========================================
def get_all_teams() -> list:
    """Return list of all NBA team names."""
    return list(team_index_current.keys())


def validate_team_name(team_name: str) -> bool:
    """Check if team name is valid."""
    return team_name in team_index_current


# ===========================================
# TEST
# ===========================================
if __name__ == "__main__":
    print("\n[NBA Prediction API Test]")
    print("=" * 50)
    
    # Test single prediction
    result = predict_game("Los Angeles Lakers", "Boston Celtics", 220.5)
    print("\nLakers vs Celtics:")
    print(f"  Winner: {result['winner']}")
    print(f"  Home Prob: {result['home_win_probability']}%")
    print(f"  Away Prob: {result['away_win_probability']}%")
    print(f"  O/U: {result['under_over']} ({result['ou_probability']}%)")
    print(f"  Model Accuracy: {result['model_accuracy']}")
    print(f"  Is Mock: {result['is_mock']}")
    
    # Test multiple predictions
    test_games = [
        {"home_team": "Golden State Warriors", "away_team": "Miami Heat"},
        {"home_team": "Milwaukee Bucks", "away_team": "Denver Nuggets"},
    ]
    
    print("\nBatch predictions:")
    for pred in predict_games(test_games):
        print(f"  {pred['home_team']} vs {pred['away_team']}: {pred['winner']} ({pred['win_probability']}%)")
