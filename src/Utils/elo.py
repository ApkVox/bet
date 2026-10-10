"""Features del modelo NBA a partir de marcadores: Elo, forma reciente y descanso.

Las features de un partido se calculan SOLO con partidos de fechas anteriores
(no hay fuga de información). Las usan el entrenamiento y la predicción en vivo.

Fuentes de partidos:
- Data/OddsData.sqlite: histórico 2007-08 -> ene 2026 (marcador y cuotas).
- Tabla nba_games de Supabase: partidos posteriores (la llena el job diario).
"""
import sqlite3
from collections import deque
from datetime import date as Date, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import toml

BASE_DIR = Path(__file__).resolve().parents[2]
ODDS_DB_PATH = BASE_DIR / "Data" / "OddsData.sqlite"
CONFIG_PATH = BASE_DIR / "config.toml"

FEATURES = ["elo_diff", "form_home", "form_away", "rest_home", "rest_away"]

# Elo estilo FiveThirtyEight
K = 20
HOME_ADV = 100
CARRY = 0.75  # al empezar temporada: 75% del Elo anterior + 25% de la media
FORM_N = 10  # forma = diferencia de puntos media de los últimos N partidos
MAX_REST = 10  # días de descanso (tope; sin partido previo = tope)

# Nombres antiguos o alternativos -> nombre actual de la franquicia
ALIASES = {
    "Charlotte Bobcats": "Charlotte Hornets",
    "Los Angeles Clippers": "LA Clippers",
    "New Jersey Nets": "Brooklyn Nets",
    "New Orleans Hornets": "New Orleans Pelicans",
    "Seattle SuperSonics": "Oklahoma City Thunder",
}


def normalize(name):
    name = str(name).strip()
    return ALIASES.get(name, name)


def season_of(day):
    """'2026-01-20' -> '2025-26' (la temporada empieza en otoño)."""
    year, month = int(day[:4]), int(day[5:7])
    start = year if month >= 8 else year - 1
    return f"{start}-{str(start + 1)[2:]}"


def in_season(day):
    """True si la fecha cae en temporada regular/playoffs según config.toml (excluye pretemporada)."""
    for value in toml.load(CONFIG_PATH)["get-data"].values():
        start = datetime.strptime(value["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(value["end_date"], "%Y-%m-%d").date()
        if start <= Date.fromisoformat(day[:10]) <= end:
            return True
    return False


def load_history():
    """Partidos del histórico local (una tabla de OddsData por temporada)."""
    with sqlite3.connect(ODDS_DB_PATH) as con:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        parts = []
        for start in range(2007, datetime.now().year + 1):
            season = f"{start}-{str(start + 1)[2:]}"
            table = next((t for t in (f"odds_{season}_new", f"odds_{season}", f"{season}_new", season)
                          if t in tables), None)
            if table:
                parts.append(pd.read_sql_query(
                    f'SELECT Date AS date, Home AS home, Away AS away, Win_Margin AS margin, '
                    f'ML_Home AS ml_home, ML_Away AS ml_away FROM "{table}"', con))
    return pd.concat(parts, ignore_index=True)


def load_games(recent=None):
    """Histórico + partidos recientes (filas de nba_games), normalizados y en orden."""
    games = load_history()
    if recent:
        r = pd.DataFrame(recent)
        r["margin"] = r["home_score"] - r["away_score"]
        games = pd.concat([games, r[["date", "home", "away", "margin", "ml_home", "ml_away"]]],
                          ignore_index=True)
    for col in ("margin", "ml_home", "ml_away"):  # el histórico trae 'NL' (sin línea) en algunas cuotas
        games[col] = pd.to_numeric(games[col], errors="coerce")
    games["date"] = games["date"].astype(str).str[:10]
    games["home"] = games["home"].map(normalize)
    games["away"] = games["away"].map(normalize)
    games = games.dropna(subset=["margin"]).drop_duplicates(["date", "home", "away"], keep="last")
    return games.sort_values("date", kind="stable").reset_index(drop=True)


class EloState:
    def __init__(self):
        self.elo = {}
        self.margins = {}
        self.last_day = {}
        self.season = None

    def _start_season(self, season):
        if season != self.season:
            if self.season is not None:
                self.elo = {t: CARRY * e + (1 - CARRY) * 1505 for t, e in self.elo.items()}
            self.season = season

    def _rest(self, team, day):
        last = self.last_day.get(team)
        if last is None:
            return float(MAX_REST)
        return float(min((Date.fromisoformat(day) - Date.fromisoformat(last)).days, MAX_REST))

    def _form(self, team):
        m = self.margins.get(team)
        return float(np.mean(m)) if m else 0.0

    def features(self, home, away, day):
        """Features de un partido en `day` usando solo lo ya registrado (partidos previos)."""
        self._start_season(season_of(day))
        return {
            "elo_diff": self.elo.get(home, 1500.0) + HOME_ADV - self.elo.get(away, 1500.0),
            "form_home": self._form(home),
            "form_away": self._form(away),
            "rest_home": self._rest(home, day),
            "rest_away": self._rest(away, day),
        }

    def update(self, home, away, day, margin):
        self._start_season(season_of(day))
        eh, ea = self.elo.get(home, 1500.0), self.elo.get(away, 1500.0)
        diff = eh + HOME_ADV - ea
        p_home = 1 / (1 + 10 ** (-diff / 400))
        winner_diff = diff if margin > 0 else -diff
        mult = (abs(margin) + 3) ** 0.8 / (7.5 + 0.006 * winner_diff)
        delta = K * mult * ((1.0 if margin > 0 else 0.0) - p_home)
        self.elo[home], self.elo[away] = eh + delta, ea - delta
        for team, m in ((home, margin), (away, -margin)):
            self.margins.setdefault(team, deque(maxlen=FORM_N)).append(m)
            self.last_day[team] = day


def replay(games):
    """Recorre los partidos en orden. Devuelve (features previas de cada partido, estado final)."""
    state = EloState()
    rows = []
    for g in games.itertuples(index=False):
        rows.append(state.features(g.home, g.away, g.date))
        state.update(g.home, g.away, g.date, g.margin)
    return pd.DataFrame(rows, index=games.index), state


# ---- Mercado y mezcla (compartido por entrenamiento y producción) ----

def american_to_prob(odds):
    """Cuota americana -> probabilidad. Cuotas inválidas (|cuota| < 100 o vacías) -> NaN."""
    odds = np.asarray(odds, dtype=float)
    odds = np.where(np.abs(odds) >= 100, odds, np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):  # np.where evalúa ambas ramas
        return np.where(odds < 0, -odds / (100 - odds), 100 / (np.abs(odds) + 100))


def market_home_prob(ml_home, ml_away):
    """Probabilidad implícita del local sin el margen de la casa (vig)."""
    home, away = american_to_prob(ml_home), american_to_prob(ml_away)
    with np.errstate(invalid="ignore"):  # sin cuota -> NaN, sin warning
        return home / (home + away)


def logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def blend(p_model, p_market, w):
    """Mezcla en escala logit: w=1 solo modelo, w=0 solo mercado. Sin cuota -> modelo."""
    p_model, p_market = np.asarray(p_model, dtype=float), np.asarray(p_market, dtype=float)
    mixed = 1 / (1 + np.exp(-(w * logit(p_model) + (1 - w) * logit(p_market))))
    return np.where(np.isnan(p_market), p_model, mixed)
