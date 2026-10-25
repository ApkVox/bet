import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to allow importing modules from root
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

import history_db


def update_pending_predictions():
    """
    Califica las predicciones PENDING con los marcadores de nba_games (los guarda el job diario).
    No consulta sbrscrape: para días pasados devuelve el marcador de otro partido entre los mismos
    equipos (ver generate_daily_job.update_past_results).
    """
    print("[History Service] Checking for pending predictions...")

    pending_dates = set()
    client = history_db._get_supabase()
    if client:
        try:
            today_str = datetime.now().strftime('%Y-%m-%d')
            res = client.table('predictions').select('date').eq('result', 'PENDING').lte('date', today_str).execute()
            pending_dates = {row['date'] for row in res.data}
        except Exception as e:
            print(f"[History Service DB Error] {e}")

    print(f"[History Service] Found pending predictions for dates: {sorted(pending_dates)}")

    updated_count = 0
    if pending_dates:
        for date_str, results in history_db.game_winners(history_db.get_game_results(), pending_dates).items():
            history_db.update_results(date_str, results)
            updated_count += len(results)

    history_db.settle_parlays()
    print(f"[History Service] Update complete. Updated {updated_count} matches.")
    return {"status": "success", "updated_count": updated_count}
