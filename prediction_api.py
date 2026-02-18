"""
===========================================
NBA Prediction API Module
===========================================
Clean prediction module that properly uses XGBoost models.
This replaces the broken random-based predictions in main.py.
"""
import gc
import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xgboost as xgb

from src.Utils.Dictionaries import team_index_current
from src.Services.shadow_bettor import get_shadow_bettor


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
    "uo_model": None,
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


def load_models():
    """Load XGBoost ML and O/U models (without calibrators to save memory)."""
    global _models_cache
    
    if _models_cache["ml_model"] is None:
        ml_path = _select_model_path("ML")
        _models_cache["ml_model"] = xgb.Booster()
        _models_cache["ml_model"].load_model(str(ml_path))
        _models_cache["ml_accuracy"] = _get_model_accuracy(ml_path)
        print(f"[OK] ML Model loaded: {ml_path.name} (Accuracy: {_models_cache['ml_accuracy']})")
    
    if _models_cache["uo_model"] is None:
        uo_path = _select_model_path("UO")
        _models_cache["uo_model"] = xgb.Booster()
        _models_cache["uo_model"].load_model(str(uo_path))
        _models_cache["uo_accuracy"] = _get_model_accuracy(uo_path)
        print(f"[OK] O/U Model loaded: {uo_path.name} (Accuracy: {_models_cache['uo_accuracy']})")


def get_model_accuracy() -> str:
    """Return ML model accuracy string."""
    if _models_cache["ml_model"] is None:
        load_models()
    return _models_cache["ml_accuracy"]


# ===========================================
# FEATURE EXTRACTION (POINT-IN-TIME SAFE)
# ===========================================
# Cache only the selected table name (NOT the DataFrame) to save memory
_team_data_cache = {
    "table_name": None,
    "data_date": None,  # Date of the snapshot used
    "target_date": None  # Target date it was fetched for
}


class DataLeakageError(Exception):
    """Raised when data selection would cause temporal leakage."""
    pass


def _get_available_table_dates(team_db_path: Path = TEAM_DB_PATH) -> list:
    """Get all available snapshot dates from TeamData.sqlite."""
    try:
        with sqlite3.connect(team_db_path) as con:
            cursor = con.execute("SELECT name FROM sqlite_master WHERE type='table'")
            dates = []
            for (name,) in cursor.fetchall():
                try:
                    table_date = pd.to_datetime(name).date()
                    dates.append(table_date)
                except ValueError:
                    continue
            return sorted(dates)
    except Exception as e:
        print(f"[ERROR] Could not list table dates: {e}")
        return []


def _resolve_table_for_date(
    target_date: date,
    team_db_path: Path = TEAM_DB_PATH
) -> tuple[Optional[str], Optional[date]]:
    """
    POINT-IN-TIME SAFE: Find the correct table name from BEFORE the target date.
    Caches only the table name (not the data) to save memory.
    
    Returns:
        Tuple of (table_name, snapshot_date)
        Returns (None, None) if no valid snapshot exists
    """
    global _team_data_cache
    
    # Check cache - reuse if same target_date
    if (_team_data_cache["table_name"] is not None and 
        _team_data_cache["target_date"] == target_date):
        print(f"[CACHE HIT] Reusing table {_team_data_cache['table_name']} for target {target_date}")
        return _team_data_cache["table_name"], _team_data_cache["data_date"]
    
    try:
        print(f"[POINT-IN-TIME] Resolving table for game date: {target_date}")
        
        with sqlite3.connect(team_db_path) as con:
            cursor = con.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = []
            for (name,) in cursor.fetchall():
                try:
                    table_date = pd.to_datetime(name).date()
                    tables.append((name, table_date))
                except ValueError:
                    continue
            
            if not tables:
                print("[ERROR] No team data tables found in TeamData.sqlite")
                return None, None
            
            # CRITICAL: Filter to only tables with date STRICTLY BEFORE target_date
            valid_tables = [(name, d) for name, d in tables if d < target_date]
            
            if not valid_tables:
                available_dates = sorted([d for _, d in tables])
                print(f"[ERROR] No valid snapshots before {target_date}.")
                raise DataLeakageError(
                    f"No team data available before {target_date}. "
                    f"Earliest available: {min(available_dates) if available_dates else 'N/A'}"
                )
            
            # Select the most recent valid table (closest to but before target_date)
            valid_tables.sort(key=lambda x: x[1], reverse=True)
            selected_table, selected_date = valid_tables[0]
            
            data_age_days = (target_date - selected_date).days
            print(f"[POINT-IN-TIME] ✓ Using snapshot: {selected_date} (age: {data_age_days}d)")
            
            if data_age_days > 3:
                print(f"[WARNING] Data is {data_age_days} days old!")
            
            # Cache only the table name, NOT the data
            _team_data_cache["table_name"] = selected_table
            _team_data_cache["data_date"] = selected_date
            _team_data_cache["target_date"] = target_date
            
            return selected_table, selected_date
            
    except DataLeakageError:
        raise
    except Exception as e:
        print(f"[ERROR] Error resolving table: {e}")
        return None, None


def _get_team_data_for_date(
    target_date: date,
    team_db_path: Path = TEAM_DB_PATH
) -> tuple[Optional[pd.DataFrame], Optional[date]]:
    """
    MEMORY-OPTIMIZED: Loads team data, uses it, then lets GC reclaim it.
    The DataFrame is NOT cached — only the table name is cached.
    """
    table_name, snapshot_date = _resolve_table_for_date(target_date, team_db_path)
    if table_name is None:
        return None, None
    
    try:
        with sqlite3.connect(team_db_path) as con:
            df = pd.read_sql_query(f'SELECT * FROM "{table_name}"', con)
            print(f"[POINT-IN-TIME] Loaded {len(df)} teams from {table_name}")
            return df, snapshot_date
    except Exception as e:
        print(f"[ERROR] Error loading team data: {e}")
        return None, None


