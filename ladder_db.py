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
