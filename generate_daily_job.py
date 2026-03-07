# 🚀 Motor de ML Independiente (generate_daily_job.py)

import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
import json

# Cargar .env para uso local
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TZ_COLOMBIA = timezone(timedelta(hours=-5))

# Forzamos entorno para los imports relativos locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from prediction_api import predict_games, _models_cache
from football_api import football_api
import history_db
from history_db import save_prediction, save_football_prediction, get_predictions_by_date
import sbrscrape

# Logging helper
def log(msg: str):
    timestamp = datetime.now(TZ_COLOMBIA).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [JOB] {msg}")

# ==========================================
# ODDS UTILITIES
# ==========================================
def get_single_odd(odds_data):
    if isinstance(odds_data, dict) and odds_data:
        return float(odds_data.get('bet365', list(odds_data.values())[0]))
    return float(odds_data) if odds_data else None


def american_to_decimal(american_odds):
    """Convert American odds (-150, +200) to decimal (1.67, 3.00)."""
    if american_odds is None:
        return None
    try:
        odds = float(american_odds)
    except (ValueError, TypeError):
        return None
    if odds == 0:
        return None
    if odds > 0:
        return round(1 + (odds / 100), 3)
    else:
        return round(1 + (100 / abs(odds)), 3)


def _refresh_odds_for_existing(games: list, today_str: str):
    """Update odds on existing predictions that have NULL odds."""
    updated = 0
    for g in games:
        home = g['home_team'].replace("Los Angeles Clippers", "LA Clippers")
        away = g['away_team'].replace("Los Angeles Clippers", "LA Clippers")
        match_id = f"{today_str}_{away}_{home}".replace(" ", "_")
        home_ml = get_single_odd(g.get("home_ml"))
        away_ml = get_single_odd(g.get("away_ml"))
        home_dec = american_to_decimal(home_ml)
        away_dec = american_to_decimal(away_ml)
        if home_dec and away_dec:
            history_db.update_prediction_odds(match_id, home_dec, away_dec)
            updated += 1
    if updated:
        log(f"Cuotas actualizadas para {updated} partidos existentes.")


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

        today_str = datetime.now(TZ_COLOMBIA).strftime("%Y-%m-%d")
        existing = get_predictions_by_date(today_str)
        if existing and len(existing) >= len(games):
            log(f"Predicciones NBA para hoy ({len(existing)}) ya existen en BD. Actualizando cuotas si faltan...")
            _refresh_odds_for_existing(games, today_str)
            return existing

        log(f"Encontrados {len(games)} juegos. Generando predicciones XGBoost + Groq...")

        # Adapt format for predict_games
        # sbrscrape uses 'home_ml' / 'away_ml' for moneyline odds (American format)
        games_to_predict = []
        for g in games:
            away = g['away_team'].replace("Los Angeles Clippers", "LA Clippers")
            home = g['home_team'].replace("Los Angeles Clippers", "LA Clippers")
            home_ml = get_single_odd(g.get("home_ml"))
            away_ml = get_single_odd(g.get("away_ml"))
            games_to_predict.append({
                "home_team": home,
                "away_team": away,
                "ou_line": get_single_odd(g.get("total", 220.0)),
                "home_odds": home_ml,
                "away_odds": away_ml,
                "game_date": today_str
            })
            log(f"  {away} @ {home} | ML: {home_ml} / {away_ml} | Decimal: {american_to_decimal(home_ml)} / {american_to_decimal(away_ml)}")

        predictions = predict_games(games_to_predict)
        
        saved_count = 0
        final_preds = []
        for pred, game_input in zip(predictions, games_to_predict):
            pred_dict = pred if isinstance(pred, dict) else pred.dict()
            pred_dict['date'] = today_str
            pred_dict['match_id'] = f"{today_str}_{pred_dict['away_team']}_{pred_dict['home_team']}".replace(" ", "_")
            
            raw_home = game_input.get('home_odds')
            raw_away = game_input.get('away_odds')
            pred_dict['home_odds'] = american_to_decimal(raw_home)
            pred_dict['away_odds'] = american_to_decimal(raw_away)
            pred_dict['market_odds'] = raw_home if pred_dict['winner'] == pred_dict['home_team'] else raw_away
            pred_dict['ev_value'] = pred_dict.get('ev_value', 0.0)
            pred_dict['kelly_stake_pct'] = pred_dict.get('kelly_stake_pct', 0.0)
            pred_dict['warning_level'] = pred_dict.get('warning_level', 'NORMAL')
            
            save_prediction(pred_dict)
            saved_count += 1
            final_preds.append(pred_dict)
            log(f"Guardado NBA: {pred_dict['away_team']} @ {pred_dict['home_team']}")

        log(f"Completado NBA: Guardadas {saved_count} predicciones.")
        return final_preds

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
        return preds

    except Exception as e:
        log(f"❌ Error crítico en Football Job: {str(e)}")
        return []


def _update_parlay_result(date_str: str, results: dict):
    """Check if the parlay for a given date was won or lost."""
    try:
        reco = history_db.get_daily_recommendations(date_str)
        if not reco or reco.get("result") not in (None, "pending", ""):
            return
        picks = reco.get("recommendations", [])
        if not picks:
            return
        all_correct = True
        for pick in picks:
            mid = pick.get("match_id", "")
            chosen = pick.get("pick", "")
            actual_winner = results.get(mid)
            if actual_winner is None:
                return
            if actual_winner != chosen:
                all_correct = False
                break
        result = "win" if all_correct else "loss"
        history_db.update_recommendation_result(date_str, result)
        log(f"Combinada {date_str}: {result.upper()}")
    except Exception as e:
        log(f"Error actualizando resultado combinada {date_str}: {e}")


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
                log(f"Resultados actualizados para {date_str}: {len(results)} partidos resolvidos")
                _update_parlay_result(date_str, results)
        except Exception as e:
            log(f"Error actualizando resultados {date_str}: {e}")

# ==========================================
# MAIN ENTRYPOINT (GITHUB ACTIONS)
# ==========================================
async def run_news_and_recommendations():
    """Fetch DeepSeek news for today's NBA matches and generate recommendations."""
    today_str = datetime.now(TZ_COLOMBIA).strftime("%Y-%m-%d")
    try:
        preds = history_db.get_predictions_by_date_light(today_str)
        if not preds:
            log("No hay predicciones NBA para hoy, saltando noticias/recomendaciones.")
            return

        from news_agent import fetch_news_for_matches
        await fetch_news_for_matches(today_str, preds)
        log("Noticias NBA generadas y cacheadas.")

        from recommendations import generate_recommendations
        await generate_recommendations(today_str)
        log("Recomendaciones NBA generadas y cacheadas.")
    except Exception as e:
        log(f"Error en noticias/recomendaciones (no critico): {e}")


async def run_all():
    log("=== LA FIJA: DAILY PREDICTION JOB STARTED ===")
    
    # 0. Actualizar resultados pendientes (Win/Loss)
    await update_past_results()
    
    # 1. Ejecutar análisis NBA
    await generate_nba_predictions()
    
    # 2. Ejecutar análisis Fútbol
    await generate_football_predictions()

    # 3. Noticias NBA + Recomendaciones (DeepSeek)
    await run_news_and_recommendations()
    
    log("=== LA FIJA: DAILY PREDICTION JOB FINISHED ===")

if __name__ == "__main__":
    asyncio.run(run_all())
