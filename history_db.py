import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional


BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "Data" / "history.db"

def _get_table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    """Return existing column names for a table."""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}

def _ensure_football_schema(conn: sqlite3.Connection) -> None:
    """
    Ensure football_predictions has all expected columns.
    This keeps old production DBs compatible without destructive migrations.
    """
    required_columns = {
        "date": "TEXT",
        "league": "TEXT DEFAULT 'ENG-Premier League'",
        "match_id": "TEXT",
        "home_team": "TEXT",
        "away_team": "TEXT",
        "prediction": "TEXT",
        "prob_home": "REAL",
        "prob_draw": "REAL",
        "prob_away": "REAL",
        "odd_home": "REAL",
        "odd_draw": "REAL",
        "odd_away": "REAL",
        "status": "TEXT DEFAULT 'PENDING'",
        "result": "TEXT",
        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    }
    existing_columns = _get_table_columns(conn, "football_predictions")
    for col, col_type in required_columns.items():
        if col not in existing_columns:
            conn.execute(f"ALTER TABLE football_predictions ADD COLUMN {col} {col_type}")

def _ensure_predictions_schema(conn: sqlite3.Connection) -> None:
    """Add odds_home / odds_away columns to predictions if missing."""
    existing = _get_table_columns(conn, "predictions")
    if "odds_home" not in existing:
        conn.execute("ALTER TABLE predictions ADD COLUMN odds_home REAL")
    if "odds_away" not in existing:
        conn.execute("ALTER TABLE predictions ADD COLUMN odds_away REAL")


def _ensure_recommendations_schema(conn: sqlite3.Connection) -> None:
    existing = _get_table_columns(conn, "daily_recommendations")
    if "result" not in existing:
        conn.execute("ALTER TABLE daily_recommendations ADD COLUMN result TEXT DEFAULT 'pending'")
    if "reasoning" not in existing:
        conn.execute("ALTER TABLE daily_recommendations ADD COLUMN reasoning TEXT")


