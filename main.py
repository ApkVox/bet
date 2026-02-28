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
import asyncio
import threading
from datetime import datetime, timezone, timedelta
from typing import Optional

# Zona horaria de Colombia (UTC-5)
TZ_COLOMBIA = timezone(timedelta(hours=-5))

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# Modules that only contain DB read logic
import history_db

# Servicio que actualiza marcadores de partidos pasados (PENDING -> WIN/LOSS)
_last_history_update_run: Optional[datetime] = None
_HISTORY_UPDATE_COOLDOWN_MINUTES = 10

def _run_history_update():
    global _last_history_update_run
    _last_history_update_run = datetime.now(timezone.utc)
    try:
        from src.Services.history_service import update_pending_predictions
        update_pending_predictions()
    except Exception as e:
        print(f"[main] Error actualizando historial (no crítico): {e}")

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
    title="La Fija API",
    description="API de predicciones deportivas pre-calculadas",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://localhost:8081",
        "exp://192.168.18.9:8081",
        "https://bet-7b8l.onrender.com",
        "https://lafija.web.app" # Posible futuro dominio
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Montar archivos estáticos
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
async def startup_event():
    print("===========================================")
    print("La Fija API arrancando...")
    print("===========================================")
    history_db.init_history_db()
    # Actualizar marcadores de partidos pasados (PENDING -> WIN/LOSS) en segundo plano
    threading.Thread(target=_run_history_update, daemon=True).start()


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
    date_str = datetime.now(TZ_COLOMBIA).strftime('%Y-%m-%d')
    existing_preds = history_db.get_predictions_by_date_light(date_str)
    
    if existing_preds:
        print(f"Sirviendo {len(existing_preds)} juegos NBA desde cache DB")
        return {
            "date": date_str,
            "total_games": len(existing_preds),
            "predictions": existing_preds,
            "model_accuracy": "70% (Offline)",
            "status": "success"
        }
    else:
        print("No hay datos calculados para hoy en SQLite.")
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
    import traceback, logging
    logger = logging.getLogger(__name__)
    try:
        preds = history_db.get_upcoming_football_predictions()

        if preds:
            try:
                from football_logos import get_team_info
                for p in preds:
                    home_info = get_team_info(p['home_team'])
                    away_info = get_team_info(p['away_team'])
                    p['home_team'] = home_info.get('name', p['home_team'])
                    p['away_team'] = away_info.get('name', p['away_team'])
                    p['home_logo'] = home_info.get('logo')
                    p['away_logo'] = away_info.get('logo')
            except Exception as logo_err:
                logger.warning(f"football_logos enrichment failed (non-fatal): {logo_err}")

            return {"status": "success", "count": len(preds), "predictions": preds}
        else:
            return {"status": "pending_github_actions", "count": 0, "predictions": []}
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"predict-football FAILED:\n{tb}")
        return {"status": "error", "detail": str(e), "traceback": tb, "count": 0, "predictions": []}


@app.post("/history/refresh")
async def refresh_history_scores():
    """Fuerza la actualización de marcadores (PENDING -> WIN/LOSS) y devuelve el resultado."""
    try:
        from src.Services.history_service import update_pending_predictions
        # Ejecutar en thread para no bloquear el event loop (evita timeouts en Render)
        result = await asyncio.to_thread(update_pending_predictions)
        return result
    except Exception as e:
        msg = str(e)
        print(f"[main] Error en refresh historial: {e}")
        raise HTTPException(status_code=500, detail=msg)


@app.get("/history/full")
async def get_full_history(background_tasks: BackgroundTasks, days: int = 365):
    """Obtiene el historial NBA de los últimos días. Dispara actualización de marcadores en background."""
    # Actualizar partidos pendientes solo si no se ha corrido recientemente (throttle)
    now = datetime.now(timezone.utc)
    if _last_history_update_run is None or (now - _last_history_update_run).total_seconds() > _HISTORY_UPDATE_COOLDOWN_MINUTES * 60:
        background_tasks.add_task(_run_history_update)
    data = history_db.get_history(days)
    # El frontend espera { history: [...] }
    if isinstance(data, list):
        return {"history": data}
    return data


@app.get("/history/football")
async def get_football_history_endpoint(days: int = 30):
    """Obtiene el historial de fútbol de los últimos días."""
    import traceback, logging
    logger = logging.getLogger(__name__)
    try:
        data = history_db.get_football_history(days)

        if isinstance(data, list):
            try:
                from football_logos import get_team_info
                for p in data:
                    home_info = get_team_info(p['home_team'])
                    away_info = get_team_info(p['away_team'])
                    p['home_team'] = home_info.get('name', p['home_team'])
                    p['away_team'] = away_info.get('name', p['away_team'])
                    p['home_logo'] = home_info.get('logo')
                    p['away_logo'] = away_info.get('logo')
            except Exception as logo_err:
                logger.warning(f"football_logos enrichment failed (non-fatal): {logo_err}")

            return {"history": data}
        return data
    except Exception as e:
        tb = traceback.format_exc()
        logger.error(f"history/football FAILED:\n{tb}")
        return {"status": "error", "detail": str(e), "traceback": tb, "history": []}


# ===========================================
# STARTUP WEB SERVER
# ===========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Arrancando modo ultraligero en puerto {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
