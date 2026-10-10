"""
===========================================
NBA Prediction API Module
===========================================
Predicción moneyline con XGBoost sobre Elo + forma + descanso (src/Utils/elo.py).

- Las features salen solo de partidos ANTERIORES a la fecha del juego
  (histórico local + marcadores guardados en Supabase por el job diario).
- `model_probability`: modelo independiente (no ve cuotas) -> para EV/valor.
- `win_probability`: mezcla con el mercado (peso `blend_weight` del modelo) -> el pick que se muestra.
"""
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import xgboost as xgb

import history_db
from src.Utils import elo
from src.Utils.Dictionaries import team_index_current
from src.Services.shadow_bettor import get_shadow_bettor


BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "Models" / "XGBoost_Models"
ACCURACY_PATTERN = re.compile(r"XGBoost_(\d+(?:\.\d+)?)%_")

_models_cache = {"ml_model": None, "ml_accuracy": "N/A", "blend_weight": 1.0}
_elo_cache = {"date": None, "state": None, "as_of": None}


def _select_model_path(kind: str) -> Path:
    """Modelo más reciente (y, a igualdad, de mayor acierto) para el tipo dado."""
    candidates = list(MODEL_DIR.glob(f"*{kind}*.json"))
    if not candidates:
        raise FileNotFoundError(f"No XGBoost {kind} model found in {MODEL_DIR}")

    def score(path):
        match = ACCURACY_PATTERN.search(path.name)
        return (path.stat().st_mtime, float(match.group(1)) if match else 0.0)

    return max(candidates, key=score)


def load_models():
    if _models_cache["ml_model"] is None:
        path = _select_model_path("ML")
        model = xgb.Booster()
        model.load_model(str(path))
        match = ACCURACY_PATTERN.search(path.name)
        _models_cache["ml_model"] = model
        _models_cache["ml_accuracy"] = model.attr("pick_accuracy") or (f"{match.group(1)}%" if match else "N/A")
        _models_cache["blend_weight"] = float(model.attr("blend_weight") or 1.0)
        print(f"[OK] ML Model loaded: {path.name} (pick accuracy: {_models_cache['ml_accuracy']}, "
              f"blend_weight: {_models_cache['blend_weight']:.2f})")


def get_model_accuracy() -> str:
    """Acierto del pick mostrado (mezcla) en el backtest."""
    load_models()
    return _models_cache["ml_accuracy"]


def _elo_state(game_date: date):
    """Estado Elo con todos los partidos ANTERIORES a game_date (cacheado por fecha)."""
    if _elo_cache["date"] != game_date:
        games = elo.load_games(recent=history_db.get_game_results())
        games = games[games["date"] < game_date.isoformat()]
        _, state = elo.replay(games)
        _elo_cache.update(date=game_date, state=state, as_of=games["date"].max())
        age = (game_date - date.fromisoformat(_elo_cache["as_of"])).days
        print(f"[ELO] {len(games)} partidos hasta {_elo_cache['as_of']} ({age} días antes del juego)")
    return _elo_cache["state"]