def init_history_db():
    """Crea la tabla de historial si no existe"""
    DB_PATH.parent.mkdir(exist_ok=True)
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                match_id TEXT UNIQUE NOT NULL,
                home_team TEXT,
                away_team TEXT,
                predicted_winner TEXT,
                prob_model REAL,
                prob_final REAL,
                odds INTEGER,
                ev_value REAL,
                kelly_stake REAL,
                warning_level TEXT,
                result TEXT DEFAULT 'PENDING',  -- 'WIN', 'LOSS', 'PENDING'
                profit REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # New table for Football
        conn.execute("""
            CREATE TABLE IF NOT EXISTS football_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                league TEXT NOT NULL,
                match_id TEXT UNIQUE NOT NULL,
                home_team TEXT,
                away_team TEXT,
                prediction TEXT, -- '1', 'X', '2'
                prob_home REAL,
                prob_draw REAL,
                prob_away REAL,
                odd_home REAL,
                odd_draw REAL,
                odd_away REAL,
                status TEXT DEFAULT 'PENDING',
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        _ensure_football_schema(conn)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS match_news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                match_id TEXT NOT NULL,
                sport TEXT DEFAULT 'nba',
                headline TEXT,
                key_points TEXT,
                injuries TEXT,
                impact_assessment TEXT,
                confidence_modifier TEXT DEFAULT 'neutral',
                raw_response TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, match_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                sport TEXT DEFAULT 'nba',
                recommendations TEXT,
                parlay_analysis TEXT,
                parlay_odds REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        _ensure_predictions_schema(conn)
        _ensure_recommendations_schema(conn)
        conn.commit()
    print("[OK] history.db inicializada (NBA + Football + News + Recommendations)")


def save_prediction(prediction_data: dict):
    """Guarda una predicción NBA con cuotas separadas por equipo."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO predictions 
            (date, match_id, home_team, away_team, predicted_winner, 
             prob_model, prob_final, odds, ev_value, kelly_stake, warning_level,
             odds_home, odds_away, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (
            prediction_data['date'],
            prediction_data['match_id'],
            prediction_data['home_team'],
            prediction_data['away_team'],
            prediction_data['winner'],
            prediction_data['win_probability'],
            prediction_data['win_probability'],
            prediction_data['market_odds'],
            prediction_data['ev_value'],
            prediction_data['kelly_stake_pct'],
            prediction_data['warning_level'],
            prediction_data.get('home_odds'),
            prediction_data.get('away_odds'),
        ))
        conn.commit()


def save_historical_prediction(prediction_data: dict):
    """Guarda una predicción histórica con resultado ya conocido"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO predictions 
            (date, match_id, home_team, away_team, predicted_winner, 
             prob_model, prob_final, odds, ev_value, kelly_stake, warning_level, result, profit)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction_data['date'],
            prediction_data['match_id'],
            prediction_data['home_team'],
            prediction_data['away_team'],
            prediction_data['winner'],
            prediction_data['win_probability'],
            prediction_data['win_probability'],
            prediction_data['market_odds'],
            prediction_data['ev_value'],
            prediction_data['kelly_stake_pct'],
            prediction_data['warning_level'],
            prediction_data.get('result', 'PENDING'),
            prediction_data.get('profit', 0.0)
        ))
        conn.commit()


def update_results(date: str, results: dict):

    """
    Actualiza resultados reales y calcula profit.
    
    Args:
        date: Fecha de los partidos
        results: {'Lakers vs Celtics': 'Lakers', ...}
    """
    with sqlite3.connect(DB_PATH) as conn:
        for match_id, actual_winner in results.items():
            cursor = conn.execute("""
                SELECT kelly_stake, odds, predicted_winner, odds_home, odds_away, home_team
                FROM predictions
                WHERE date = ? AND match_id = ?
            """, (date, match_id))
            
            row = cursor.fetchone()
            if not row:
                continue
            
            kelly_stake, odds_american, predicted_winner, odds_home, odds_away, home_team = row
            is_win = (predicted_winner == actual_winner)
            
            if is_win:
                decimal_odds = odds_home if predicted_winner == home_team else odds_away
                if decimal_odds and decimal_odds > 1:
                    profit = kelly_stake * (decimal_odds - 1)
                elif odds_american:
                    am = float(odds_american)
                    profit = kelly_stake * (am / 100) if am > 0 else kelly_stake * (100 / abs(am))
                else:
                    profit = 0
            else:
                profit = -kelly_stake
            
            # Actualizar
            conn.execute("""
                UPDATE predictions
                SET result = ?,
                    profit = ?
                WHERE date = ? AND match_id = ?
            """, ('WIN' if is_win else 'LOSS', profit, date, match_id))
        
        conn.commit()


def save_football_prediction(prediction_data: dict, match_id: str, date: str):
    """Guarda una predicción de fútbol"""
    with sqlite3.connect(DB_PATH) as conn:
        # prediction_data comes from football_api.predict_match
        # keys: prediction, probs{home, draw, away}, etc.
        
        # safely get probs
        probs = prediction_data.get('probs', {})
        
        conn.execute("""
            INSERT OR REPLACE INTO football_predictions 
            (date, league, match_id, home_team, away_team, prediction, 
             prob_home, prob_draw, prob_away, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
        """, (
            date,
            prediction_data.get('league', 'ENG-Premier League'),
            match_id,
            prediction_data['home_team'],
            prediction_data['away_team'],
            prediction_data['prediction'],
            probs.get('home', 0),
            probs.get('draw', 0),
            probs.get('away', 0)
        ))
        conn.commit()


def get_football_history(days: int = 30) -> list[dict]:
    """Obtiene historial de predicciones de fútbol"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT date, league, match_id, home_team, away_team, prediction,
                   prob_home, prob_draw, prob_away, result, created_at
            FROM football_predictions
            WHERE date >= date('now', '-' || ? || ' days')
            ORDER BY date DESC, created_at DESC
        """, (days,))
        
        rows = cursor.fetchall()
        
        return [
            {
                "date": row[0],
                "league": row[1],
                "match_id": row[2],
                "home_team": row[3],
                "away_team": row[4],
                "prediction": row[5],
                "probs": {
                    "home": row[6],
                    "draw": row[7],
                    "away": row[8]
                },
                "result": row[9],
                "created_at": row[10]
            }
            for row in rows
        ]


def get_history(days: int = 7) -> list[dict]:
    """Obtiene historial de predicciones"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT date, match_id, home_team, away_team, predicted_winner, prob_final, odds, 
                   ev_value, kelly_stake, result, profit
            FROM predictions
            WHERE date >= date('now', '-' || ? || ' days')
            ORDER BY date DESC, created_at DESC
        """, (days,))
        
        rows = cursor.fetchall()
        
        return [
            {
                "date": row[0],
                "match": row[1],
                "home_team": row[2],
                "away_team": row[3],
                "predicted_winner": row[4],
                "probability": row[5],
                "odds": row[6],
                "ev": row[7],
                "kelly_stake": row[8],
                "result": row[9],
                "profit": row[10]
            }
            for row in rows
        ]


def get_team_prediction_accuracy(team_name: str) -> dict:
    """Obtiene la precisión de predicción para un equipo específico"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins
            FROM predictions
            WHERE (home_team LIKE ? OR away_team LIKE ?)
            AND result != 'PENDING'
        """, (f"%{team_name}%", f"%{team_name}%"))
        
        row = cursor.fetchone()
        total, wins = row[0] or 0, row[1] or 0
        
        return {
            "team": team_name,
            "total_bets": total,
            "wins": wins,
            "accuracy": round((wins / total * 100) if total > 0 else 0, 1)
        }

def get_predictions_by_date_light(date: str) -> list[dict]:
    """Versión ligera que NO importa prediction_api (para uso en Render)."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT date, match_id, home_team, away_team, predicted_winner, 
                   prob_final, odds, ev_value, kelly_stake, warning_level, result,
                   odds_home, odds_away
            FROM predictions
            WHERE date = ?
        """, (date,))
        
        rows = cursor.fetchall()
        predictions = []
        
        for row in rows:
            p = {
                "match_id": row[1],
                "home_team": row[2],
                "away_team": row[3],
                "winner": row[4],
                "win_probability": row[5] or 0,
                "under_over": "N/A",
                "ou_line": 0,
                "ou_probability": 0,
                "ai_analysis": None,
                "is_mock": False,
                "odds_home": row[11],
                "odds_away": row[12],
                "ev_score": row[7],
                "kelly_stake": row[8],
                "warning_level": row[9],
                "game_status": row[10],
                "home_score": None,
                "away_score": None,
                "implied_prob": None,
                "discrepancy": None,
                "value_type": None,
                "sentiment_score": None,
                "key_injuries": None,
                "risk_analysis": None
            }
            predictions.append(p)
            
        return predictions


def get_predictions_by_date(date: str) -> list[dict]:
    """Obtiene predicciones guardadas para una fecha específica"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT date, match_id, home_team, away_team, predicted_winner, 
                   prob_final, odds, ev_value, kelly_stake, warning_level, result
            FROM predictions
            WHERE date = ?
        """, (date,))
        
        rows = cursor.fetchall()
        
        predictions = []
        import prediction_api # to use MatchPrediction class if needed or just dict
        
        for row in rows:
            # We need to reconstruct MatchPrediction objects or equivalent dicts
            # For read-through cache, we need to return objects compatible with the main API response
            # predict_today expects MatchPrediction objects
            
            # (date, match_id, home_team, away_team, predicted_winner, prob_final, odds, ev_value, kelly_stake, warning_level, result)
            
            # Reconstruct dictionary first
            p = {
                "date": row[0],
                "match_id": row[1],
                "home_team": row[2],
                "away_team": row[3],
                "winner": row[4],
                "win_probability": row[5],
                "market_odds_home": row[6] if row[4] == row[2] else 0, # Approximation if we only stored 'odds'
                "market_odds_away": row[6] if row[4] == row[3] else 0,
                "ev_value": row[7],
                "kelly_stake_pct": row[8],
                "warning_level": row[9],
                "result": row[10]  # Include result for cache status
            }
            predictions.append(p)
            
        return predictions



def delete_predictions_for_date(date: str) -> int:
    """Elimina todas las predicciones de una fecha específica (para invalidar cache stale)"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("DELETE FROM predictions WHERE date = ? AND result = 'PENDING'", (date,))
        deleted = cursor.rowcount
        conn.commit()
    print(f"[DB] Deleted {deleted} stale predictions for {date}")
    return deleted


def get_team_recent_results(team_name: str, limit: int = 5) -> list:
    """Obtiene los últimos N resultados de un equipo"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT date, match_id, predicted_winner, result
            FROM predictions
            WHERE (home_team LIKE ? OR away_team LIKE ?)
            AND result != 'PENDING'
            ORDER BY date DESC
            LIMIT ?
        """, (f"%{team_name}%", f"%{team_name}%", limit))
        
        return [
            {
                "date": row[0],
                "match": row[1],
                "predicted_winner": row[2],
                "result": row[3]
            }
            for row in cursor.fetchall()
        ]


def get_upcoming_football_predictions() -> list[dict]:
    """Obtiene predicciones de fútbol pendientes para la próxima jornada (fecha >= actual)."""
    with sqlite3.connect(DB_PATH) as conn:
        # Retrieve matches that are from today onwards and pending
        cursor = conn.execute("""
            SELECT date, league, match_id, home_team, away_team, prediction,
                   prob_home, prob_draw, prob_away, result, created_at
            FROM football_predictions
            WHERE date >= date('now', 'localtime') AND result = 'PENDING'
            ORDER BY date ASC, created_at DESC
        """)
        
        rows = cursor.fetchall()
        
        return [
            {
                "date": row[0],
                "league": row[1],
                "match_id": row[2],
                "home_team": row[3],
                "away_team": row[4],
                "prediction": row[5],
                "probs": {
                    "home": row[6],
                    "draw": row[7],
                    "away": row[8]
                },
                "result": row[9],
                "created_at": row[10]
            }
            for row in rows
        ]


def update_prediction_odds(match_id: str, odds_home: float, odds_away: float) -> None:
    """Update odds for an existing prediction (used when odds were missing on initial save)."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE predictions SET odds_home = ?, odds_away = ?
            WHERE match_id = ? AND (odds_home IS NULL OR odds_away IS NULL)
        """, (odds_home, odds_away, match_id))
        conn.commit()


