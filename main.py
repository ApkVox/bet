"""
===========================================
NBA PREDICTOR AI - MAIN API (LIGHT VERSION)
===========================================
Esta versión está optimizada para consumir <50MB RAM en Render.
Solo expone las APIs leyendo desde SQLite (history.db).
El trabajo pesado se movió a GitHub Actions (generate_daily_job.py).
"""

import os
import sys
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# Modules that only contain DB read logic
import history_db

# ===========================================
# CONFIGURACIÓN
# ===========================================
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "https://bet-7b8l.onrender.com")

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
    
    odds_home: Optional[int] = None
    odds_away: Optional[int] = None
    implied_prob: Optional[float] = None
    ev_score: Optional[float] = None
    kelly_stake: Optional[float] = None
    discrepancy: Optional[float] = None
    warning_level: Optional[str] = None
    value_type: Optional[str] = None
    sentiment_score: Optional[float] = None
    key_injuries: Optional[list] = None
    risk_analysis: Optional[str] = None
    game_status: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None

class PredictionResponse(BaseModel):
    date: str
    total_games: int
    predictions: list[MatchPrediction]
    model_accuracy: str
    status: str

# ===========================================
# INICIALIZACIÓN DE FASTAPI
# ===========================================
app = FastAPI(
    title="Courtside AI API (Light)",
    description="API de consulta de predicciones deportivas pre-calculadas",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Montar archivos estáticos
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup_event():
    print("===========================================")
    print("🚀 Courtside AI Light API Arrancando...")
    print("===========================================")
    history_db.init_history_db()


# ===========================================
# RUTAS DE LA API (FRONTEND Y LECTURA)
# ===========================================

@app.get("/")
async def serve_frontend():
    """Sirve la Single Page Application."""
    return FileResponse('static/index.html')


@app.get("/api/health")
async def health_check():
    """Endpoint simple para verificar que la DB responde."""
    return {"status": "online", "db_connected": True}


@app.get("/predict-today")
async def predict_today():
    """
    Obtiene las predicciones NBA generadas hoy desde la BD.
    Si no están listas o si es muy temprano, notifica al cliente que GitHub Actions está por correr.
    """
    date_str = datetime.now().strftime('%Y-%m-%d')
    existing_preds = history_db.get_predictions_by_date_light(date_str)
    
    if existing_preds:
        print(f"✅ Sirviendo {len(existing_preds)} juegos NBA desde caché DB (Light API)")
        return {
            "date": date_str,
            "total_games": len(existing_preds),
            "predictions": existing_preds,
            "model_accuracy": "70% (Offline)",
            "status": "success"
        }
    else:
        print("⚠️ No hay datos calculados para hoy en SQLite. Notificando al Frontend.")
        return {
            "date": date_str,
            "total_games": 0,
            "predictions": [],
            "model_accuracy": "N/A",
            "status": "pending_github_actions"
        }


@app.get("/predict-football")
async def predict_football():
    """
    Obtiene las predicciones de Fútbol preparadas por GitHub Actions.
    """
    preds = history_db.get_football_history(days=3)
    
    if preds:
         return {"status": "success", "count": len(preds), "predictions": preds}
    else:
         return {"status": "pending_github_actions", "count": 0, "predictions": []}


@app.get("/history/full")
async def get_full_history(days: int = 365):
    """Obtiene el historial NBA de los últimos días"""
    data = history_db.get_history(days)
    # El frontend espera { history: [...] }
    if isinstance(data, list):
        return {"history": data}
    return data


@app.get("/history/football")
async def get_football_history_endpoint(days: int = 30):
    """Obtiene el historial de fútbol de los últimos días."""
    data = history_db.get_football_history(days)
    if isinstance(data, list):
        return {"history": data}
    return data


# ===========================================
# STARTUP WEB SERVER
# ===========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Arrancando modo ultraligero en puerto {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
