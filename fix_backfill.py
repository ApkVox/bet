"""
Script de backfill REAL usando XGBoost model.
Corre prediction_api.predict_games() para cada fecha faltante.
"""
import sys, os, gc
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sqlite3
from datetime import date, timedelta
from pathlib import Path
import sbrscrape

DB_PATH = Path(__file__).parent / "Data" / "history.db"

# Importar el modelo real
from prediction_api import predict_games, load_models, get_model_accuracy
from history_db import save_prediction, update_results, get_predictions_by_date

def get_sbr_games(date_str):
    try:
        board = sbrscrape.Scoreboard(sport="NBA", date=date_str)
        games = getattr(board, 'games', None)
        return games if games else []
    except Exception as e:
        print(f"  ⚠️ SBR error: {e}")
        return []

def main():
    print("🧠 BACKFILL CON MODELO XGBOOST REAL")
    print("=" * 50)
    
    # Cargar modelo
    print("📦 Cargando modelos XGBoost...")
    load_models()
    accuracy = get_model_accuracy()
    print(f"✅ Modelo cargado. Precisión: {accuracy}")
    
    # Rango: Feb 19 al Feb 26 (post All-Star break)
    start = date(2026, 2, 19)
    end = date(2026, 2, 26)
    
    conn = sqlite3.connect(DB_PATH)
    
    total_inserted = 0
    total_resolved = 0
    
    d = start
    while d <= end:
        date_str = d.strftime("%Y-%m-%d")
        print(f"\n📅 {date_str}")
        
        # Verificar si ya hay predicciones reales (prob != 52)
        cursor = conn.execute(
            "SELECT COUNT(*) FROM predictions WHERE date = ? AND prob_model != 52.0",
            (date_str,)
        )
        real_count = cursor.fetchone()[0]
        if real_count > 0:
            print(f"  ⏭️ Ya tiene {real_count} predicciones reales. Saltando modelo.")
            # Pero intentamos resolver resultados
            games = get_sbr_games(date_str)
            if games and d < date.today():
                resolved = resolve_results(conn, date_str, games)
                if resolved > 0:
                    total_resolved += resolved
            d += timedelta(days=1)
            continue
        
        # Borrar cualquier residuo antiguo para esta fecha
        conn.execute("DELETE FROM predictions WHERE date = ?", (date_str,))
        conn.commit()
        
        # Obtener juegos de SBR
        games = get_sbr_games(date_str)
        if not games:
            print(f"  ⏭️ Sin juegos NBA")
            d += timedelta(days=1)
            continue
        
        print(f"  🏀 {len(games)} juegos encontrados. Ejecutando XGBoost...")
        
        # Preparar datos para predict_games
        games_to_predict = []
        for g in games:
            away = g.get('away_team', '').replace("Los Angeles Clippers", "LA Clippers")
            home = g.get('home_team', '').replace("Los Angeles Clippers", "LA Clippers")
            
            ou_line = g.get('total', 220.0)
            try:
                ou_line = float(ou_line) if ou_line else 220.0
            except (ValueError, TypeError):
                ou_line = 220.0
            
            home_ml = g.get('home_ml')
            away_ml = g.get('away_ml')
            
            try:
                home_odds = float(home_ml) if home_ml else None
            except (ValueError, TypeError):
                home_odds = None
            try:
                away_odds = float(away_ml) if away_ml else None
            except (ValueError, TypeError):
                away_odds = None
            
            games_to_predict.append({
                "home_team": home,
                "away_team": away,
                "ou_line": ou_line,
                "home_odds": home_odds,
                "away_odds": away_odds,
                "game_date": d
            })
        
        # Ejecutar modelo XGBoost
        try:
            predictions = predict_games(games_to_predict, default_game_date=d)
            
            inserted = 0
            for pred in predictions:
                pred_dict = pred if isinstance(pred, dict) else pred
                
                # Construir datos para save_prediction
                away = pred_dict.get('away_team', '')
                home = pred_dict.get('home_team', '')
                match_id = f"{away} vs {home}"
                
                save_data = {
                    'date': date_str,
                    'match_id': match_id,
                    'home_team': home,
                    'away_team': away,
                    'winner': pred_dict.get('winner', home),
                    'win_probability': pred_dict.get('win_probability', 50),
                    'market_odds': pred_dict.get('odds_home') or pred_dict.get('odds_away') or 0,
                    'ev_value': pred_dict.get('ev_score', 0) or 0,
                    'kelly_stake_pct': pred_dict.get('kelly_stake', 0) or 0,
                    'warning_level': pred_dict.get('warning_level', 'NORMAL') or 'NORMAL',
                }
                
                try:
                    save_prediction(save_data)
                    inserted += 1
                except Exception as e:
                    print(f"  ⚠️ Error guardando {match_id}: {e}")
            
            print(f"  ✅ {inserted} predicciones XGBoost guardadas")
            total_inserted += inserted
            
        except Exception as e:
            print(f"  ❌ Error XGBoost: {e}")
            import traceback
            traceback.print_exc()
        
        # Resolver resultados para fechas pasadas
        if d < date.today():
            resolved = resolve_results(conn, date_str, games)
            total_resolved += resolved
        
        gc.collect()
        d += timedelta(days=1)
    
    conn.close()
    
    print(f"\n{'=' * 50}")
    print(f"📊 RESUMEN: {total_inserted} predicciones XGBoost, {total_resolved} resultados resueltos")
    print("✅ Backfill XGBoost completado")


def resolve_results(conn, date_str, games):
    """Actualiza Win/Loss con resultados reales de SBR."""
    results = {}
    for g in games:
        hs = g.get('home_score')
        aws = g.get('away_score')
        if hs is None or aws is None:
            continue
        try:
            hs = int(hs)
            aws = int(aws)
        except (ValueError, TypeError):
            continue
        
        actual_winner = g['home_team'] if hs > aws else g['away_team']
        actual_winner = actual_winner.replace("Los Angeles Clippers", "LA Clippers")
        home = g['home_team'].replace("Los Angeles Clippers", "LA Clippers")
        away = g['away_team'].replace("Los Angeles Clippers", "LA Clippers")
        match_id = f"{away} vs {home}"
        results[match_id] = actual_winner
    
    if results:
        update_results(date_str, results)
        print(f"  🏆 {len(results)} resultados Win/Loss resueltos")
        return len(results)
    return 0


if __name__ == "__main__":
    main()