def get_all_prediction_dates() -> dict:
    """Returns {date_str: count} for all dates with predictions"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT date, COUNT(*) FROM predictions
            GROUP BY date ORDER BY date
        """)
        return {row[0]: row[1] for row in cursor.fetchall()}


def get_match_ids_for_date(date: str) -> set:
    """Returns set of match_id strings for a given date"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT match_id FROM predictions WHERE date = ?", (date,)
        )
        return {row[0] for row in cursor.fetchall()}


# =============================================
# MATCH NEWS (Groq Agent cache)
# =============================================

def save_match_news(date: str, match_id: str, news_data: dict) -> None:
    """Persists Groq agent news for a single match."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO match_news
            (date, match_id, sport, headline, key_points, injuries,
             impact_assessment, confidence_modifier, raw_response)
            VALUES (?, ?, 'nba', ?, ?, ?, ?, ?, ?)
        """, (
            date,
            match_id,
            news_data.get("headline", ""),
            json.dumps(news_data.get("key_points", []), ensure_ascii=False),
            json.dumps(news_data.get("injuries", []), ensure_ascii=False),
            news_data.get("impact_assessment", ""),
            news_data.get("confidence_modifier", "neutral"),
            json.dumps(news_data, ensure_ascii=False),
        ))
        conn.commit()


def get_match_news(match_id: str) -> Optional[dict]:
    """Returns cached news for a single match or None."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT headline, key_points, injuries, impact_assessment,
                   confidence_modifier, created_at
            FROM match_news WHERE match_id = ?
        """, (match_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "headline": row[0],
            "key_points": json.loads(row[1]) if row[1] else [],
            "injuries": json.loads(row[2]) if row[2] else [],
            "impact_assessment": row[3],
            "confidence_modifier": row[4],
            "created_at": row[5],
        }


def get_news_for_date(date: str) -> list[dict]:
    """Returns all cached news for a given date."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT match_id, headline, key_points, injuries,
                   impact_assessment, confidence_modifier, created_at
            FROM match_news WHERE date = ?
        """, (date,))
        return [
            {
                "match_id": r[0],
                "headline": r[1],
                "key_points": json.loads(r[2]) if r[2] else [],
                "injuries": json.loads(r[3]) if r[3] else [],
                "impact_assessment": r[4],
                "confidence_modifier": r[5],
                "created_at": r[6],
            }
            for r in cursor.fetchall()
        ]


def news_exist_for_date(date: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT COUNT(*) FROM match_news WHERE date = ?", (date,)
        )
        return cursor.fetchone()[0] > 0


# =============================================
# DAILY RECOMMENDATIONS
# =============================================

def save_daily_recommendations(date: str, reco_data: dict) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO daily_recommendations
            (date, sport, recommendations, parlay_analysis, parlay_odds, reasoning, result)
            VALUES (?, 'nba', ?, ?, ?, ?, 'pending')
        """, (
            date,
            json.dumps(reco_data.get("recommendations", []), ensure_ascii=False),
            reco_data.get("parlay_analysis", ""),
            reco_data.get("parlay_odds", 0.0),
            reco_data.get("reasoning", ""),
        ))
        conn.commit()


