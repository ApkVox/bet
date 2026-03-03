#!/usr/bin/env python3
"""
Verifica la base de datos de historial: lista fechas con predicciones PENDIENTES
anteriores al 03/03/2026 y opcionalmente las actualiza (WIN/LOSS).
Uso:
  python scripts/verify_history_db.py           # solo listar pendientes
  python scripts/verify_history_db.py --fix     # listar y ejecutar actualización
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3
from history_db import DB_PATH

CUTOFF_DATE = "2026-03-03"


def main():
    fix = "--fix" in sys.argv
    if not DB_PATH.exists():
        print(f"No existe la base de datos en {DB_PATH}")
        return 1

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT date, COUNT(*) as cnt
            FROM predictions
            WHERE result = 'PENDING' AND date < ?
            GROUP BY date
            ORDER BY date
        """, (CUTOFF_DATE,))
        rows = cursor.fetchall()

    if not rows:
        print(f"OK: No hay predicciones pendientes con fecha anterior a {CUTOFF_DATE}.")
        return 0

    print(f"Fechas con predicciones PENDIENTES antes de {CUTOFF_DATE}:")
    for date_str, count in rows:
        print(f"  {date_str}: {count} partidos pendientes")

    if fix:
        print("\nEjecutando actualización de marcadores (history_service)...")
        try:
            from src.Services.history_service import update_pending_predictions
            result = update_pending_predictions()
            print(f"Resultado: {result.get('updated_count', 0)} partidos actualizados.")
        except Exception as e:
            print(f"Error al actualizar: {e}")
            return 1
    else:
        print("\nPara actualizar pendientes, ejecuta: python scripts/verify_history_db.py --fix")

    return 0


if __name__ == "__main__":
    sys.exit(main())
