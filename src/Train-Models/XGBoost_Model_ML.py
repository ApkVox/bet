"""Modelo moneyline NBA (XGBoost sobre Elo + forma + descanso): backtest y modelo final.

Backtest walk-forward: para cada temporada S de BACKTEST_SEASONS se entrena solo con
temporadas anteriores y se predice S. Se compara contra el mercado (probabilidad
implícita sin vig) y contra la mezcla modelo+mercado que se muestra en la web.

El modelo es independiente del mercado (no ve cuotas): sirve para detectar valor.
La mezcla (peso `blend_weight`, guardado dentro del modelo) es la que elige el pick.
Las features salen de src/Utils/elo.py, el mismo código que usa la predicción en vivo.

Uso:
    PYTHONPATH=. python src/Train-Models/XGBoost_Model_ML.py            # backtest + guarda modelo
    PYTHONPATH=. python src/Train-Models/XGBoost_Model_ML.py --dry-run  # solo backtest
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

import history_db
from src.Utils import elo

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE_DIR / "Models" / "XGBoost_Models"

TARGET = "home_win"
FIRST_SEASON = "2008-09"  # 2007-08 solo calienta el Elo
BACKTEST_SEASONS = ["2022-23", "2023-24", "2024-25", "2025-26"]
PARAMS = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "tree_method": "hist",
    "max_depth": 3,
    "eta": 0.03,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 10,
    "lambda": 1.0,
    "seed": 42,
}
MAX_ROUNDS = 3000


def load_dataset():
    """Partidos (histórico local + nba_games de Supabase) con sus features previas."""
    games = elo.load_games(recent=history_db.get_game_results())
    feats, _ = elo.replay(games)
    df = games.join(feats)
    df["Season"] = df["date"].map(elo.season_of)
    df[TARGET] = (df["margin"] > 0).astype(int)
    df["p_market"] = elo.market_home_prob(df["ml_home"], df["ml_away"])
    return df[df["Season"] >= FIRST_SEASON].reset_index(drop=True)


def metrics(p, y):
    p = np.clip(np.asarray(p, dtype=float), 1e-6, 1 - 1e-6)
    return {
        "n": int(len(y)),
        "acc": float(((p > 0.5) == y).mean()),
        "logloss": float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean()),
        "brier": float(((p - y) ** 2).mean()),
        "p_local": float(p.mean()),
    }


def fit_blend_weight(p_model, p_market, y):
    grid = np.linspace(0, 1, 101)
    losses = [metrics(elo.blend(p_model, p_market, w), y)["logloss"] for w in grid]
    return float(grid[int(np.argmin(losses))])


def train(train_df, valid_df, feats):
    """Early stopping con valid_df y reentrena con train+valid usando esas rondas."""
    def dmatrix(d):
        return xgb.DMatrix(d[feats].astype(float), label=d[TARGET], feature_names=feats)
    probe = xgb.train(PARAMS, dmatrix(train_df), MAX_ROUNDS, evals=[(dmatrix(valid_df), "valid")],
                      early_stopping_rounds=100, verbose_eval=False)
    rounds = probe.best_iteration + 1
    return xgb.train(PARAMS, dmatrix(pd.concat([train_df, valid_df])), rounds), rounds


def predict(booster, df, feats):
    return booster.predict(xgb.DMatrix(df[feats].astype(float), feature_names=feats))


def backtest(df, feats):
    """Predicciones fuera de muestra para cada temporada de BACKTEST_SEASONS."""
    parts = []
    for season in BACKTEST_SEASONS:
        past = sorted(s for s in df["Season"].unique() if s < season)
        booster, rounds = train(df[df["Season"].isin(past[:-1])], df[df["Season"] == past[-1]], feats)
        test = df[df["Season"] == season]
        parts.append(test.assign(p_model=predict(booster, test, feats)))
        print(f"  {season}: entrenado con {past[0]}..{past[-1]} ({rounds} rondas, {len(test)} partidos)")
    return pd.concat(parts)


def report(oos, w):
    rows = []
    for season, g in list(oos.groupby("Season")) + [("TODAS", oos)]:
        y = g[TARGET].to_numpy()
        has_mkt = g["p_market"].notna().to_numpy()
        for name, p in (("modelo", g["p_model"]), ("mercado", g["p_market"]),
                        (f"mezcla w={w:.2f}", elo.blend(g["p_model"], g["p_market"], w))):
            p = np.asarray(p, dtype=float)
            rows.append({"temporada": season, "fuente": name, **metrics(p[has_mkt], y[has_mkt])})
    table = pd.DataFrame(rows)
    print(f"\nlocal gana realmente: {oos[TARGET].mean() * 100:.1f}%  (métricas sobre partidos con cuota)")
    print(table.to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    return table


def main():
    parser = argparse.ArgumentParser(description="Backtest y entrenamiento del modelo moneyline.")
    parser.add_argument("--dry-run", action="store_true", help="Solo backtest, no guarda modelo.")
    args = parser.parse_args()

    df = load_dataset()
    feats = elo.FEATURES
    print(f"{len(df)} partidos ({df['date'].min()} -> {df['date'].max()}), features: {feats}\nBacktest:")
    oos = backtest(df, feats)
    y = oos[TARGET].to_numpy()

    # Peso de la mezcla: se ajusta con las 2 primeras temporadas y se valida con las 2 últimas
    first = oos["Season"].isin(BACKTEST_SEASONS[:2]).to_numpy()
    last = oos["Season"].isin(BACKTEST_SEASONS[2:]).to_numpy() & oos["p_market"].notna().to_numpy()
    w_val = fit_blend_weight(oos["p_model"][first], oos["p_market"][first], y[first])
    held = metrics(elo.blend(oos["p_model"][last], oos["p_market"][last], w_val), y[last])
    mkt = metrics(oos["p_market"][last], y[last])
    print(f"\nMezcla validada: w={w_val:.2f} (ajustado en {BACKTEST_SEASONS[:2]}) -> en {BACKTEST_SEASONS[2:]}: "
          f"logloss {held['logloss']:.4f} vs mercado {mkt['logloss']:.4f}")
    w = fit_blend_weight(oos["p_model"], oos["p_market"], y)
    table = report(oos, w)

    if args.dry_run:
        return

    seasons = sorted(df["Season"].unique())
    booster, rounds = train(df[df["Season"].isin(seasons[:-1])], df[df["Season"] == seasons[-1]], feats)
    summary = table[table["temporada"] == "TODAS"].set_index("fuente")
    booster.set_attr(
        blend_weight=str(w),
        model_accuracy=f"{summary['acc'].iloc[0] * 100:.1f}%",
        pick_accuracy=f"{summary['acc'].iloc[2] * 100:.1f}%",
        trained_on=f"{seasons[0]}..{seasons[-1]} ({df['date'].max()})",
        backtest=json.dumps(table[table["temporada"] == "TODAS"].to_dict("records")),
        created=datetime.now().isoformat(timespec="seconds"),
    )
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    path = MODEL_DIR / f"XGBoost_{summary['acc'].iloc[0] * 100:.1f}%_ML_elo_nb{rounds}.json"
    booster.save_model(str(path))
    print(f"\nModelo guardado: {path.name} (blend_weight={w:.2f})")


if __name__ == "__main__":
    main()
