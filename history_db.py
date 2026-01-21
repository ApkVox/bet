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
    print("✅ history.db inicializada")


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


def get_performance_stats(days: int = 30) -> dict:
    """Obtiene estadísticas de rendimiento"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT 
                COUNT(*) as total_bets,
                SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(profit) as total_profit,
                AVG(CASE WHEN result != 'PENDING' THEN profit END) as avg_profit
            FROM predictions
            WHERE date >= date('now', '-' || ? || ' days')
            AND result != 'PENDING'
        """, (days,))
        
        row = cursor.fetchone()
        total, wins, total_profit, avg_profit = row
        
        return {
            "total_bets": total or 0,
            "wins": wins or 0,
            "win_rate": round((wins / total * 100) if total > 0 else 0, 1),
            "total_profit": round(total_profit or 0, 2),
            "avg_profit": round(avg_profit or 0, 2),
            "roi": round((total_profit / total * 100) if total > 0 else 0, 1)
        }


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