def get_daily_recommendations(date: str) -> Optional[dict]:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT recommendations, parlay_analysis, parlay_odds, created_at,
                   reasoning, result
            FROM daily_recommendations WHERE date = ?
        """, (date,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "recommendations": json.loads(row[0]) if row[0] else [],
            "parlay_analysis": row[1],
            "parlay_odds": row[2],
            "created_at": row[3],
            "reasoning": row[4] or "",
            "result": row[5] or "pending",
        }


def get_recommendations_history(limit: int = 14) -> list[dict]:
    """Returns past daily recommendations with their results."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT date, recommendations, parlay_analysis, parlay_odds,
                   created_at, result
            FROM daily_recommendations
            ORDER BY date DESC LIMIT ?
        """, (limit,))
        return [
            {
                "date": r[0],
                "recommendations": json.loads(r[1]) if r[1] else [],
                "parlay_analysis": r[2],
                "parlay_odds": r[3],
                "created_at": r[4],
                "result": r[5] or "pending",
            }
            for r in cursor.fetchall()
        ]


def delete_daily_recommendations(date: str) -> None:
    """Remove stale recommendations for a date so they can be regenerated."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM daily_recommendations WHERE date = ?", (date,))
        conn.commit()


def update_recommendation_result(date: str, result: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE daily_recommendations SET result = ? WHERE date = ?",
            (result, date)
        )
        conn.commit()
