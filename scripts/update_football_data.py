import pandas as pd
import requests
import io
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL base de football-data.co.uk
BASE_URL = "https://www.football-data.co.uk/mmz4281"
SEASONS = ["2324", "2425", "2526"] # Últimas 3 temporadas (incluyendo la actual)
LEAGUE_CODE = "E0" # Premier League

OUTPUT_PATH = "Data/football/complete_features.csv" # Mantenemos el nombre original para evitar romper dependencias

def download_season_data(season):
    url = f"{BASE_URL}/{season}/{LEAGUE_CODE}.csv"
    logger.info(f"Descargando datos de la temporada {season}: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        return df
    except Exception as e:
        logger.error(f"Error descargando temporada {season}: {e}")
        return None

def update_data():
    all_data = []
    
    for season in SEASONS:
        df = download_season_data(season)
        if df is not None:
            # Asegurarse de que la fecha esté en formato datetime para ordenar
            df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
            all_data.append(df)
    
    if not all_data:
        logger.error("No se pudieron obtener datos de ninguna temporada.")
        return

    # Combinar y limpiar
    combined_df = pd.concat(all_data, ignore_index=True)
    combined_df = combined_df.dropna(subset=['Date', 'HomeTeam', 'AwayTeam', 'FTR'])
    
    # Ordenar por fecha cronológica
    combined_df = combined_df.sort_values(by='Date')
    
    # Asegurar que el directorio existe
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    
    # Guardar
    combined_df.to_csv(OUTPUT_PATH, index=False)
    logger.info(f"¡Éxito! Base de datos actualizada con {len(combined_df)} partidos. Última fecha: {combined_df['Date'].max()}")

if __name__ == "__main__":
    update_data()