def _get_latest_team_data(team_db_path: Path = TEAM_DB_PATH) -> Optional[pd.DataFrame]:
    """
    DEPRECATED: Use _get_team_data_for_date() instead for point-in-time safety.
    """
    yesterday = date.today() - timedelta(days=1)
    print(f"[DEPRECATED] _get_latest_team_data called without date. Using {yesterday} as cutoff.")
    df, _ = _get_team_data_for_date(yesterday, team_db_path)
    return df


def clear_team_data_cache():
    """Clear the team data cache."""
    global _team_data_cache
    _team_data_cache = {"table_name": None, "data_date": None, "target_date": None}
    print("[CACHE] Team data cache cleared")


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
def predict_game(
    home_team: str,
    away_team: str,
    ou_line: float = 220.0,
    game_date: Optional[date] = None,
    home_odds: Optional[float] = None,
    away_odds: Optional[float] = None
) -> dict:
    """
    Predict the outcome of a single NBA game using the trained XGBoost model.
    Also executes ShadowBettor pipeline to log decision.
    
    Args:
        home_team: Home team full name
        away_team: Away team full name
        ou_line: Over/Under line (default 220.0)
        game_date: Date of the game (defaults to today).
        home_odds: Optional decimal odds for Home Win
        away_odds: Optional decimal odds for Away Win
    
    Returns:
        Dictionary with prediction results and bet recommendations.
    """
    # Ensure models are loaded
    load_models()
    
    # Default to today if no game_date provided
    if game_date is None:
        game_date = date.today()
    
    # Get team data (POINT-IN-TIME SAFE)
    try:
        team_df, data_snapshot_date = _get_team_data_for_date(game_date)
    except DataLeakageError as e:
        return _mock_response(home_team, str(e))
    
    if team_df is None:
        return _mock_response(home_team, "No team data available")
    
    # Build features
    features = _build_game_features(team_df, home_team, away_team)
    if features is None:
        return _mock_response(home_team, f"Cannot build features for {home_team} vs {away_team}")
    
    # ML Prediction (Moneyline) — raw XGBoost softmax (no calibrator to save memory)
    features_2d = features.reshape(1, -1)
    ml_probs = _models_cache["ml_model"].predict(xgb.DMatrix(features_2d))[0]
    
    away_prob_raw = float(ml_probs[0])
    home_prob_raw = float(ml_probs[1])
    away_prob = away_prob_raw * 100
    home_prob = home_prob_raw * 100
    
    if home_prob > away_prob:
        winner = home_team
        win_prob = home_prob
    else:
        winner = away_team
        win_prob = away_prob
    
    # Shadow Bettor Integration (Audit Decisions)
    shadow = get_shadow_bettor()
    
    # Home Bet Evaluation
    home_decision = None
    if home_odds:
        home_decision = shadow.process_game(
            game_id=f"{game_date}_{home_team}_HOME",
            probability=home_prob_raw,
            odds=home_odds,
            game_date=datetime(game_date.year, game_date.month, game_date.day) # Convert to datetime
        )

    # Away Bet Evaluation
    away_decision = None
    if away_odds:
        away_decision = shadow.process_game(
            game_id=f"{game_date}_{away_team}_AWAY",
            probability=away_prob_raw,
            odds=away_odds,
            game_date=datetime(game_date.year, game_date.month, game_date.day)
        )
    
    # O/U Prediction — raw XGBoost softmax (no calibrator to save memory)
    features_with_ou = np.append(features, ou_line).reshape(1, -1)
    ou_probs = _models_cache["uo_model"].predict(xgb.DMatrix(features_with_ou))[0]
    
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
        "error": None,
        "data_snapshot_date": str(data_snapshot_date) if data_snapshot_date else None,
        "game_date": str(game_date),
        "bet_analysis": {
            "home": {
                "decision": home_decision.decision if home_decision else "N/A",
                "stake_units": home_decision.stake_units if home_decision else 0,
                "reason": home_decision.reason if home_decision else ""
            },
            "away": {
                "decision": away_decision.decision if away_decision else "N/A",
                "stake_units": away_decision.stake_units if away_decision else 0,
                "reason": away_decision.reason if away_decision else ""
            }
        }
    }

def _mock_response(home_team, error_msg):
    return {
        "error": error_msg,
        "winner": home_team,
        "home_win_probability": 50.0,
        "away_win_probability": 50.0,
        "under_over": "OVER",
        "ou_probability": 50.0,
        "is_mock": True,
        "data_snapshot_date": None,
        "bet_analysis": {}
    }


def predict_games(games: list, default_game_date: Optional[date] = None) -> list:
    """
    Predict outcomes for multiple games.
    
    Args:
        games: List of dicts with 'home_team', 'away_team', optional 'ou_line', optional 'game_date'
        default_game_date: Default date to use if individual games don't specify one
    
    Returns:
        List of prediction dictionaries
    """
    results = []
    for game in games:
        home = game.get("home_team")
        away = game.get("away_team")
        ou_line = game.get("ou_line", 220.0)
        
        # Support game_date from individual game or use default
        game_date = game.get("game_date", default_game_date)
        if isinstance(game_date, str):
            game_date = pd.to_datetime(game_date).date()
        
        if not home or not away:
            results.append({"error": "Missing team names"})
            continue
        
        prediction = predict_game(home, away, ou_line if ou_line else 220.0, game_date)
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
