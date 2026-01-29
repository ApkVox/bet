import sqlite3
import json
from datetime import datetime

DB_NAME = "ladder.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla de Estado
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ladder_state (
            id INTEGER PRIMARY KEY,
            current_capital REAL NOT NULL,
            step_number INTEGER NOT NULL,
            last_update_date TEXT
        )
    ''')
    
    # Tabla de Historial
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ladder_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            bet_details TEXT NOT NULL, -- JSON
            outcome TEXT, -- 'WIN' or 'LOSS'
            learning_note TEXT
        )
    ''')
    
    # Tabla de Tickets Generados
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS generated_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            ticket_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabla de Predicciones Diarias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            predictions_json TEXT NOT NULL, -- Lista de predicciones completa
            summary_stats TEXT, -- JSON con stats del día (winrate, profit, etc)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date)
        )
    ''')
    
    # Inicializar si está vacío
    cursor.execute('SELECT count(*) FROM ladder_state')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO ladder_state (id, current_capital, step_number, last_update_date) VALUES (1, 10000, 1, ?)', (datetime.now().strftime("%Y-%m-%d"),))
    
    conn.commit()
    conn.close()

def get_state():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM ladder_state WHERE id = 1')
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_state(new_capital, new_step):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE ladder_state 
        SET current_capital = ?, step_number = ?, last_update_date = ? 
        WHERE id = 1
    ''', (new_capital, new_step, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    conn.close()

def add_history(bet_details_json, outcome, learning_note):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ladder_history (date, bet_details, outcome, learning_note)
        VALUES (?, ?, ?, ?)
    ''', (datetime.now().strftime("%Y-%m-%d"), bet_details_json, outcome, learning_note))
    conn.commit()
    conn.close()

def get_bad_beats(limit=5):
    """Retorna los últimos errores (LOSS) para aprender"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT learning_note FROM ladder_history 
        WHERE outcome = 'LOSS' 
        ORDER BY id DESC LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [row['learning_note'] for row in rows]

def save_generated_ticket(ticket_data, date=None):
    """Guarda un ticket generado"""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
        
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO generated_tickets (date, ticket_json)
        VALUES (?, ?)
    ''', (date, json.dumps(ticket_data)))
    conn.commit()
    conn.close()

def get_generated_tickets(limit=20, date=None):
    """Obtiene historial de tickets generados"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if date:
        cursor.execute('''
            SELECT * FROM generated_tickets 
            WHERE date = ?
            ORDER BY created_at DESC
        ''', (date,))
    else:
        cursor.execute('''
            SELECT * FROM generated_tickets 
            ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        
    rows = cursor.fetchall()
    conn.close()
    
    tickets = []
    for row in rows:
        try:
            tickets.append({
                "id": row["id"],
                "date": row["date"],
                "ticket": json.loads(row["ticket_json"]),
                "created_at": row["created_at"]
            })
        except:
            continue
    return tickets

# ==========================================
# NUEVAS FUNCIONES PARA HISTORIAL DE PREDICCIONES
# ==========================================
def save_daily_predictions(date_str, predictions_list, stats=None):
    """Guarda o actualiza las predicciones de un día"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    preds_json = json.dumps(predictions_list)
    stats_json = json.dumps(stats) if stats else "{}"
    
    cursor.execute('''
        INSERT OR REPLACE INTO daily_predictions (date, predictions_json, summary_stats)
        VALUES (?, ?, ?)
    ''', (date_str, preds_json, stats_json))
    
    conn.commit()
    conn.close()

def get_predictions_by_date(date_str):
    """Recupera predicciones de una fecha específica"""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM daily_predictions WHERE date = ?', (date_str,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "date": row["date"],
            "predictions": json.loads(row["predictions_json"]),
            "stats": json.loads(row["summary_stats"]) if row["summary_stats"] else {}
        }
    return None

def get_available_dates():
    """Devuelve lista de fechas con data disponible"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT date FROM daily_predictions ORDER BY date DESC')
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]
