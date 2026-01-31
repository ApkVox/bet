import sqlite3
from pathlib import Path

BASE_DIR = Path("c:/Users/hasle/OneDrive/Documentos/Apps/bet")
DB_PATH = BASE_DIR / "Data" / "history.db"

def check_history():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    print(f"Checking database at {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check count of predictions by date
        print("\nPredictions count by date:")
        cursor.execute("SELECT date, count(*) FROM predictions GROUP BY date ORDER BY date DESC")
        rows = cursor.fetchall()
        for row in rows:
            print(f"{row[0]}: {row[1]} predictions")
            
        print("\nChecking specifically for 2026-01-30:")
        cursor.execute("SELECT * FROM predictions WHERE date = '2026-01-30'")
        rows_30 = cursor.fetchall()
        if not rows_30:
            print("No entries found for 2026-01-30")
        else:
            print(f"Found {len(rows_30)} entries for 2026-01-30")
            
        conn.close()
    except Exception as e:
        print(f"Error accessing database: {e}")

if __name__ == "__main__":
    check_history()
