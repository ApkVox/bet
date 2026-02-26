import sys
import os
import asyncio
from datetime import datetime, timedelta, date

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prediction_api import predict_games
from history_db import save_historical_prediction, update_results, get_predictions_by_date
import sbrscrape

def get_date_range(start_date, end_date):
    for n in range(int((end_date - start_date).days) + 1):
        yield start_date + timedelta(n)

async def backfill():
    start_date = date(2026, 2, 13)
    end_date = date(2026, 2, 26)

    print(f"🔄 Iniciando Backfill desde {start_date} hasta {end_date}")

    for single_date in get_date_range(start_date, end_date):
        date_str = single_date.strftime("%Y-%m-%d")
        print(f"\\n--- Procesando fecha {date_str} ---")
        
        # Omitir si ya existen
        existing = get_predictions_by_date(date_str)
        if existing and len(existing) > 0:
             print(f"Saltando {date_str}, ya tiene {len(existing)} predicciones guardadas.")
             
             # Pero vamos a intentar buscar si se pueden resolver los PENDING
             board = sbrscrape.Scoreboard(sport="NBA", date=date_str)
             results = {}
             for g in board.games:
                 if g.get('home_score') and g.get('away_score'):
                     home_score = int(g['home_score'])
                     away_score = int(g['away_score'])
                     winner = g['home_team'] if home_score > away_score else g['away_team']
                     home = g['home_team'].replace("Los Angeles Clippers", "LA Clippers")
                     away = g['away_team'].replace("Los Angeles Clippers", "LA Clippers")
                     results[f"{away} vs {home}"] = winner
             if results:
                 update_results(date_str, results)
                 print(f"Resultados actualizados para {date_str}: {len(results)} partidos.")
             continue

        board = sbrscrape.Scoreboard(sport="NBA", date=date_str)
        games = getattr(board, 'games', [])
        
        if not games:
            print(f"Sin partidos el {date_str}")
            continue
            
        print(f"Encontrados {len(games)} juegos. Extrayendo características punto-en-el-tiempo...")
        
        games_to_predict = []
        for g in games:
            away = g['away_team'].replace("Los Angeles Clippers", "LA Clippers")
            home = g['home_team'].replace("Los Angeles Clippers", "LA Clippers")
            games_to_predict.append({
                "home_team": home,
                "away_team": away,
                "ou_line": g.get("total", 220.0),
                "home_odds": g.get("home_odds", None),
                "away_odds": g.get("away_odds", None),
                "game_date": single_date
            })
            
        try:
            predictions = predict_games(games_to_predict, default_game_date=single_date)
            
            # Save them
            for pred in predictions:
                pred_dict = pred if isinstance(pred, dict) else pred.dict()
                pred_dict['date'] = date_str
                save_historical_prediction(pred_dict)
                
            print(f"✅ Guardadas {len(predictions)} predicciones NBA para {date_str}")
            
            # Update results immediately using SBR score data
            results = {}
            for g in games:
                 if g.get('home_score') and g.get('away_score'):
                     home_score = int(g['home_score'])
                     away_score = int(g['away_score'])
                     winner = g['home_team'] if home_score > away_score else g['away_team']
                     home = g['home_team'].replace("Los Angeles Clippers", "LA Clippers")
                     away = g['away_team'].replace("Los Angeles Clippers", "LA Clippers")
                     results[f"{away} vs {home}"] = winner
                     
            if results:
                update_results(date_str, results)
                print(f"🏆 Resueltos {len(results)} partidos en Win/Loss para {date_str}")

        except Exception as e:
            print(f"❌ Error modelando {date_str}: {e}")

if __name__ == "__main__":
    asyncio.run(backfill())
