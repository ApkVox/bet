import bisect
import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import toml

from src.Utils.Dictionaries import (
    team_index_07,
    team_index_08,
    team_index_12,
    team_index_13,
    team_index_14,
    team_index_current,
)

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "config.toml"
ODDS_DB_PATH = BASE_DIR / "Data" / "OddsData.sqlite"
TEAMS_DB_PATH = BASE_DIR / "Data" / "TeamData.sqlite"
OUTPUT_DB_PATH = BASE_DIR / "Data" / "dataset.sqlite"
OUTPUT_TABLE = "dataset_2012-26"

TEAM_INDEX_BY_SEASON = {
    "2007-08": team_index_07,
    "2008-09": team_index_08,
    "2009-10": team_index_08,
    "2010-11": team_index_08,
    "2011-12": team_index_08,
    "2012-13": team_index_12,
    "2013-14": team_index_13,
    "2014-15": team_index_14,
    "2015-16": team_index_14,
    "2016-17": team_index_14,
    "2017-18": team_index_14,
    "2018-19": team_index_14,
    "2019-20": team_index_14,
    "2020-21": team_index_14,
    "2021-22": team_index_14,
    "2022-23": team_index_current,
    "2023-24": team_index_current,
    "2024-25": team_index_current,
    "2025-26": team_index_current,
}


def table_exists(con, table_name):
    cursor = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def normalize_date(value):
    if isinstance(value, datetime):
        return value.date().isoformat()
    if hasattr(value, "date"):
        try:
            return value.date().isoformat()
        except Exception:
            pass
    return str(value)


def get_team_index_map(season_key):
    if season_key in TEAM_INDEX_BY_SEASON:
        return TEAM_INDEX_BY_SEASON[season_key]
    try:
        start_year = int(season_key.split("-")[0])
    except (ValueError, IndexError):
        return team_index_current
    return team_index_current if start_year >= 2022 else team_index_14


def list_snapshot_dates(teams_con):
    names = [r[0] for r in teams_con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    return sorted(n for n in names if len(n) == 10 and n[4] == "-" and n[7] == "-")


def fetch_team_table(teams_con, snapshot_dates, date_str):
    """Snapshot ESTRICTAMENTE anterior al partido.

    Las tablas de TeamData usan DateTo inclusivo: la del día D ya contiene el
    resultado del partido de D. Usarla filtra el resultado (fuga). En vivo se
    usa el último snapshot < D, así que el entrenamiento debe hacer lo mismo.
    """
    i = bisect.bisect_left(snapshot_dates, date_str[:10]) - 1
    if i < 0:
        return None
    return pd.read_sql_query(f'SELECT * FROM "{snapshot_dates[i]}"', teams_con)


def build_game_features(team_df, home_team, away_team, index_map):
    home_index = index_map.get(home_team)
    away_index = index_map.get(away_team)
    if home_index is None or away_index is None:
        return None
    if len(team_df.index) != 30:
        return None

    home_team_series = team_df.iloc[home_index]
    away_team_series = team_df.iloc[away_index]
    return pd.concat([
        home_team_series,
        away_team_series.rename(index={col: f"{col}.1" for col in team_df.columns.values}),
    ])


def select_odds_table(odds_con, season_key):
    candidates = [
        f"odds_{season_key}_new",
        f"odds_{season_key}",
        f"{season_key}_new",
        f"{season_key}",
    ]
    for table_name in candidates:
        if table_exists(odds_con, table_name):
            return table_name
    return None


def main():
    config = toml.load(CONFIG_PATH)

    scores = []
    win_margin = []
    ou_values = []
    ou_cover = []
    games = []
    days_rest_away = []
    days_rest_home = []
    game_dates = []
    seasons = []
    ml_home = []
    ml_away = []
    home_names = []
    away_names = []

    with sqlite3.connect(ODDS_DB_PATH) as odds_con, sqlite3.connect(TEAMS_DB_PATH) as teams_con:
        snapshot_dates = list_snapshot_dates(teams_con)
        for season_key in config["create-games"].keys():
            print(season_key)
            odds_table = select_odds_table(odds_con, season_key)
            if not odds_table:
                print(f"Missing odds tables for {season_key}.")
                continue

            odds_df = pd.read_sql_query(f'SELECT * FROM "{odds_table}"', odds_con)
            if odds_df.empty:
                print(f"No odds data for {season_key}.")
                continue

            index_map = get_team_index_map(season_key)

            for row in odds_df.itertuples(index=False):
                date_str = normalize_date(row.Date)
                team_df = fetch_team_table(teams_con, snapshot_dates, date_str)
                if team_df is None:
                    continue

                game = build_game_features(team_df, row.Home, row.Away, index_map)
                if game is None:
                    continue

                scores.append(row.Points)
                ou_values.append(row.OU)
                days_rest_home.append(row.Days_Rest_Home)
                days_rest_away.append(row.Days_Rest_Away)
                win_margin.append(1 if row.Win_Margin > 0 else 0)
                game_dates.append(date_str)
                seasons.append(season_key)
                ml_home.append(row.ML_Home)
                ml_away.append(row.ML_Away)
                home_names.append(row.Home)
                away_names.append(row.Away)

                if row.Points < row.OU:
                    ou_cover.append(0)
                elif row.Points > row.OU:
                    ou_cover.append(1)
                else:
                    ou_cover.append(2)

                games.append(game)

    if not games:
        print("No game rows produced. Check odds and team tables.")
        return

    season = pd.concat(games, ignore_index=True, axis=1).T
    frame = season.drop(columns=["TEAM_ID", "TEAM_ID.1"], errors="ignore")
    frame["Score"] = np.asarray(scores)
    frame["Home-Team-Win"] = np.asarray(win_margin)
    frame["OU"] = np.asarray(ou_values)
    frame["OU-Cover"] = np.asarray(ou_cover)
    frame["Days-Rest-Home"] = np.asarray(days_rest_home)
    frame["Days-Rest-Away"] = np.asarray(days_rest_away)
    # Solo para evaluación y mezcla con el mercado; el modelo independiente no las usa
    frame["Game_Date"] = game_dates
    frame["Season"] = seasons
    frame["ML_Home"] = np.asarray(ml_home, dtype=float)
    frame["ML_Away"] = np.asarray(ml_away, dtype=float)
    frame["Home"] = home_names
    frame["Away"] = away_names

    for field in frame.columns.values:
        if "TEAM_" in field or "Date" in field or field in ("Season", "Home", "Away"):
            continue
        frame[field] = frame[field].astype(float)

    with sqlite3.connect(OUTPUT_DB_PATH) as con:
        frame.to_sql(OUTPUT_TABLE, con, if_exists="replace", index=False)


if __name__ == "__main__":
    main()
