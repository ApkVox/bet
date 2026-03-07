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

from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
import uvicorn

# Modules that only contain DB read logic
import history_db

import admin_auth
import site_settings

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
    
    odds_home: Optional[float] = None
    odds_away: Optional[float] = None
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
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
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
    """Sirve la pantalla de login de administración."""
    return FileResponse('static/admin.html')


@app.get("/promo-editor")
async def serve_promo_editor():
    """Editor visual de promos (requiere haber hecho login en /admin)."""
    return FileResponse('static/promo_editor.html')


@app.get("/api/settings")
async def get_public_settings():
    """Configuración pública (tema, branding, anuncios) para el frontend."""
    return site_settings.get_public_settings()


# -------------------------------------------
# Admin API (login + cuenta inicial)
# -------------------------------------------


def _admin_token(request: Request) -> Optional[str]:
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


def require_admin(request: Request):
    """Valida JWT de administrador desde Authorization: Bearer <token>."""
    token = _admin_token(request)
    if not token or not admin_auth.verify_token(token):
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")


@app.get("/api/admin/status")
async def admin_status():
    """
    Devuelve el estado básico del módulo de administración:
    - has_admin: si ya existe una cuenta admin
    - token_ttl_hours: duración de los JWT
    """
    return {
        "has_admin": admin_auth.has_admin(),
        "token_ttl_hours": admin_auth.TOKEN_EXPIRY_HOURS,
    }


@app.post("/api/admin/create-initial")
async def admin_create_initial(request: Request):
    """
    Crea la cuenta inicial de administrador.
    Solo se permite si todavía no existe un admin.
    Body: { "password": "..." }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    password = (body.get("password") or "").strip()
    if not password:
        raise HTTPException(status_code=400, detail="Falta contraseña")

    if admin_auth.has_admin():
        raise HTTPException(status_code=400, detail="Ya existe una cuenta de administrador")

    try:
        admin_auth.create_initial_admin(password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        from config_store import ConfigStoreError
        print(f"[main] create-initial error: {type(e).__name__}: {e}")
        detail = str(e) if isinstance(e, ConfigStoreError) else "Error al guardar. Revisa DATABASE_URL y la tabla app_config en Supabase."
        raise HTTPException(status_code=500, detail=detail)

    return {"status": "ok", "message": "Cuenta de administrador creada correctamente"}


@app.post("/api/admin/login")
async def admin_login(request: Request):
    """
    Login admin con contraseña; devuelve un JWT.
    Body: { "password": "..." }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    password = (body.get("password") or "").strip()
    if not password:
        raise HTTPException(status_code=400, detail="Falta contraseña")

    ip = request.client.host if request.client else "unknown"
    if not admin_auth.check_rate_limit(ip):
        raise HTTPException(status_code=429, detail="Demasiados intentos. Espera 15 minutos.")

    try:
        token = admin_auth.login_with_password(password)
    except ValueError as e:
        admin_auth.record_attempt(ip)
        raise HTTPException(status_code=401, detail=str(e))

    return {"token": token}


