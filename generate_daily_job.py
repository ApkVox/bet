# 🚀 Motor de ML Independiente (generate_daily_job.py)

import os
import sys
import asyncio
from datetime import datetime
import json

# Forzamos entorno para los imports relativos locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prediction_api import predict_games, _models_cache
from football_api import football_api
from history_db import save_prediction, save_football_prediction, get_predictions_by_date
import sbrscrape

# Logging helper
def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [JOB] {msg}")

# ==========================================
# SCRAPING & NBA PREDICTIONS
# ==========================================
async def generate_nba_predictions():
    log("Iniciando scrapping de SBR para juegos NBA de hoy...")
    try:
        scraper = sbrscrape.Scoreboard(sport="NBA")
        games = scraper.games
        
        if not games:
            log("No hay juegos actuales (posiblemente fuera de temporada o sandbox). Usando fecha de prueba 2024-02-27.")
            scraper = sbrscrape.Scoreboard(sport="NBA", date="2024-02-27")
            games = scraper.games

        if not games:
            log("No hay juegos NBA programados para hoy.")
            return

        today_str = datetime.now().strftime("%Y-%m-%d")
        existing = get_predictions_by_date(today_str)
        if existing and len(existing) >= len(games):
            log(f"Predicciones NBA para hoy ({len(existing)}) ya existen en BD. Omitiendo.")
            # Para refrecar cuotas de partidos no empezados podríamos actualizar, 
            # pero por ahora para el Actions 1 vez al día, la creación basta.
            return

        log(f"Encontrados {len(games)} juegos. Generando predicciones XGBoost + Groq...")
        
        def get_single_odd(odds_data):
            if isinstance(odds_data, dict) and odds_data:
                return float(odds_data.get('bet365', list(odds_data.values())[0]))
            return float(odds_data) if odds_data else None

        # Adapt format for predict_games
        games_to_predict = []
        for g in games:
            away = g['away_team'].replace("Los Angeles Clippers", "LA Clippers")
            home = g['home_team'].replace("Los Angeles Clippers", "LA Clippers")
            games_to_predict.append({
                "home_team": home,
                "away_team": away,
                "ou_line": get_single_odd(g.get("total", 220.0)),
                "home_odds": get_single_odd(g.get("home_odds")),
                "away_odds": get_single_odd(g.get("away_odds")),
                "game_date": today_str
            })

        predictions = predict_games(games_to_predict)
        
        saved_count = 0
        for pred in predictions:
            pred_dict = pred if isinstance(pred, dict) else pred.dict()
            pred_dict['date'] = today_str
            pred_dict['match_id'] = f"{today_str}_{pred_dict['away_team']}_{pred_dict['home_team']}".replace(" ", "_")
            
            # Map API fields to DB fields
            pred_dict['market_odds'] = pred_dict.get('home_odds', 0) if pred_dict['winner'] == pred_dict['home_team'] else pred_dict.get('away_odds', 0)
            pred_dict['ev_value'] = pred_dict.get('ev_value', 0.0)
            pred_dict['kelly_stake_pct'] = pred_dict.get('kelly_stake_pct', 0.0)
            pred_dict['warning_level'] = pred_dict.get('warning_level', 'NORMAL')
            
            save_prediction(pred_dict)
            saved_count += 1
            log(f"✅ Guardado NBA: {pred_dict['away_team']} @ {pred_dict['home_team']}")

        log(f"Completado NBA: Guardadas {saved_count} predicciones.")

    except Exception as e:
        import traceback
        log(f"❌ Error crítico en NBA Job: {traceback.format_exc()}")


# ==========================================
# FOOTBALL PREDICTIONS (POISSON)
# ==========================================
async def generate_football_predictions():
    log("Iniciando modelo Poisson para Fútbol (European Leagues)...")
    try:
        football_api.ensure_initialized()
        preds = football_api.get_all_predictions()
        
        if not preds:
            log("No se encontraron fixtures de fútbol próximos (3 días).")
            return

        saved_count = 0
        for p in preds:
            save_football_prediction(p, p["match_id"], p["date"])
            saved_count += 1
            
        log(f"Completado Fútbol: Guardadas {saved_count} predicciones.")

    except Exception as e:
        log(f"❌ Error crítico en Football Job: {str(e)}")


# ==========================================
# RESULT UPDATER (WIN / LOSS)
# ==========================================
async def update_past_results():
    log("Actualizando resultados finalizados de los últimos 3 días...")
    from history_db import update_results
    import sbrscrape
    from datetime import date, timedelta
    
    today = date.today()
    for n in range(1, 4): # Revisa ayer, antier, tras-antier
        past_date = today - timedelta(days=n)
        date_str = past_date.strftime("%Y-%m-%d")
        
        try:
            board = sbrscrape.Scoreboard(sport="NBA", date=date_str)
            games = getattr(board, 'games', [])
            if not games:
                continue
            
            results = {}
            for g in games:
                 if g.get('home_score') and g.get('away_score'):
                     home_score = int(g['home_score'])
                     away_score = int(g['away_score'])
                     winner = g['home_team'] if home_score > away_score else g['away_team']
                     home = g['home_team'].replace("Los Angeles Clippers", "LA Clippers")
                     away = g['away_team'].replace("Los Angeles Clippers", "LA Clippers")
                     match_id = f"{date_str}_{away}_{home}".replace(" ", "_")
                     results[match_id] = winner
                     
            if results:
                update_results(date_str, results)
                log(f"🏆 Resultados actualizados para {date_str}: {len(results)} partidos resolvidos")
        except Exception as e:
            log(f"❌ Error actualizando resultados {date_str}: {e}")

# ==========================================
# MAIN ENTRYPOINT (GITHUB ACTIONS)
# ==========================================
async def run_all():
    log("=== LA FIJA: DAILY PREDICTION JOB STARTED ===")
    
    # 0. Actualizar resultados pendientes (Win/Loss)
    await update_past_results()
    
    # 1. Ejecutar análisis NBA
    await generate_nba_predictions()
    
    # 2. Ejecutar análisis Fútbol
    await generate_football_predictions()
    
    log("=== LA FIJA: DAILY PREDICTION JOB FINISHED ===")

if __name__ == "__main__":
    asyncio.run(run_all())