def predict_game(
    home_team: str,
    away_team: str,
    ou_line: float = 220.0,
    game_date: Optional[date] = None,
    home_odds: Optional[float] = None,
    away_odds: Optional[float] = None,
) -> dict:
    """
    Predice un partido. home_odds/away_odds: cuotas americanas (opcional; sin ellas
    el pick usa solo el modelo). También registra la decisión del ShadowBettor.
    """
    load_models()
    game_date = game_date or date.today()
    home, away = elo.normalize(home_team), elo.normalize(away_team)
    state = _elo_state(game_date)
    if home not in state.elo or away not in state.elo:
        return _mock_response(home_team, away_team, f"Equipo desconocido: {home_team} / {away_team}")

    features = state.features(home, away, game_date.isoformat())
    model = _models_cache["ml_model"]
    names = model.feature_names
    p_home_model = float(model.predict(xgb.DMatrix(np.array([[features[n] for n in names]]),
                                                   feature_names=names))[0])
    p_home_market = float(elo.market_home_prob(home_odds if home_odds is not None else np.nan,
                                               away_odds if away_odds is not None else np.nan))
    p_home = float(elo.blend(p_home_model, p_home_market, _models_cache["blend_weight"]))

    home_wins = p_home >= 0.5
    winner = home_team if home_wins else away_team
    pick = (lambda p: p) if home_wins else (lambda p: 1 - p)

    # Shadow Bettor: decide con la probabilidad del modelo independiente (opcional, nunca bloquea)
    home_decision = away_decision = None
    try:
        shadow = get_shadow_bettor()
        game_dt = datetime(game_date.year, game_date.month, game_date.day)
        if home_odds:
            home_decision = shadow.process_game(game_id=f"{game_date}_{home_team}_HOME",
                                                probability=p_home_model, odds=home_odds, game_date=game_dt)
        if away_odds:
            away_decision = shadow.process_game(game_id=f"{game_date}_{away_team}_AWAY",
                                                probability=1 - p_home_model, odds=away_odds, game_date=game_dt)
    except Exception as shadow_err:
        print(f"[shadow_bettor] Skipped (non-critical): {shadow_err}")

    def decision(d):
        return {"decision": d.decision if d else "N/A", "stake_units": d.stake_units if d else 0,
                "reason": d.reason if d else ""}

    return {
        "home_team": home_team,
        "away_team": away_team,
        "winner": winner,
        "home_win_probability": round(p_home * 100, 1),
        "away_win_probability": round((1 - p_home) * 100, 1),
        "win_probability": round(pick(p_home) * 100, 1),
        "model_probability": round(pick(p_home_model) * 100, 1),
        "market_probability": None if np.isnan(p_home_market) else round(pick(p_home_market) * 100, 1),
        "under_over": "N/A",
        "ou_line": ou_line,
        "ou_probability": 0.0,
        "model_accuracy": _models_cache["ml_accuracy"],
        "features": {k: round(v, 2) for k, v in features.items()},
        "is_mock": False,
        "error": None,
        "data_snapshot_date": _elo_cache["as_of"],
        "game_date": str(game_date),
        "bet_analysis": {"home": decision(home_decision), "away": decision(away_decision)},
    }


def _mock_response(home_team, away_team, error_msg):
    return {
        "home_team": home_team,
        "away_team": away_team,
        "error": error_msg,
        "winner": home_team,
        "home_win_probability": 50.0,
        "away_win_probability": 50.0,
        "win_probability": 50.0,
        "under_over": "N/A",
        "ou_probability": 0.0,
        "is_mock": True,
        "data_snapshot_date": None,
        "bet_analysis": {},
    }


def predict_games(games: list, default_game_date: Optional[date] = None) -> list:
    """Predice varios partidos: dicts con 'home_team', 'away_team' y opcional 'game_date', cuotas."""
    results = []
    for game in games:
        home, away = game.get("home_team"), game.get("away_team")
        game_date = game.get("game_date", default_game_date)
        if isinstance(game_date, str):
            game_date = pd.to_datetime(game_date).date()
        if not home or not away:
            results.append(_mock_response(home or "", away or "", "Missing team names"))
            continue
        results.append(predict_game(home, away, game.get("ou_line") or 220.0, game_date,
                                    home_odds=game.get("home_odds"), away_odds=game.get("away_odds")))
    return results


def get_all_teams() -> list:
    """Return list of all NBA team names."""
    return list(team_index_current.keys())


def validate_team_name(team_name: str) -> bool:
    """Check if team name is valid."""
    return team_name in team_index_current


if __name__ == "__main__":
    for p in predict_games([
        {"home_team": "Golden State Warriors", "away_team": "Miami Heat", "home_odds": -150, "away_odds": 130},
        {"home_team": "Milwaukee Bucks", "away_team": "Denver Nuggets"},
        {"home_team": "Boston", "away_team": "Detroit"},
    ]):
        print(f"{p['away_team']} @ {p['home_team']}: {p['winner']} {p['win_probability']}% "
              f"(modelo {p.get('model_probability')}%, mercado {p.get('market_probability')}%) "
              f"mock={p['is_mock']} {p.get('error') or ''}")