@app.post("/api/admin/change-password")
async def admin_change_password(request: Request, _: None = Depends(require_admin)):
    """Cambia la contraseña del admin validando la actual."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    current = (body.get("current_password") or "").strip()
    new_pwd = (body.get("new_password") or "").strip()

    if not current or not new_pwd:
        raise HTTPException(status_code=400, detail="Faltan campos obligatorios")

    try:
        admin_auth.change_password(current, new_pwd)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "ok", "message": "Contraseña actualizada correctamente"}


@app.get("/api/admin/settings")
async def admin_get_settings(_: None = Depends(require_admin)):
    """
    Obtiene la configuración completa del sitio para el panel de administración.
    No incluye ninguna credencial sensible.
    """
    return site_settings.load_settings()


# Límites para evitar 413 en Render (payload demasiado grande)
_MAX_ANNOUNCEMENT_LEN = 500
_MAX_BRANDING_SUBTITLE_LEN = 200


@app.post("/api/admin/settings")
async def admin_save_settings(request: Request, _: None = Depends(require_admin)):
    """
    Guarda la configuración del sitio.
    Solo se actualizan las claves de alto nivel conocidas.
    Campos largos se truncan para evitar 413.
    """
    try:
        body = await request.json()
    except Exception:
        body = None

    if not isinstance(body, dict) or not body:
        raise HTTPException(status_code=400, detail="Body vacío o inválido")

    # Truncar campos que pueden crecer y causar 413
    if "announcement" in body and isinstance(body["announcement"], dict):
        t = body["announcement"].get("text", "")
        if isinstance(t, str) and len(t) > _MAX_ANNOUNCEMENT_LEN:
            body["announcement"] = {**body["announcement"], "text": t[:_MAX_ANNOUNCEMENT_LEN]}
    if "branding" in body and isinstance(body["branding"], dict):
        s = body["branding"].get("subtitle", "")
        if isinstance(s, str) and len(s) > _MAX_BRANDING_SUBTITLE_LEN:
            body["branding"] = {**body["branding"], "subtitle": s[:_MAX_BRANDING_SUBTITLE_LEN]}

    cfg = site_settings.load_settings()
    for key in ("theme", "branding", "features", "announcement", "ads", "betting"):
        if key in body:
            cfg[key] = body[key]

    site_settings.save_settings(cfg)
    return {"status": "ok"}


@app.get("/api/health")
async def health_check():
    """Endpoint simple para verificar que la DB responde."""
    return {"status": "online", "db_connected": True}


# -------------------------------------------
# Promo editor preview + config (admin y cards)
# -------------------------------------------
def _parse_promo_query(request: Request) -> tuple:
    """Extrae home_team, away_team, winner, probability y config_override de query params."""
    q = request.query_params
    home_team = q.get("home_team", "Charlotte Hornets")
    away_team = q.get("away_team", "Dallas Mavericks")
    winner = q.get("winner", home_team)
    prob_s = q.get("probability", "58.1")
    try:
        probability = float(prob_s)
    except ValueError:
        probability = 58.1
    config_override = {}
    int_keys = (
        "logo_cy", "logo_left_cx", "logo_right_offset", "logo_max",
        "names_y", "names_font_size", "names_max_w",
        "box_y0", "box_y1", "box_pad_x", "box_radius", "box_border_w",
        "label_offset_y", "label_font_size",
        "winner_offset_y", "winner_font_size",
        "prob_offset_y", "prob_font_size",
        "footer_y", "footer_font_size",
    )
    color_keys = ("names_color", "box_border_color", "label_color", "winner_color", "prob_color", "footer_color")
    for k in int_keys:
        v = q.get(k)
        if v is not None:
            try:
                config_override[k] = int(v)
            except ValueError:
                pass
    for k in color_keys:
        v = q.get(k)
        if v:
            config_override[k] = v
    for toggle in ("show_logos", "show_names", "show_box_border", "show_label", "show_winner", "show_prob", "show_footer"):
        v = q.get(toggle)
        if v is not None:
            config_override[toggle] = str(v).lower() in ("true", "1", "yes", "on")
    return home_team, away_team, winner, probability, config_override


@app.get("/api/promo-editor-preview")
async def promo_editor_preview_get(request: Request):
    """Preview por GET (query params). Para URLs largas usar POST."""
    try:
        from promo_generator import generate_promo_image
        home_team, away_team, winner, probability, config_override = _parse_promo_query(request)
        data = generate_promo_image(home_team, away_team, winner, probability, status=None, config_override=config_override or None)
        return Response(content=data, media_type="image/png")
    except Exception as e:
        print(f"[main] promo-editor-preview error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/promo-editor-preview")
async def promo_editor_preview_post(request: Request):
    """Preview por POST (body JSON). Evita 413 por URL demasiado larga en Render."""
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(400, "Body debe ser JSON object")
        home_team = str(body.get("home_team", "Charlotte Hornets"))[:80]
        away_team = str(body.get("away_team", "Dallas Mavericks"))[:80]
        winner = str(body.get("winner", home_team))[:80]
        probability = float(body.get("probability", 58.1))
        config_override = {k: v for k, v in body.items() if k not in ("home_team", "away_team", "winner", "probability")}
        from promo_generator import generate_promo_image
        data = generate_promo_image(home_team, away_team, winner, probability, status=None, config_override=config_override or None)
        return Response(content=data, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[main] promo-editor-preview POST error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/promo-image")
async def promo_image(request: Request):
    """Genera imagen de promo para una predicción (para descargar desde las cards)."""
    try:
        from promo_generator import generate_promo_image
        home_team = request.query_params.get("home_team", "")
        away_team = request.query_params.get("away_team", "")
        winner = request.query_params.get("winner", "")
        prob_s = request.query_params.get("probability", "0")
        status = request.query_params.get("status")  # PENDING, WIN, LOSS -> Ganada/Perdida
        try:
            probability = float(prob_s)
        except ValueError:
            probability = 0.0
        if not home_team or not away_team or not winner:
            raise HTTPException(status_code=400, detail="Faltan home_team, away_team o winner")
        status_label = None
        if status and str(status).upper() in ("WIN", "GANADA"):
            status_label = "GANADA"
        elif status and str(status).upper() in ("LOSS", "PERDIDA"):
            status_label = "PERDIDA"
        data = generate_promo_image(home_team, away_team, winner, probability, status=status_label)
        return Response(content=data, media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        print(f"[main] promo-image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/promo-config")
async def get_promo_config(_: None = Depends(require_admin)):
    """Devuelve la configuración del editor de promo (layout)."""
    try:
        from promo_generator import load_config
        return load_config()
    except Exception as e:
        print(f"[main] get promo-config error: {e}")
        return {}


_PROMO_CONFIG_KEYS = frozenset((
    "logo_cy", "logo_left_cx", "logo_right_offset", "logo_max",
    "names_y", "names_font_size", "names_max_w", "names_color",
    "box_y0", "box_y1", "box_pad_x", "box_radius", "box_border_w", "box_border_color",
    "label_offset_y", "label_font_size", "label_color",
    "winner_offset_y", "winner_font_size", "winner_color",
    "prob_offset_y", "prob_font_size", "prob_color",
    "footer_y", "footer_font_size", "footer_color",
    "show_logos", "show_names", "show_box_border", "show_label", "show_winner", "show_prob", "show_footer",
))


@app.post("/api/promo-config")
async def save_promo_config(request: Request, _: None = Depends(require_admin)):
    """Guarda la configuración del editor de promo. Solo claves conocidas (evita 413)."""
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(400, "Body debe ser JSON object")
        cfg = {k: v for k, v in body.items() if k in _PROMO_CONFIG_KEYS}
        from promo_generator import save_config
        save_config(cfg)
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[main] save promo-config error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


# -------------------------------------------
# DeepSeek API Key management
# -------------------------------------------

@app.post("/api/admin/deepseek-key")
async def save_deepseek_key(request: Request, _: None = Depends(require_admin)):
    """Guarda la API key de DeepSeek (solo para esta sesión del servidor)."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body inválido")
    key = (body.get("key") or "").strip()
    if not key or not key.startswith("sk-"):
        raise HTTPException(status_code=400, detail="API key inválida (debe empezar con sk-)")
    os.environ["DEEPSEEK_API_KEY"] = key
    return {"status": "ok", "message": "API Key actualizada para esta sesión."}


