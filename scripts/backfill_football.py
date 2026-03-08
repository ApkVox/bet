import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Añadir el directorio raíz al path para importar módulos locales
sys.path.append(os.getcwd())

from footy.poisson_predictor import PoissonScorelinePredictor
import history_db
from football_logos import get_team_info

def backfill():
    print("⏳ Iniciando Backfill de Fútbol (Premier League) desde 2026-01-01...")
    
    # 1. Cargar datos actualizados
    CSV_PATH = "Data/football/complete_features.csv"
    if not os.path.exists(CSV_PATH):
        print(f"❌ Error: No se encuentra {CSV_PATH}")
        return
        
    df = pd.read_csv(CSV_PATH)
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    # 2. Preparar el predictor
    predictor = PoissonScorelinePredictor()
    # Entrenamos con todo el DF (el Time Decay se encarga de priorizar lo reciente)
    predictor.calculate_team_strengths(df)
    
    # 3. Filtrar partidos desde el 1 de enero de 2026
    # Nota: El CSV solo tiene hasta mayo 2025. Para predecir 2026, 
    # necesitamos los fixtures o resultados de 2026 que NO están en el CSV de entrenamiento.
    # Si el CSV no tiene 2026, el backfill solo puede hacerse si tenemos otra fuente de fixtures.
    # Sin embargo, el usuario pide desde el 1 de enero. 
    # Vamos a buscar en el CSV si hay registros de 2026 (quizás la descarga los trajo).
    
    backfill_df = df[df['Date'] >= '2026-01-01'].copy()
    
    if len(backfill_df) == 0:
        print("⚠️ No hay partidos de 2026 en el CSV actual. El backfill estadístico requiere datos de resultados/fixtures.")
        print("Intentando obtener fixtures actuales de la temporada 24/25 que corresponden a 2026...")
        # Si el CSV descargado es E0.csv (Premier 24/25), los partidos de Enero-Mayo 2025 ya están ahí.
        # ¿Quizás el usuario se refiere a la temporada actual 25/26? 
        # Si estamos en Marzo 2026, la temporada es 25/26.
    
    print(f"📋 Procesando {len(backfill_df)} partidos encontrados desde 2026-01-01...")
    
    count = 0
    for idx, row in backfill_df.iterrows():
        home = row['HomeTeam']
        away = row['AwayTeam']
        date_str = row['Date'].strftime('%Y-%m-%d')
        actual_ftr = row['FTR'] # Resultado real
        
        # Generar predicción pura (sin noticias)
        probs_data = predictor.predict_scoreline_probabilities(home, away)
        outcomes = probs_data['outcome_probabilities']
        
        # Lógica de predicción (1, X, 2)
        best_outcome = max(outcomes, key=outcomes.get)
        if best_outcome == 'home_win': pred_str = '1'
        elif best_outcome == 'draw': pred_str = 'X'
        else: pred_str = '2'
        
        # Formatear para history_db
        prediction_data = {
            'home_team': home,
            'away_team': away,
            'prediction': pred_str,
            'league': 'ENG-Premier League',
            'probs': {
                'home': round(outcomes['home_win'] * 100, 1),
                'draw': round(outcomes['draw'] * 100, 1),
                'away': round(outcomes['away_win'] * 100, 1)
            },
            'confidence_modifier': 'neutral' # Sin noticias para el pasado
        }
        
        match_id = f"EPL_{home}_{away}_{date_str}".replace(" ", "_")
        
        # Guardar predicción
        history_db.save_football_prediction(prediction_data, match_id, date_str)
        
        # Si ya hay resultado real, actualizar el estado (WIN/LOSS)
        if pd.notna(actual_ftr):
            res_val = 'WIN'
            if pred_str == '1' and actual_ftr != 'H': res_val = 'LOSS'
            elif pred_str == 'X' and actual_ftr != 'D': res_val = 'LOSS'
            elif pred_str == '2' and actual_ftr != 'A': res_val = 'LOSS'
            
            # Usar la función interna para actualizar el resultado en la tabla football_predictions
            client = history_db._get_supabase()
            if client:
                client.table('football_predictions').update({'result': res_val}).eq('match_id', match_id).execute()
        
        count += 1
        if count % 10 == 0:
            print(f"✅ {count} partidos procesados...")

    print(f"✨ Backfill completado. {count} predicciones generadas y sincronizadas.")

if __name__ == "__main__":
    backfill()
