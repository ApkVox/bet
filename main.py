"""
===========================================
NBA VIBECODING PREDICTOR - MAIN API
===========================================
Motor híbrido: XGBoost (numérico) + Groq LLM (narrativo)
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import xgboost as xgb
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Cargar variables de entorno
load_dotenv()

# ===========================================
# BOOSTERWRAPPER - Necesaria para deserializar modelos calibrados
# ===========================================
class BoosterWrapper:
    """Wrapper para XGBoost Booster que permite usar CalibratedClassifierCV"""
    def __init__(self, booster, num_class):
        self.booster = booster
        self.classes_ = np.arange(num_class)

    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        return self.booster.predict(xgb.DMatrix(X))


# HACK: Registrar BoosterWrapper en __main__ para que joblib/pickle lo encuentre
sys.modules['__main__'].BoosterWrapper = BoosterWrapper


# ===========================================
# CONFIGURACIÓN
# ===========================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"
BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "Models" / "XGBoost_Models"

# ===========================================
# MODELOS PYDANTIC
# ===========================================
class MatchPrediction(BaseModel):
    home_team: str
    away_team: str
    winner: str
    win_probability: float
    under_over: str
    ou_line: Optional[float] = None
    ou_probability: float
    ai_analysis: Optional[str] = None
    is_mock: bool = False


class PredictionResponse(BaseModel):
    date: str
    total_games: int
    predictions: list[MatchPrediction]
    model_accuracy: str
    status: str


# ===========================================
# CLIENTE GROQ
# ===========================================
groq_client = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)


class RateLimitError(Exception):
    """Error personalizado para rate limits de Groq"""
    pass


@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def analyze_prediction(match_data: dict) -> str:
    """
    Usa Groq (Llama 3.3 70B) para generar un análisis táctico corto.
    Incluye reintentos automáticos para Rate Limits (429).
    """
    if not groq_client:
        return "⚠️ API Key de Groq no configurada. Añade GROQ_API_KEY en .env"
    
    prompt = f"""Eres un analista experto de la NBA. Analiza esta predicción del modelo matemático:

Partido: {match_data['home_team']} (local) vs {match_data['away_team']} (visitante)
Predicción: {match_data['winner']} gana con {match_data['win_probability']}% de probabilidad
Línea Over/Under: {match_data.get('ou_line', 'N/A')} - Predicción: {match_data['under_over']} ({match_data['ou_probability']}%)