# -------------------------------------------
# News API (DeepSeek agent cache)
# -------------------------------------------

@app.get("/api/news/today")
async def get_today_news():
    """Returns all cached news for today's NBA matches."""
    date_str = datetime.now(TZ_COLOMBIA).strftime('%Y-%m-%d')
    return {"date": date_str, "news": history_db.get_news_for_date(date_str)}


@app.post("/api/news/refresh")
async def refresh_news(background_tasks: BackgroundTasks):
    """Busca noticias para los partidos NBA de hoy (local/dev). Requiere DEEPSEEK_API_KEY."""
    date_str = datetime.now(TZ_COLOMBIA).strftime('%Y-%m-%d')
    preds = history_db.get_predictions_by_date_light(date_str)
    if not preds:
        return {"date": date_str, "status": "skip", "message": "No hay predicciones NBA para hoy."}
    try:
        from news_agent import fetch_news_for_matches
        results = await fetch_news_for_matches(date_str, preds)
        return {"date": date_str, "status": "ok", "fetched": len(results), "news": results}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/news/{match_id:path}")
async def get_match_news(match_id: str):
    """Returns cached news for a specific NBA match (fútbol no tiene noticias)."""
    data = history_db.get_match_news(match_id)
    if not data:
        return {"found": False, "news": None}
    return {"found": True, "news": data}


# -------------------------------------------
# Recommendations API
# -------------------------------------------

@app.get("/api/recommendations/today")
async def get_recommendations_today():
    """Returns today's betting recommendations (generates on first call)."""
    date_str = datetime.now(TZ_COLOMBIA).strftime('%Y-%m-%d')
    try:
        from recommendations import generate_recommendations
        data = await generate_recommendations(date_str)
        return {"date": date_str, "status": "ok", **data}
    except Exception as e:
        print(f"[main] recommendations error: {e}")
        return {"date": date_str, "status": "error", "recommendations": [], "parlay_odds": 0}


@app.get("/api/recommendations/history")
async def get_recommendations_history():
    """Returns past parlay recommendations with win/loss results."""
    return {"history": history_db.get_recommendations_history(14)}


@app.post("/api/recommendations/calculate")
async def calculate_parlay_endpoint(request: Request):
    """Calculate potential profit for a parlay bet.
    Body: { "amount": 50000, "odds": [1.85, 2.10, 1.65] }
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body inválido")

    amount = float(body.get("amount", 0))
    odds_list = body.get("odds", [])

    if amount <= 0 or not odds_list:
        raise HTTPException(status_code=400, detail="Monto y cuotas requeridos")

    from recommendations import calculate_parlay as calc
    result = calc([float(o) for o in odds_list], amount)
    return result


# ===========================================
# STARTUP WEB SERVER
# ===========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Arrancando modo ultraligero en puerto {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
