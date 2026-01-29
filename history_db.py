import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "Data" / "history.db"

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
        conn.commit()
    print("[OK] history.db inicializada")


def save_prediction(prediction_data: dict):
    """Guarda una predicción"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT OR REPLACE INTO predictions 
            (date, match_id, home_team, away_team, predicted_winner, 
             prob_model, prob_final, odds, ev_value, kelly_stake, warning_level, result)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING')
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
            prediction_data['warning_level']
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
            # Obtener kelly_stake y odds para calcular profit
            cursor = conn.execute("""
                SELECT kelly_stake, odds, predicted_winner
                FROM predictions
                WHERE date = ? AND match_id = ?
            """, (date, match_id))
            
            row = cursor.fetchone()
            if not row:
                continue
            
            kelly_stake, odds, predicted_winner = row
            is_win = (predicted_winner == actual_winner)
            
            # Calcular profit
            if is_win:
                # Ganancia = stake × (odds / 100)
                profit = kelly_stake * (abs(odds) / 100) if odds else 0
            else:
                # Pérdida = -stake
                profit = -kelly_stake
            
            # Actualizar
            conn.execute("""
                UPDATE predictions
                SET result = ?,
                    profit = ?
                WHERE date = ? AND match_id = ?
            """, ('WIN' if is_win else 'LOSS', profit, date, match_id))
        
        conn.commit()




def get_history(days: int = 7) -> list[dict]:
    """Obtiene historial de predicciones"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT date, match_id, predicted_winner, prob_final, odds, 
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
                "predicted_winner": row[2],
                "probability": row[3],
                "odds": row[4],
                "ev": row[5],
                "kelly_stake": row[6],
                "result": row[7],
                "profit": row[8]
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
                # 'result': row[10] # Not used in MatchPrediction but useful for status
            }
            predictions.append(p)
            
        return predictions



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
