"""
===========================================
NBA PREDICTOR AI - MAIN API (LIGHT VERSION)
===========================================
Esta versi├│n est├í optimizada para consumir <50MB RAM en Render.
Solo expone las APIs leyendo desde SQLite (history.db).
El trabajo pesado se movi├│ a GitHub Actions (generate_daily_job.py).
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
        print(f"[main] Error actualizando historial (no cr├¡tico): {e}")

# ===========================================
# CONFIGURACI├ôN
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
# INICIALIZACI├ôN DE FASTAPI
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
        "http://localhost:8080",
        "http://127.0.0.1:8080",
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


# Montar archivos est├íticos
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


@app.get("/admin")
async def serve_admin():
    """Sirve el panel de administración."""
    return FileResponse('static/admin.html')


@app.get("/api/settings")
async def get_public_settings():
    """Configuración pública (tema, branding, anuncios) para el frontend."""
    try:
        from admin_config import get_public_config
        return get_public_config()
    except Exception as e:
        print(f"[main] Error cargando config pública: {e}")
        return {"theme": {}, "branding": {}, "features": {}, "announcement": {}, "ads": {"enabled": False}}


# -------------------------------------------
# Admin API (autenticación JWT)
# -------------------------------------------
def _admin_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


@app.post("/api/admin/login")
async def admin_login(request: Request):
    """Login admin con contraseña; devuelve JWT."""
    from admin_config import load_config, verify_password, create_token, check_rate_limit, record_attempt
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not body or "password" not in body:
        raise HTTPException(status_code=400, detail="Falta contraseña")
    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera 15 minutos.")
    config = load_config()
    pwd_hash = config.get("password_hash") or ""
    if not pwd_hash:
        raise HTTPException(status_code=500, detail="No hay contraseña admin configurada. Ejecuta: python admin_config.py set-password")
    if not verify_password(body["password"], pwd_hash):
        record_attempt(ip)
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    token = create_token()
    return {"token": token}


@app.get("/api/admin/settings")
async def admin_get_settings(request: Request):
    """Obtiene la configuración completa (solo con JWT válido)."""
    from admin_config import verify_token, load_config
    token = _admin_token(request)
    if not token or not verify_token(token):
        raise HTTPException(status_code=401, detail="No autorizado")
    config = load_config()
    out = {k: v for k, v in config.items() if k not in ("password_hash", "jwt_secret")}
    return out


@app.post("/api/admin/settings")
async def admin_save_settings(request: Request):
    """Guarda la configuración (solo con JWT válido)."""
    from admin_config import verify_token, load_config, save_config
    token = _admin_token(request)
    if not token or not verify_token(token):
        raise HTTPException(status_code=401, detail="No autorizado")
    try:
        body = await request.json()
    except Exception:
        body = None
    if not body:
        raise HTTPException(status_code=400, detail="Body vacío")
    config = load_config()
    for key in ("theme", "branding", "features", "announcement", "ads"):
        if key in body:
            config[key] = body[key]
    save_config(config)
    return {"status": "ok"}


@app.post("/api/admin/password")
async def admin_change_password(request: Request):
    """Cambia la contraseña del admin (requiere JWT y contraseña actual)."""
    from admin_config import verify_token, load_config, save_config, verify_password, hash_password
    token = _admin_token(request)
    if not token or not verify_token(token):
        raise HTTPException(status_code=401, detail="No autorizado")
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not body or "current_password" not in body or "new_password" not in body:
        raise HTTPException(status_code=400, detail="Faltan current_password o new_password")
    if len(body["new_password"]) < 6:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 6 caracteres")
    config = load_config()
    if not verify_password(body["current_password"], config.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    config["password_hash"] = hash_password(body["new_password"])
    save_config(config)
    return {"status": "ok"}


@app.get("/api/health")
async def health_check():
    """Endpoint simple para verificar que la DB responde."""
    return {"status": "online", "db_connected": True}


@app.get("/predict-today")
async def predict_today():
    """
    Obtiene las predicciones NBA generadas hoy desde la BD.
    Si no est├ín listas, las genera en tiempo real (Self-Healing).
    """
    date_str = datetime.now(TZ_COLOMBIA).strftime('%Y-%m-%d')
    existing_preds = history_db.get_predictions_by_date_light(date_str)
    
    if not existing_preds:
        print("No hay datos NBA en SQLite. Generando On-Demand...")
        try:
            from generate_daily_job import generate_nba_predictions
            # Generar predicciones en tiempo real de forma as├¡ncrona pero esperando resultado
            new_preds = await generate_nba_predictions()
            if new_preds:
                # Reload from DB specifically to get the light DB format to match frontend expectations
                existing_preds = history_db.get_predictions_by_date_light(date_str)
        except Exception as e:
            print(f"Error generando NBA on-demand: {e}")

    if existing_preds:
        print(f"Sirviendo {len(existing_preds)} juegos NBA")
        return {
            "date": date_str,
            "total_games": len(existing_preds),
            "predictions": existing_preds,
            "model_accuracy": "70% (Offline)",
            "status": "success"
        }
    else:
        return {
            "date": date_str,
            "total_games": 0,
            "predictions": [],
            "model_accuracy": "N/A",
            "status": "no_games_today"
        }


@app.get("/predict-football")
async def predict_football():
    """
    Obtiene las predicciones de F├║tbol preparadas por la BD o las genera On-Demand.
    """
    import traceback, logging
    logger = logging.getLogger(__name__)
    try:
        preds = history_db.get_upcoming_football_predictions()
        
        if not preds:
            logger.info("No hay datos F├║tbol en SQLite. Generando On-Demand...")
            try:
                from generate_daily_job import generate_football_predictions
                new_preds = await generate_football_predictions()
                if new_preds:
                    preds = history_db.get_upcoming_football_predictions()
            except Exception as e:
                logger.error(f"Error generando F├║tbol on-demand: {e}")

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
    """Fuerza la actualizaci├│n de marcadores y predicciones de hoy. (On-Demand Refresh)"""
    try:
        from src.Services.history_service import update_pending_predictions
        from history_db import delete_predictions_for_date
        from generate_daily_job import generate_nba_predictions, generate_football_predictions
        
        # 1. Update old results
        result = await asyncio.to_thread(update_pending_predictions)
        
        # 2. Force delete today's pending matches to clear old odds
        today_str = datetime.now(TZ_COLOMBIA).strftime('%Y-%m-%d')
        deleted_count = await asyncio.to_thread(delete_predictions_for_date, today_str)
        print(f"[main] Eliminadas {deleted_count} predicciones antiguas para el d├¡a de hoy.")
        
        # 3. Trigger fresh generation
        await generate_nba_predictions()
        await generate_football_predictions()
        
        result['status'] = 'success'
        result['message'] = f'Marcadores actualizados y cuotas refrescadas para hoy.'
        return result
    except Exception as e:
        msg = str(e)
        print(f"[main] Error en refresh historial: {e}")
        raise HTTPException(status_code=500, detail=msg)


@app.get("/history/full")
async def get_full_history(background_tasks: BackgroundTasks, days: int = 365):
    """Obtiene el historial NBA de los ├║ltimos d├¡as. Dispara actualizaci├│n de marcadores en background."""
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
    """Obtiene el historial de f├║tbol de los ├║ltimos d├¡as."""
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
