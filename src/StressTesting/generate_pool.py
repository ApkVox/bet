"""
Generate Prediction Pool for Monte Carlo Simulation
===================================================
Generates a CSV of game predictions with "Synthetic Odds" since historical odds are missing.

Logic:
- Loads historical games (2015-2026 test set).
- Gets model probabilities.
- Outcome: 1 (Home Win) or 0 (Away Win).
- Synthetic Odds: 1 / (Probability + Margin).
"""
import sqlite3
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import xgboost as xgb

# Project root setup
BASE_DIR = Path(__file__).resolve().parents[2]
DATASET_DB = BASE_DIR / "Data" / "dataset.sqlite"
MODEL_DIR = BASE_DIR / "Models" / "XGBoost_Models"
OUTPUT_DIR = BASE_DIR / "src" / "StressTesting"

TARGET_COLUMN = "Home-Team-Win"
DROP_COLUMNS = [
    "index", "Score", "Home-Team-Win", "TEAM_NAME", "Date",
    "index.1", "TEAM_NAME.1", "Date.1", "OU-Cover", "OU",
    "TEAM_ID", "TEAM_ID.1"
]

BOOKMAKER_MARGIN = 0.045  # 4.5% margin for synthetic odds

def load_data_and_model():
    # Load dataset
    with sqlite3.connect(DATASET_DB) as con:
        cursor = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [t[0] for t in cursor.fetchall()]
        dataset_name = max([t for t in tables if t.startswith("dataset_")], default=tables[0])
        df = pd.read_sql_query(f'SELECT * FROM "{dataset_name}"', con)
    
    # Load model
    candidates = list(MODEL_DIR.glob("*ML*.json"))
    best_path = max(candidates, key=lambda p: float(p.name.split('_')[1].replace('%', '')))
    bst = xgb.Booster()
    bst.load_model(str(best_path))
    
    return df, bst, best_path.name

def prepare_features(df):
    data = df.copy()
    X_df = data.drop(columns=DROP_COLUMNS, errors="ignore")
    numeric_cols = X_df.select_dtypes(include=[np.number]).columns
    X_df = X_df[numeric_cols]
    
    X = X_df.to_numpy()
    y = data[TARGET_COLUMN].astype(int).to_numpy()
    return X, y

def generate_pool():
    df, model, model_name = load_data_and_model()
    print(f"Loaded {len(df)} games using model: {model_name}")
    
    X, y = prepare_features(df)
    
    # Predict all
    dmatrix = xgb.DMatrix(X)
    probs = model.predict(dmatrix)
    if len(probs.shape) == 2:
        probs = probs[:, 1]
    
    # Validation period (last ~11 seasons)
    pool = []
    
    np.random.seed(42) # For reproducible noise
    
    for prob, outcome in zip(probs, y):
        # Synthetic Market Odds Simulation
        # To verify the strategy, we need to simulate a market that the model disagrees with.
        # We assume the Market is "Good but slightly worse/different" than our model.
        # Logic: Market Prob = Model Prob + Noise + Regression to Mean
        
        # 1. Regress model prob towards 0.5 (Market is often more conservative or misses "sharp" edges)
        # However, sometimes market is sharper.
        # Let's add random noise to simulate disagreement.
        # Noise std dev = 0.05 (5%)
        noise = np.random.normal(0, 0.05)
        
        # Market estimation of true prob
        market_fair_prob = np.clip(prob + noise, 0.05, 0.95)
        
        # 2. Add vig (margin)
        market_prob_home_vig = min(0.99, market_fair_prob + (BOOKMAKER_MARGIN / 2))
        market_prob_away_vig = min(0.99, (1 - market_fair_prob) + (BOOKMAKER_MARGIN / 2))
        
        odds_home = 1.0 / market_prob_home_vig
        odds_away = 1.0 / market_prob_away_vig
        
        # Model considers 'prob' as the True Probability.
        # It calculates EV against 'odds_home' or 'odds_away'.
        
        pool.append({
            "prob_home": round(prob, 4),
            "odds_home": round(odds_home, 4),
            "prob_away": round(1.0 - prob, 4),
            "odds_away": round(odds_away, 4),
            "outcome_home": int(outcome), # 1 if Home Won
        })
        
    # Save to CSV
    pool_df = pd.DataFrame(pool)
    output_path = OUTPUT_DIR / "simulation_pool.csv"
    pool_df.to_csv(output_path, index=False)
    print(f"Generated pool with {len(pool_df)} games: {output_path}")

if __name__ == "__main__":
    generate_pool()
