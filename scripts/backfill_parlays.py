import os
import sys
import asyncio
from datetime import date, timedelta
from dotenv import load_dotenv

sys.path.append('.')
load_dotenv()

import history_db
from news_agent import fetch_news_for_matches
from recommendations import generate_recommendations
import sbrscrape

async def backfill_parlays():
    print("Iniciando backfill de combinadas (7 dias)...")
    
    # Check existing recommendations
    client = history_db._get_supabase()
    res = client.table('daily_recommendations').select('date').execute()
    existing_dates = set(r['date'] for r in res.data)
    print(f"Combinadas existentes en DB: {len(existing_dates)} fechas -> {sorted(list(existing_dates))}")
    
    end_date = date.today() - timedelta(days=1)
    # 7 dias contando desde hoy para atrás
    start_date = date.today() - timedelta(days=7)
    
    d = start_date
    dates_to_process = []
    while d <= end_date:
        ds = d.strftime('%Y-%m-%d')
        if ds not in existing_dates:
            dates_to_process.append(ds)
        d += timedelta(days=1)
        
    print(f"Fechas a procesar (sin combinada): {dates_to_process}")
    
    for ds in dates_to_process:
        print(f"\n--- Procesando fecha para combinada: {ds} ---")
        preds = history_db.get_predictions_by_date_light(ds)
        
        if not preds:
            print(f"  -> No hay predicciones en DB para {ds}. No se puede generar combinada.")
            # Create an empty record so it won't retry forever
            history_db.save_daily_recommendations(ds, {
                "recommendations": [],
                "parlay_analysis": "No hubo análisis ni partidos NBA disponibles ese día.",
                "parlay_odds": 0.0,
                "reasoning": "Vacío por calendario",
                "result": "pending"
            })
            continue
            
        print(f"  -> Hay {len(preds)} predicciones en DB. Consultando noticias...")
        news = await fetch_news_for_matches(ds, preds)
        
        print("  -> Generando recomendaciones vía DeepSeek...")
        try:
            res_reco = await generate_recommendations(ds)
            print(f"  -> DeepSeek devolvió {len(res_reco.get('recommendations', []))} picks")
            
            # Now determine if this parlay won/lost based on REAL scores!
            print("  -> Verificando resultado real del Parlay...")
            sb = sbrscrape.Scoreboard(sport="NBA", date=ds)
            games = sb.games if hasattr(sb, 'games') else []
            
            results = {}
            for g in games:
                if 'status' not in g or 'final' not in g['status'].lower():
                    continue
                home = g.get('home_team')
                away = g.get('away_team')
                hs = g.get('home_score')
                ats = g.get('away_score')
                if home and away and hs is not None and ats is not None:
                    home = home.replace("Los Angeles Clippers", "LA Clippers")
                    away = away.replace("Los Angeles Clippers", "LA Clippers")
                    winner = home if hs > ats else away
                    match_id = f"{ds}_{away}_{home}".replace(" ", "_")
                    # Soporte secundario por si SBR tiene otro match_id (espacios vs guiones_bajos)
                    match_id_alt = f"{ds} {away} vs {home}"
                    results[match_id] = winner
                    results[match_id_alt] = winner
            
            from generate_daily_job import _update_parlay_result
            _update_parlay_result(ds, results)
            
        except Exception as e:
            print(f"  -> ERROR en recomendación: {e}")

if __name__ == "__main__":
    asyncio.run(backfill_parlays())
