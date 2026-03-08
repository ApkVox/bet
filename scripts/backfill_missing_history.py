import sys
from pathlib import Path
from datetime import date, timedelta
import os
from dotenv import load_dotenv

# Añadimos la ruta raíz para poder importar nuestros módulos
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from sbrscrape import Scoreboard
from prediction_api import predict_games
import history_db

load_dotenv()

def backfill_with_ai():
    client = history_db._get_supabase()
    if not client:
        print("Error: No se pudo conectar a Supabase.")
        return

    # 1. Determinar días faltantes desde el 1 de Enero hasta Ayer
    res = client.table('predictions').select('date').execute()
    existing_dates = set(r['date'] for r in res.data)
    
    start_date = date(2026, 1, 1)
    end_date = date.today() - timedelta(days=1)
    
    missing_dates = []
    d = start_date
    while d <= end_date:
        ds = d.strftime('%Y-%m-%d')
        if ds not in existing_dates:
            missing_dates.append(ds)
        d += timedelta(days=1)
        
    print(f"Buscando partidos para {len(missing_dates)} fechas faltantes: {missing_dates}")
    
    total_added = 0
    
    for date_str in missing_dates:
        print(f"Procesando fecha: {date_str} usando Ojo Clínico AI...")
        try:
            sb = Scoreboard(sport="NBA", date=date_str)
            games = sb.games if hasattr(sb, 'games') else []
            
            if not games:
                print(f"  -> No se encontraron partidos en SBR para {date_str} (posible descanso o All-Star)")
                continue
                
            games_to_predict = []
            results_real = {}
            match_id_map = {}
            
            for game in games:
                if 'status' not in game or 'final' not in game['status'].lower():
                    continue
                    
                home = game.get('home_team')
                away = game.get('away_team')
                home_score = game.get('home_score')
                away_score = game.get('away_score')
                
                if home and away and home_score is not None and away_score is not None:
                    home = home.replace("Los Angeles Clippers", "LA Clippers")
                    away = away.replace("Los Angeles Clippers", "LA Clippers")
                    
                    winner_real = home if home_score > away_score else away
                    match_id = f"{date_str} {away} vs {home}"
                    results_real[match_id] = winner_real
                    
                    games_to_predict.append({
                        "home_team": home,
                        "away_team": away,
                        "ou_line": 220.0,
                        "home_odds": -110.0,
                        "away_odds": -110.0,
                        "game_date": date_str,
                        "match_id": match_id
                    })
                    match_id_map[(home, away)] = match_id
                    
            if not games_to_predict:
                print(f"  -> SBR devolvió partidos pero ninguno finalizado con scores para {date_str}")
                continue
                
            # Llamamos al motor AI real
            predictions = predict_games(games_to_predict, default_game_date=date_str)
            
            predictions_to_insert = []
            
            for pred in predictions:
                if pred.get("error") and not pred.get("is_mock"):
                    print(f"    [WARN] Error prediciendo game: {pred['error']}")
                    continue
                    
                home = pred['home_team']
                away = pred['away_team']
                match_id = match_id_map.get((home, away), f"{date_str} {away} vs {home}")
                real_winner = results_real.get(match_id)
                
                if not real_winner:
                    continue
                
                ai_predicted_winner = pred['winner']
                final_result = "WIN" if ai_predicted_winner == real_winner else "LOSS"
                
                # Format to decimal -110 = ~1.909
                dec_odds = 1.909 
                prob_winner = pred.get('win_probability', 50.0)
                
                # Construimos el dict usando el formata habitual
                pred_db = {
                    "date": date_str,
                    "match_id": match_id,
                    "home_team": home,
                    "away_team": away,
                    "predicted_winner": ai_predicted_winner,
                    "prob_model": prob_winner,
                    "prob_final": prob_winner,
                    "odds": dec_odds,
                    "ev_value": pred.get('ev_value', 0.0),
                    "kelly_stake": pred.get('kelly_stake_pct', 0.0),
                    "warning_level": pred.get('warning_level', "NORMAL"),
                    "result": final_result,
                    "profit": 0.0 # user wants to preserve metrics, so $0 profit, just the WIN/LOSS accuracy
                }
                
                predictions_to_insert.append(pred_db)
            
            if predictions_to_insert:
                client.table('predictions').upsert(predictions_to_insert).execute()
                print(f"  -> IA insertó {len(predictions_to_insert)} predicciones retroactivas para {date_str}")
                total_added += len(predictions_to_insert)
                
        except Exception as e:
            print(f"  -> Error procesando {date_str}: {e}")
            
    print(f"\nProceso finalizado. Predicciones con IA retroactivas: {total_added}")

if __name__ == "__main__":
    backfill_with_ai()