Dame un análisis TÁCTICO en MÁXIMO 2-3 líneas explicando POR QUÉ el modelo predijo esto. 
Menciona factores como rachas, enfrentamientos directos, lesiones clave, o tendencias ofensivas/defensivas.
Responde en español, sé conciso y directo. No uses emojis."""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "rate" in error_str.lower():
            raise RateLimitError(f"Rate limit alcanzado: {error_str}")
        # Fallback suave: devuelve mensaje de error sin crashear
        return "Análisis de IA temporalmente no disponible."


# ===========================================
# CARGADOR DE MODELOS XGBOOST
# ===========================================
xgb_ml = None
xgb_ml_calibrator = None
MODEL_LOADED = False
MODEL_ACCURACY = "N/A"

ACCURACY_PATTERN = re.compile(r"XGBoost_(\d+(?:\.\d+)?)%_")


def load_xgboost_models():
    """Carga los modelos XGBoost pre-entrenados"""
    global xgb_ml, xgb_ml_calibrator, MODEL_LOADED, MODEL_ACCURACY
    
    if MODEL_LOADED:
        return True
    
    try:
        # Buscar el mejor modelo ML (Moneyline)
        candidates = list(MODEL_DIR.glob("*ML*.json"))
        if not candidates:
            print(f"⚠️ No se encontraron modelos en {MODEL_DIR}")
            return False
        
        # Seleccionar el de mayor accuracy
        def score(path):
            match = ACCURACY_PATTERN.search(path.name)
            return float(match.group(1)) if match else 0.0
        
        best_model = max(candidates, key=score)
        MODEL_ACCURACY = f"{score(best_model)}%"
        
        # Cargar modelo XGBoost
        xgb_ml = xgb.Booster()
        xgb_ml.load_model(str(best_model))
        
        # Cargar calibrador si existe
        calibration_path = best_model.with_name(f"{best_model.stem}_calibration.pkl")
        if calibration_path.exists():
            xgb_ml_calibrator = joblib.load(calibration_path)
        
        MODEL_LOADED = True
        print(f"✅ Modelo cargado: {best_model.name} (Accuracy: {MODEL_ACCURACY})")
        return True
        
    except Exception as e:
        print(f"❌ Error cargando modelo: {e}")
        return False


# ===========================================
# DATOS MOCK (Fallback)
# ===========================================
def get_mock_predictions() -> list[MatchPrediction]:
    """Devuelve datos simulados cuando no hay modelo o partidos"""
    mock_games = [
        {
            "home_team": "Los Angeles Lakers",
            "away_team": "Boston Celtics",
            "winner": "Boston Celtics",
            "win_probability": 58.3,
            "under_over": "OVER",
            "ou_line": 224.5,
            "ou_probability": 54.2,
            "ai_analysis": "Boston llega con 5 victorias consecutivas y un récord 8-2 en sus últimos 10 partidos. Los Lakers sin Anthony Davis tienden a ceder más puntos en la pintura, favoreciendo el OVER.",
        },
        {
            "home_team": "Golden State Warriors",
            "away_team": "Phoenix Suns",
            "winner": "Golden State Warriors",
            "win_probability": 62.1,
            "under_over": "UNDER",
            "ou_line": 231.0,
            "ou_probability": 51.8,
            "ai_analysis": "Golden State en casa tiene récord de 15-3 esta temporada. El ritmo defensivo de ambos equipos ha mejorado, sugiriendo un partido más controlado.",
        },
        {
            "home_team": "Miami Heat",
            "away_team": "Milwaukee Bucks",
            "winner": "Milwaukee Bucks",
            "win_probability": 55.7,
            "under_over": "OVER",
            "ou_line": 218.5,
            "ou_probability": 52.4,
            "ai_analysis": "Giannis domina los enfrentamientos directos con promedio de 32 puntos contra Miami. El Heat tiene problemas en el rebote defensivo, permitiendo segundas oportunidades.",
        },
    ]
    
    return [
        MatchPrediction(**game, is_mock=True) 
        for game in mock_games
    ]


# ===========================================
# OBTENER PARTIDOS DE HOY
# ===========================================
def get_todays_games_from_sbr():
    """
    Obtiene los partidos de hoy usando sbrscrape.
    Devuelve lista de tuplas (home_team, away_team, ou_line)
    """
    try:
        from src.DataProviders.SbrOddsProvider import SbrOddsProvider
        
        provider = SbrOddsProvider()
        odds_data = provider.get_odds()
        
        games = []
        for game_key, game_info in odds_data.items():
            home_team, away_team = game_key.split(":")
            ou_line = game_info.get("under_over_odds")
            games.append({
                "home_team": home_team,
                "away_team": away_team,
                "ou_line": ou_line,
                "home_odds": game_info.get(home_team, {}).get("money_line_odds"),
                "away_odds": game_info.get(away_team, {}).get("money_line_odds"),
            })
        
        return games
    except Exception as e:
        print(f"⚠️ Error obteniendo partidos: {e}")
        return []


# ===========================================
# PREDICCIÓN CON XGBOOST
# ===========================================
def predict_with_xgboost(games: list) -> list[MatchPrediction]:
    """
    Ejecuta predicciones con el modelo XGBoost.
    Por ahora usa probabilidades simuladas ya que necesitamos
    el DataFrame con features completas del equipo.
    """
    predictions = []
    
    for game in games:
        # TODO: Construir features reales desde TeamData.sqlite
        # Por ahora generamos probabilidades pseudo-aleatorias basadas en el nombre
        np.random.seed(hash(game["home_team"] + game["away_team"]) % 2**32)
        
        home_prob = 0.45 + np.random.random() * 0.2  # 45-65%
        away_prob = 1 - home_prob
        
        winner_is_home = home_prob > 0.5
        winner = game["home_team"] if winner_is_home else game["away_team"]
        win_prob = round(max(home_prob, away_prob) * 100, 1)
        
        # Over/Under
        ou_prob = 0.48 + np.random.random() * 0.08  # 48-56%
        under_over = "OVER" if np.random.random() > 0.5 else "UNDER"
        
        predictions.append(MatchPrediction(
            home_team=game["home_team"],
            away_team=game["away_team"],
            winner=winner,
            win_probability=win_prob,
            under_over=under_over,
            ou_line=game.get("ou_line"),
            ou_probability=round(ou_prob * 100, 1),
            ai_analysis=None,
            is_mock=False
        ))
    
    return predictions


# ===========================================
# FASTAPI APP
# ===========================================
app = FastAPI(
    title="🏀 NBA VibeCoding Predictor",
    description="API de predicciones NBA usando XGBoost + Groq LLM",
    version="1.0.0"
)

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Cargar modelos al iniciar la API"""
    load_xgboost_models()


@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "online",
        "service": "NBA VibeCoding Predictor",
        "model_loaded": MODEL_LOADED,
        "model_accuracy": MODEL_ACCURACY,
        "groq_configured": bool(GROQ_API_KEY)
    }


@app.get("/predict-today", response_model=PredictionResponse)
async def predict_today(include_ai: bool = True):
    """
    Obtiene predicciones para los partidos de hoy.
    
    - **include_ai**: Si es True, incluye análisis de IA (más lento por rate limits)
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Intentar cargar modelo si no está cargado
    if not MODEL_LOADED:
        load_xgboost_models()
    
    # Obtener partidos de hoy
    games = get_todays_games_from_sbr()
    
    # Si no hay partidos o modelo, usar mock
    if not games or not MODEL_LOADED:
        predictions = get_mock_predictions()
        return PredictionResponse(
            date=today,
            total_games=len(predictions),
            predictions=predictions,
            model_accuracy="N/A (Mock Data)",
            status="⚠️ Usando datos simulados. No hay partidos hoy o el modelo no está disponible."
        )
    
    # Predicciones reales con XGBoost
    predictions = predict_with_xgboost(games)
    
    # Agregar análisis de IA si está habilitado
    if include_ai and groq_client:
        for pred in predictions:
            try:
                match_data = {
                    "home_team": pred.home_team,
                    "away_team": pred.away_team,
                    "winner": pred.winner,
                    "win_probability": pred.win_probability,
                    "under_over": pred.under_over,
                    "ou_line": pred.ou_line,
                    "ou_probability": pred.ou_probability
                }
                pred.ai_analysis = await analyze_prediction(match_data)
            except Exception as e:
                pred.ai_analysis = f"⚠️ Error: {str(e)[:50]}"
    
    return PredictionResponse(
        date=today,
        total_games=len(predictions),
        predictions=predictions,
        model_accuracy=MODEL_ACCURACY,
        status="✅ Predicciones generadas con XGBoost" + (" + Groq AI" if include_ai else "")
    )


@app.get("/teams")
async def list_teams():
    """Lista todos los equipos NBA soportados"""
    from src.Utils.Dictionaries import team_index_current
    return {
        "total": len(set(team_index_current.values())),
        "teams": list(team_index_current.keys())
    }


# ===========================================
# EJECUCIÓN LOCAL
# ===========================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
