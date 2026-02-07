"""
===========================================
NBA PREDICTOR AI - MAIN API
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
import history_db
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from groq import Groq
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Cargar variables de entorno
load_dotenv()

# ===========================================
# SCHEDULER GLOBAL
# ===========================================
scheduler = AsyncIOScheduler()
LAST_UPDATE_TIME = None
UPDATE_RESULTS = []

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
    
    # Campos de cuotas de mercado y discrepancia
    market_odds_home: Optional[int] = None  # American odds
    market_odds_away: Optional[int] = None
    implied_prob_market: Optional[float] = None
    discrepancy: Optional[float] = None
    warning_level: str = "NORMAL"  # 'NORMAL', 'MEDIUM', 'HIGH'
    
    # Campos de bankroll y valor esperado
    ev_value: Optional[float] = None  # Expected Value %
    is_value_bet: bool = False  # True si EV > 0
    kelly_stake_pct: Optional[float] = None  # % de bankroll (Kelly/4)
    value_type: Optional[str] = None  # 'NORMAL', 'GOLDEN_OPPORTUNITY'
    
    # MVP v1.0: Campos críticos de decisión
    risk_level: str = "NORMAL"  # 'NORMAL', 'MEDIUM', 'HIGH', 'EXTREME'
    status: str = "BET"  # 'BET', 'CAUTION', 'DO_NOT_BET'
    sentiment_score: Optional[float] = None  # -1.0 a 1.0 de IA
    key_injuries: Optional[list] = None  # Lista de lesiones detectadas
    risk_analysis: Optional[str] = None  # Análisis corto de riesgo

    # Live Score Fields
    game_status: Optional[str] = None # e.g. "Top 1st", "Final"
    home_score: Optional[int] = None
    away_score: Optional[int] = None


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


# ===========================================
# CUOTAS DE MERCADO Y DISCREPANCIA
# ===========================================
ODDS_API_KEY = os.getenv("ODDS_API_KEY", None)

def fetch_market_odds(home_team: str, away_team: str) -> dict:
    """
    Obtiene cuotas REALES de mercado del cache de SBR.
    Fallback a mock solo si no hay datos.
    """
    global TODAYS_GAMES_CACHE
    
    # Buscar en el cache de partidos reales
    for game in TODAYS_GAMES_CACHE:
        if game.get("home_team") == home_team and game.get("away_team") == away_team:
            home_odds = game.get("home_odds")
            away_odds = game.get("away_odds")
            if home_odds is not None and away_odds is not None:
                return {
                    "home_odds": home_odds,
                    "away_odds": away_odds,
                    "is_real": True
                }
    
    # Fallback a mock si no encontramos cuotas reales
    import hashlib
    team_hash = int(hashlib.md5(f"{home_team}{away_team}".encode()).hexdigest(), 16)
    is_home_favorite = (team_hash % 2) == 0
    
    if is_home_favorite:
        home_odds = -(120 + (team_hash % 200))
        away_odds = +(110 + (team_hash % 150))
    else:
        home_odds = +(110 + (team_hash % 150))
        away_odds = -(120 + (team_hash % 200))
    
    return {
        "home_odds": home_odds,
        "away_odds": away_odds,
        "is_real": False
    }


def american_to_decimal(american_odds: int) -> float:
    """Convierte odds americanas a decimales"""
    if american_odds >= 100:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1


def calculate_implied_probability(american_odds: int) -> float:
    """Calcula probabilidad implícita de la cuota"""
    decimal_odds = american_to_decimal(american_odds)
    return round((1 / decimal_odds) * 100, 1)


def calculate_discrepancy_analysis(model_prob: float, market_odds: int, is_home: bool) -> dict:
    """
    Analiza la discrepancia entre modelo y mercado.
    
    Returns:
        {
            "implied_prob": float,
            "discrepancy": float,  # abs(model_prob - implied_prob)
            "warning_level": str   # 'NORMAL', 'MEDIUM', 'HIGH'
        }
    """
    if not market_odds:
        return {
            "implied_prob": None,
            "discrepancy": 0.0,
            "warning_level": "NORMAL"
        }
    
    implied_prob = calculate_implied_probability(market_odds)
    discrepancy = abs(model_prob - implied_prob)
    
    # Determinar nivel de alerta
    if discrepancy > 15:
        warning_level = "HIGH"
    elif discrepancy > 8:
        warning_level = "MEDIUM"
    else:
        warning_level = "NORMAL"
    
    return {
        "implied_prob": implied_prob,
        "discrepancy": round(discrepancy, 1),
        "warning_level": warning_level
    }


def calculate_expected_value(model_prob: float, american_odds: int) -> float:
    """
    Calcula Expected Value (EV).
    Formula: (prob × payout) - 1
    
    EV > 0 = Value Bet (el modelo cree que tiene ventaja)
    EV < 0 = No apostar
    """
    if not american_odds:
        return 0.0
    
    # Convertir a decimal
    decimal_odds = american_to_decimal(american_odds)
    
    # Calcular EV
    prob_decimal = model_prob / 100
    ev = (prob_decimal * decimal_odds) - 1
    
    return round(ev * 100, 1)  # Devolver como porcentaje


def calculate_kelly_stake(model_prob: float, american_odds: int, safety_factor: float = 0.25) -> float:
    """
    Calcula Kelly Stake (% de bankroll óptimo).
    Formula: (prob × odds - 1) / (odds - 1)
    
    Args:
        model_prob: Probabilidad del modelo (%)
        american_odds: Cuota americana
        safety_factor: Fracción de Kelly (default: 1/4 Kelly para seguridad)
    
    Returns:
        % de bankroll a apostar (0-5%)
    """
    if not american_odds or model_prob <= 0:
        return 0.0
    
    decimal_odds = american_to_decimal(american_odds)
    prob_decimal = model_prob / 100
    
    # Kelly Formula
    kelly = (prob_decimal * decimal_odds - 1) / (decimal_odds - 1)
    
    # Aplicar safety factor (Fractional Kelly)
    kelly_adjusted = kelly * safety_factor
    
    # Limitar entre 0% y 5% de bankroll (nunca apostar más del 5%)
    kelly_clamped = max(0, min(0.05, kelly_adjusted))
    
    return round(kelly_clamped * 100, 2)  # Devolver como %


# ===========================================
# MVP v1.0: BÚSQUEDA BLINDADA CON TENACITY
# ===========================================
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True
)
def _search_news_with_retry(team_name: str) -> list:
    """
    Búsqueda con reintentos automáticos usando tenacity.
    Query específica: '"{team_name}" nba injuries report today'
    """
    from duckduckgo_search import DDGS
    
    # Extraer nombre corto del equipo
    team_short = team_name.split()[-1]
    
    # Query ESPECÍFICA con comillas para exactitud
    query = f'"{team_short}" nba injuries report today'
    
    print(f"   🔍 Query: '{query}'")
    
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=3))
    
    return results


async def search_news_async(home_team: str, away_team: str) -> Optional[str]:
    """
    MVP v1.0: Búsqueda blindada asíncrona.
    - Usa tenacity para reintentos (3 intentos)
    - Query específica con comillas
    - Devuelve None explícitamente si falla (NO string vacío)
    - Ejecuta en thread pool para no bloquear el servidor
    """
    import asyncio
    
    def _search_sync():
        """Función síncrona ejecutada en thread pool"""
        try:
            # Extraer nombres cortos
            home_short = home_team.split()[-1]
            away_short = away_team.split()[-1]
            
            print(f"\n🔍 [MVP] Búsqueda blindada de noticias...")
            print(f"   Equipos: {home_team} vs {away_team}")
            
            all_results = []
            
            # Buscar noticias para cada equipo con reintentos
            for team in [home_team, away_team]:
                try:
                    results = _search_news_with_retry(team)
                    print(f"   ✓ {team.split()[-1]}: {len(results)} resultados")
                    all_results.extend(results)
                except Exception as e:
                    print(f"   ✗ {team.split()[-1]}: Error después de 3 reintentos - {str(e)[:40]}")
            
            # DEBUG: Mostrar resultados
            print(f"\n📰 [MVP] Resultados:")
            if all_results:
                # Eliminar duplicados
                unique_results = []
                seen = set()
                for r in all_results:
                    title = r.get('title', '')
                    if title and title not in seen:
                        unique_results.append(r)
                        seen.add(title)
                
                print(f"   Total: {len(unique_results)} noticias únicas")
                for i, r in enumerate(unique_results[:5], 1):
                    print(f"   {i}. {r.get('title', 'N/A')[:60]}...")
                
                # Formatear noticias
                news_items = []
                for r in unique_results[:6]:
                    title = r.get('title', 'Sin título')
                    body = r.get('body', r.get('snippet', ''))[:150]
                    if body:
                        news_items.append(f"- {title}: {body}")
                
                return "\n".join(news_items) if news_items else None
            else:
                print("   ⚠️ NINGUNA NOTICIA ENCONTRADA")
                return None  # Explícitamente None, NO string vacío
            
        except Exception as e:
            print(f"   ❌ ERROR CRÍTICO: {str(e)}")
            return None  # Fallo total = None
    
    # Ejecutar en thread pool para no bloquear servidor principal
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search_sync)


# ===========================================
# ANÁLISIS IA CON IMPACT SCORE
# ===========================================
@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def analyze_with_impact(match_data: dict) -> dict:
    """
    Analiza el partido con IA y devuelve un diccionario con:
    - impact_score: float entre -0.5 y 0.5
    - key_factor: string con el factor más importante
    - reasoning: string con el análisis corto
    """
    default_result = {
        "impact_score": 0.0,
        "key_factor": "Sin datos",
        "reasoning": "Análisis no disponible."
    }
    
    if not groq_client:
        return default_result
    
    # Buscar noticias reales (versión async)
    noticias = await search_news_async(match_data['home_team'], match_data['away_team'])
    
    # NUEVO: Contexto de discrepancia si es alta
    discrepancy_context = ""
    if match_data.get("warning_level") == "HIGH":
        market_odds = match_data.get('market_odds_winner', 'N/A')
        implied_prob = match_data.get('implied_prob_market', 0)
        discrepancy = match_data.get('discrepancy', 0)
        
        discrepancy_context = f"""
⚠️ ALERTA DE DISCREPANCIA ALTA:
- Modelo XGBoost: {match_data['win_probability']}%
- Mercado (cuota {market_odds}): {implied_prob}% implícito
- Discrepancia: {discrepancy}%

INSTRUCCIÓN CRÍTICA:
El mercado está FUERTEMENTE EN CONTRA del modelo ({discrepancy}% de diferencia).
Esto puede indicar:
1. Lesión de última hora que el modelo no conoce
2. Información privilegiada del mercado
3. Sobrerreacción del mercado a noticias recientes

Tu análisis debe ser DE ALERTA. NO recomiendes esta apuesta ciegamente.
Investiga POR QUÉ el mercado difiere tanto del modelo.
"""
    
    # MVP v1.0: System Prompt V3 - JSON estructurado
    # Manejamos el caso de None explícito de la búsqueda
    noticias_text = noticias if noticias else "NO_NEWS_FOUND"
    
    prompt = f"""Eres un ANALISTA DE RIESGO para apuestas NBA profesionales.

PARTIDO: {match_data['home_team']} (LOCAL) vs {match_data['away_team']} (VISITANTE)
PREDICCIÓN MODELO XGBOOST: {match_data['winner']} gana con {match_data['win_probability']}%

{discrepancy_context}

NOTICIAS DE HOY:
{noticias_text}

🔴 REGLA DE ORO: Si tu sentiment_score es 0 (neutral), DEBES justificar explícitamente por qué.
Ejemplo válido: "Plantillas completas confirmadas, sin lesiones reportadas"
🚫 PROHIBIDO: "Noticias neutrales" o "No hay factores significativos"

📊 ESCALA sentiment_score:
- +1.0 = Noticia muy positiva (rival sin star player confirmado)
- +0.5 = Noticia positiva (equipo local en racha ganadora)
- 0.0 = Neutral JUSTIFICADO (plantillas completas confirmadas)
- -0.5 = Noticia negativa (jugador clave GTD/Questionable)
- -1.0 = Noticia muy negativa (star player OUT confirmado)

RESPONDE ÚNICAMENTE CON ESTE JSON (sin markdown, sin texto extra):
{{"sentiment_score": 0.0, "key_injuries": ["nombre1", "nombre2"], "risk_analysis": "análisis corto y denso"}}"""

    try:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.2  # Muy baja para JSON consistente
        )
        
        raw_response = response.choices[0].message.content.strip()
        
        import json
        
        # Limpiar respuesta (LLM a veces añade markdown)
        if raw_response.startswith("```"):
            raw_response = raw_response.split("```")[1]
            if raw_response.startswith("json"):
                raw_response = raw_response[4:]
        raw_response = raw_response.strip()
        
        result = json.loads(raw_response)
        
        # Validar y limitar sentiment_score entre -1.0 y 1.0
        sentiment = float(result.get("sentiment_score", 0))
        sentiment = max(-1.0, min(1.0, sentiment))
        
        # Extraer key_injuries como lista
        injuries = result.get("key_injuries", [])
        if isinstance(injuries, str):
            injuries = [injuries] if injuries else []
        
        return {
            "sentiment_score": sentiment,
            "key_injuries": injuries[:5],  # Máximo 5 lesiones
            "risk_analysis": str(result.get("risk_analysis", "Sin análisis"))[:200],
            # Compatibilidad con campos anteriores
            "impact_score": sentiment * 0.5,  # Convertir a escala anterior
            "key_factor": ", ".join(injuries) if injuries else "Sin lesiones",
            "reasoning": str(result.get("risk_analysis", "Sin análisis"))[:200]
        }
        
    except json.JSONDecodeError:
        return {
            "sentiment_score": 0.0,
            "key_injuries": [],
            "risk_analysis": "Error parseando respuesta IA",
            "impact_score": 0.0,
            "key_factor": "Error",
            "reasoning": raw_response[:150] if 'raw_response' in dir() else "Error"
        }
    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "rate" in error_str.lower():
            raise RateLimitError(f"Rate limit: {error_str}")
        return {
            "sentiment_score": 0.0,
            "key_injuries": [],
            "risk_analysis": f"Error: {error_str[:50]}",
            "impact_score": 0.0,
            "key_factor": "Error",
            "reasoning": "Error de análisis"
        }


def apply_ai_fusion(base_probability: float, sentiment_score: float) -> float:
    """
    MVP v1.0: Fórmula exacta de Weighted Voting.
    
    final_prob = base_prob + (sentiment_score * 0.10)
    
    - Las noticias pueden mover la aguja MÁXIMO un 10%
    - sentiment_score va de -1.0 a +1.0
    - Resultado limitado entre 0.0 y 1.0
    """
    # Convertir a decimal si viene en porcentaje
    if base_probability > 1:
        base_probability = base_probability / 100
    
    # FÓRMULA MVP: base_prob + (sentiment * 0.10)
    news_adjustment = sentiment_score * 0.10
    final_prob = base_probability + news_adjustment
    
    # CLIP: Limitar entre 0.0 y 1.0
    final_prob = max(0.0, min(1.0, final_prob))
    
    return round(final_prob * 100, 1)


# ===========================================
# WRAPPER ASYNC CON TIMEOUT
# ===========================================
async def analyze_single_prediction(pred: MatchPrediction, timeout: int = 8) -> MatchPrediction:
    """
    Analiza un partido con timeout para evitar bloqueos.
    
    Args:
        pred: Predicción a analizar
        timeout: Tiempo máximo en segundos (default: 8)
    
    Returns:
        Predicción actualizada con análisis de IA
    """
    import asyncio
    
    match_data = {
        "home_team": pred.home_team,
        "away_team": pred.away_team,
        "winner": pred.winner,
        "win_probability": pred.win_probability,
        "under_over": pred.under_over,
        "ou_line": pred.ou_line,
        "ou_probability": pred.ou_probability,
        # NUEVO: Añadir datos de discrepancia
        "warning_level": pred.warning_level,
        "market_odds_winner": pred.market_odds_home if pred.winner == pred.home_team else pred.market_odds_away,
        "implied_prob_market": pred.implied_prob_market,
        "market_odds_winner": pred.market_odds_home if pred.winner == pred.home_team else pred.market_odds_away,
        "implied_prob_market": pred.implied_prob_market,
        "discrepancy": pred.discrepancy,
        "game_status": pred.game_status,
        "home_score": pred.home_score,
        "away_score": pred.away_score
    }
    
    try:
        # Timeout de 8 segundos por partido
        analysis = await asyncio.wait_for(
            analyze_with_impact(match_data),
            timeout=timeout
        )
        
        # Aplicar fusión: modificar probabilidad según impacto de noticias
        original_prob = pred.win_probability
        adjusted_prob = apply_ai_fusion(original_prob, analysis["impact_score"])
        
        # Actualizar predicción
        pred.win_probability = adjusted_prob
        
        # Recalcular ganador si la fusión cambia el resultado
        if adjusted_prob < 50:
            pred.winner = pred.away_team if pred.winner == pred.home_team else pred.home_team
            pred.win_probability = round(100 - adjusted_prob, 1)
        
        # Construir análisis para mostrar (incluir warning si existe)
        impact_indicator = "📈" if analysis["impact_score"] > 0 else ("📉" if analysis["impact_score"] < 0 else "➡️")
        impact_change = f"{analysis['impact_score']:+.2f}" if analysis["impact_score"] != 0 else "0"
        
        warning_prefix = ""
        if pred.warning_level == "HIGH":
            warning_prefix = "⚠️ ALERTA: "
        elif pred.warning_level == "MEDIUM":
            warning_prefix = "⚡ "
        
        pred.ai_analysis = f"{warning_prefix}{impact_indicator} [{impact_change}] {analysis['key_factor']}: {analysis['reasoning']}"
        
        return pred
        
    except asyncio.TimeoutError:
        # Si tarda más de 8s, usar solo XGBoost
        pred.ai_analysis = "⏱️ Timeout: usando predicción base del modelo"
        return pred
    except Exception as e:
        pred.ai_analysis = f"⚠️ Error: {str(e)[:40]}"
        return pred


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
            print(f"[WARN] No se encontraron modelos en {MODEL_DIR}")
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
        print(f"[OK] Modelo cargado: {best_model.name} (Accuracy: {MODEL_ACCURACY})")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error cargando modelo: {e}")
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
    Obtiene los partidos de hoy usando script externo para evitar bloqueos.
    Devuelve lista de tuplas (home_team, away_team, ou_line)
    """
    print("⚡ [DEBUG] Iniciando búsqueda de partidos (subprocess)...")
    import subprocess
    import json
    import sys
    
    try:
        # Ruta al script
        script_path = BASE_DIR / "src" / "DataProviders" / "fetch_games.py"
        
        # Ejecutar como subprocess
        # sys.executable asegura que usamos el mismo intérprete python
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=20  # Timeout generoso
        )
        
        if result.returncode != 0:
            print(f"❌ [ERROR] Subprocess falló: {result.stderr}")
            return []
            
        odds_data = json.loads(result.stdout)
        
        games = []
        if not odds_data:
            print("⚠️ [WARN] SBR devolvió un diccionario vacío.")
        
        for game_key, game_info in odds_data.items():
            try:
                # game_key es "Home:Away"
                parts = game_key.split(":")
                if len(parts) != 2:
                    print(f"⚠️ [WARN] Formato de llave inválido: {game_key}")
                    continue
                    
                home_team, away_team = parts
                ou_line = game_info.get("under_over_odds")
                
                # Convertir a float si es posible, o usar default
                try:
                    ou_line_val = float(ou_line) if ou_line else 220.0
                except:
                    ou_line_val = 220.0

                games.append({
                    "home_team": home_team,
                    "away_team": away_team,
                    "ou_line": ou_line_val,
                    "home_odds": game_info.get(home_team, {}).get("money_line_odds"),
                    "away_odds": game_info.get(away_team, {}).get("money_line_odds"),
                    "game_status": game_info.get("status"),
                    "home_score": game_info.get("home_score"),
                    "away_score": game_info.get("away_score"),
                })
            except Exception as e_inner:
                print(f"⚠️ [WARN] Error procesando partido {game_key}: {e_inner}")

        print(f"✅ [OK] SBR: Encontrados {len(games)} partidos reales NBA de hoy.")
        return games
        
    except subprocess.TimeoutExpired:
        print("❌ [ERROR] Timeout ejecutando fetch_games.py")
        return []
    except Exception as e:
        print(f"❌ [ERROR] Error CRÍTICO obteniendo partidos SBR: {e}")
        import traceback
        traceback.print_exc()
        return []


# ===========================================
# PREDICCIÓN CON XGBOOST
# ===========================================
# ===========================================
# CÁLCULOS FINANCIEROS OPTIMIZADOS
# ===========================================
def calculate_expected_value(prob_pct: float, american_odds: int) -> float:
    """Calcula el EV% de una apuesta"""
    if not american_odds:
        return 0.0
        
    decimal_odds = american_to_decimal(american_odds)
    prob_decimal = prob_pct / 100
    
    # EV = (Prob * Cuota) - 1
    ev = (prob_decimal * decimal_odds) - 1
    return round(ev * 100, 2)


def calculate_dynamic_kelly(prob_pct: float, american_odds: int, safety_factor: float = 0.25) -> float:
    """
    Criterio de Kelly Dinámico:
    - Cuotas altas (>= 1.90): Kelly / 3 (Más agresivo, buscamos valor)
    - Cuotas bajas (< 1.90): Kelly / 4 (Conservador, protegemos bankroll)
    """
    if not american_odds:
        return 0.0
        
    decimal_odds = american_to_decimal(american_odds)
    prob_decimal = prob_pct / 100
    
    # Kelly Base = (bp - q) / b
    # b = decimal_odds - 1
    # p = prob_decimal
    # q = 1 - p
    
    b = decimal_odds - 1
    q = 1 - prob_decimal
    
    kelly_fraction = (b * prob_decimal - q) / b
    
    # Ajuste Dinámico
    if decimal_odds >= 1.90:
        adjusted_safety = 0.33  # Kelly / 3
    else:
        adjusted_safety = 0.25  # Kelly / 4
        
    # Aplicar safety factor adicional si hay riesgo ALTO
    final_safety = min(adjusted_safety, safety_factor)
        
    kelly_stake = kelly_fraction * final_safety
    
    # Limitar entre 0% y 5% (hard limit de seguridad)
    return round(max(0.0, min(0.05, kelly_stake)) * 100, 2)


# ===========================================
# PREDICCIÓN CON XGBOOST (FIXED - Uses real model now)
# ===========================================
def predict_with_xgboost(games: list) -> list[MatchPrediction]:
    """
    Ejecuta predicciones con XGBoost REAL usando prediction_api.
    - Usa el modelo entrenado (68.9% accuracy)
    - Extrae features reales de TeamData.sqlite
    - Cuotas siguen siendo mock (marcadas claramente)
    """
    from prediction_api import predict_game as real_predict
    
    predictions = []
    
    for game in games:
        home_team = game["home_team"]
        away_team = game["away_team"]
        ou_line = game.get("ou_line", 220.0)
        
        # Use the REAL XGBoost prediction
        result = real_predict(home_team, away_team, ou_line if ou_line else 220.0)
        
        is_mock = result.get("is_mock", True)
        winner = result.get("winner", home_team)
        winner_is_home = (winner == home_team)
        win_prob = result.get("win_probability", 55.0)
        under_over = result.get("under_over", "OVER")
        ou_prob = result.get("ou_probability", 52.0)
        
        # Obtener cuotas MOCK (claramente marcadas)
        odds_data = fetch_market_odds(home_team, away_team)
        winner_odds = odds_data["home_odds"] if winner_is_home else odds_data["away_odds"]
        decimal_odds = american_to_decimal(winner_odds) if winner_odds else 1.0
        
        # Calcular Discrepancia y EV
        discrepancy_info = calculate_discrepancy_analysis(win_prob, winner_odds, winner_is_home)
        ev_value = calculate_expected_value(win_prob, winner_odds)
        
        # ===========================================
        # LÓGICA DE FILTRADO Y DECISIÓN
        # ===========================================
        status = "BET"
        risk_level = "NORMAL"
        value_type = "NORMAL"
        
        # 1. Filtro de Cuota Mínima
        if decimal_odds < 1.55 and decimal_odds > 1.0:
            status = "DO_NOT_BET"
            risk_level = "LOW_ODDS"
        
        # 2. Kill Switch (Discrepancia > 20%)
        if discrepancy_info["discrepancy"] and discrepancy_info["discrepancy"] > 20:
            status = "DO_NOT_BET"
            risk_level = "EXTREME"
            
        # 3. Filtro Min EV
        if ev_value < 2.0:
            if status == "BET":
                status = "DO_NOT_BET"
                risk_level = "LOW_VALUE"
        
        # 4. Golden Opportunity (Underdog Ganador)
        if status == "BET" and decimal_odds >= 2.00:
            value_type = "GOLDEN_OPPORTUNITY"
            
        # Calcular Kelly
        safety = 0.5 if discrepancy_info["warning_level"] == "HIGH" else 1.0
        kelly_stake = calculate_dynamic_kelly(win_prob, winner_odds, safety_factor=safety)
        
        if status == "DO_NOT_BET":
            kelly_stake = 0.0
            is_value_bet = False
        else:
            is_value_bet = True
            
        # Build analysis string
        ai_analysis = None
        if result.get("error"):
            ai_analysis = f"[WARN] {result['error']}"
        elif not is_mock:
            ai_analysis = f"[XGBoost {result.get('model_accuracy', 'N/A')}] Prediccion basada en estadisticas reales de equipos"
        else:
            ai_analysis = "[MOCK] Sin datos de equipos disponibles"
            
        predictions.append(MatchPrediction(
            home_team=home_team,
            away_team=away_team,
            winner=winner,
            win_probability=win_prob,
            under_over=under_over,
            ou_line=ou_line,
            ou_probability=ou_prob,
            ai_analysis=ai_analysis,
            is_mock=is_mock,
            market_odds_home=odds_data["home_odds"],
            market_odds_away=odds_data["away_odds"],
            implied_prob_market=discrepancy_info["implied_prob"],
            discrepancy=discrepancy_info["discrepancy"],
            warning_level=discrepancy_info["warning_level"],
            ev_value=ev_value,
            is_value_bet=is_value_bet,
            kelly_stake_pct=kelly_stake,
            risk_level=risk_level,
            status=status,
            value_type=value_type,
            sentiment_score=None,
            key_injuries=None,
            risk_analysis=None
        ))
    
    return predictions


# ===========================================
# FASTAPI APP
# ===========================================
app = FastAPI(
    title="🏀 NBA Predictor AI",
    description="API de predicciones NBA usando XGBoost + Groq LLM",
    version="1.0.0"
)

# ===========================================
# SECURITY: CORS Configuration
# ===========================================
# Dominios permitidos (agregar tu dominio en produccion)
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "https://bet-7b8l.onrender.com",  # Producción en Render
    # Agregar aqui tu dominio de produccion, ej:
    # "https://tu-app.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Global cache for today's games
TODAYS_GAMES_CACHE = []
GAMES_CACHE_DATE = None

def refresh_games_cache():
    """Pre-load games from SBR (run synchronously on startup)"""
    global TODAYS_GAMES_CACHE, GAMES_CACHE_DATE
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    
    print("[INFO] Loading today's NBA games from SBR...")
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
        
        TODAYS_GAMES_CACHE = games
        GAMES_CACHE_DATE = today
        print(f"[OK] Loaded {len(games)} real NBA games for {today}")
        return games
    except Exception as e:
        print(f"[WARN] Could not load games from SBR: {e}")
        TODAYS_GAMES_CACHE = []
        return []


# ===========================================
# BACKGROUND JOB: Auto-update pending predictions
# ===========================================
def run_pending_updates():
    """
    Background job that runs every 30 minutes.
    Updates pending predictions with real scores from SBR.
    """
    global LAST_UPDATE_TIME, UPDATE_RESULTS
    from datetime import datetime
    
    print("[SCHEDULER] Running automatic pending predictions update...")
    
    try:
        from src.Services.history_service import update_pending_predictions
        result = update_pending_predictions()
        LAST_UPDATE_TIME = datetime.now().isoformat()
        UPDATE_RESULTS.append({
            "timestamp": LAST_UPDATE_TIME,
            "result": result
        })
        # Keep only last 10 results
        if len(UPDATE_RESULTS) > 10:
            UPDATE_RESULTS = UPDATE_RESULTS[-10:]
        print(f"[SCHEDULER] Update complete: {result}")
    except Exception as e:
        print(f"[SCHEDULER] Error in background update: {e}")
        LAST_UPDATE_TIME = datetime.now().isoformat()
        UPDATE_RESULTS.append({
            "timestamp": LAST_UPDATE_TIME,
            "result": {"status": "error", "message": str(e)}
        })


@app.on_event("startup")
async def startup_event():
    """Cargar modelos al iniciar la API"""
    from prediction_api import load_models
    load_models()
    
    # Pre-cargar partidos de hoy
    refresh_games_cache()
    
    # Inicializar base de datos de historial
    from history_db import init_history_db
    init_history_db()
    
    # Iniciar scheduler para actualización automática de scores
    # Ejecuta cada 15 minutos para actualizar partidos finalizados
    scheduler.add_job(
        run_pending_updates,
        IntervalTrigger(minutes=15),
        id='update_pending_predictions',
        name='Auto-update pending predictions',
        replace_existing=True
    )
    scheduler.start()
    print("[SCHEDULER] Background scheduler started - Updates every 15 minutes")
    
    # Ejecutar una vez al inicio (después de 5 segundos para dar tiempo a cargar todo)
    import asyncio
    await asyncio.sleep(5)
    run_pending_updates()


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler gracefully"""
    if scheduler.running:
        scheduler.shutdown()
        print("[SCHEDULER] Background scheduler stopped")


@app.get("/")
async def serve_index():
    """Sirve el dashboard como página principal"""
    index_path = BASE_DIR / "static" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    # Fallback al health check si no hay frontend
    return {
        "status": "online",
        "service": "NBA Predictor AI",
        "message": "Frontend no encontrado. Usa /predict-today para la API."
    }


@app.get("/api/health")
async def health_check():
    """Health check para monitoreo"""
    return {
        "status": "online",
        "service": "NBA Predictor AI",
        "model_loaded": MODEL_LOADED,
        "model_accuracy": MODEL_ACCURACY,
        "groq_configured": bool(GROQ_API_KEY)
    }


@app.get("/predict-today", response_model=PredictionResponse)
async def predict_today(include_ai: bool = True):
    """
    Obtiene predicciones para los partidos de hoy.
    OPTIMIZADO: Lee del historial si ya existen (Load Once).
    """
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Intentar leer del historial (CACHE HIT)
    from history_db import get_predictions_by_date, save_prediction
    
    cached_preds = get_predictions_by_date(today)
    print(f"DEBUG: Read-Through Cache Check for DATE='{today}'. Found: {len(cached_preds) if cached_preds else 0}")
    
    if cached_preds and len(cached_preds) > 0:
        # Convertir diccionarios a MatchPrediction objects
        pred_objects = []
        for p in cached_preds:
            # Reconstruct basic MatchPrediction (AI analysis might be generic if not saved textually, 
            # but usually we want to preserve AI insights. For now MVP stores basic data and re-runs AI? 
            # No, user wants FAST load. We should assume data in DB is sufficient.
            # Warning: DB schema doesn't store 'ai_analysis' text string currently in save_prediction.
            # We will return basic data which is fast.
            
            # Simple conversion
            try:
                mp = MatchPrediction(
                    home_team=p['home_team'],
                    away_team=p['away_team'],
                    winner=p['winner'],
                    win_probability=p['win_probability'],
                    market_odds_home=p.get('market_odds_home', 0),
                    market_odds_away=p.get('market_odds_away', 0),
                    ev_value=p['ev_value'],
                    kelly_stake_pct=p['kelly_stake_pct'],
                    warning_level=p['warning_level'],
                    
                    # Campos default/calculados
                    under_over="N/A",  # Fixed: str, not float
                    ou_line=0.0,
                    ou_probability=50.0,
                    # predicted_score_home removed (not in schema)
                    # predicted_score_away removed (not in schema)
                    implied_prob_market=0.0,
                    discrepancy=0.0,
                    ai_analysis="✅ Cargado del historial (Guardado previamente)", 
                    game_status=p.get('result', 'PENDIENTE'),
                    home_score=0,
                    away_score=0
                )
                pred_objects.append(mp)
            except Exception as ex:
                print(f"DEBUG: Error converting cached pred for {p.get('match_id')}: {ex}")

        if len(pred_objects) > 0:
            return PredictionResponse(
                date=today,
                total_games=len(pred_objects),
                predictions=pred_objects,
                model_accuracy=MODEL_ACCURACY,
                status="✅ Cargado del Historial (Optimizado)"
            )

    # 2. Si no hay cache, generar (CACHE MISS)
    try:
        if not MODEL_LOADED:
            load_xgboost_models()
        
        games = get_todays_games_from_sbr()
        
        if not games or not MODEL_LOADED:
            predictions = get_mock_predictions()
            return PredictionResponse(
                date=today,
                total_games=len(predictions),
                predictions=predictions,
                model_accuracy="N/A (Mock Data)",
                status="⚠️ Usando datos simulados"
            )
        
        predictions = predict_with_xgboost(games)
        
        if include_ai and groq_client:
            import asyncio
            tasks = [analyze_single_prediction(pred) for pred in predictions]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if not isinstance(result, Exception):
                    predictions[i] = result
        
        # 3. GUARDAR en Historial (Write-Through)
        try:
            for pred in predictions:
                save_prediction({
                    'date': today,
                    'match_id': f"{pred.home_team} vs {pred.away_team}",
                    'home_team': pred.home_team,
                    'away_team': pred.away_team,
                    'winner': pred.winner,
                    'win_probability': pred.win_probability,
                    'market_odds': pred.market_odds_home if pred.winner == pred.home_team else pred.market_odds_away,
                    'ev_value': pred.ev_value,
                    'kelly_stake_pct': pred.kelly_stake_pct,
                    'warning_level': pred.warning_level
                })
        except Exception as e:
            print(f"Error auto-saving predictions: {e}")

        response = PredictionResponse(
            date=today,
            total_games=len(predictions),
            predictions=predictions,
            model_accuracy=MODEL_ACCURACY,
            status="✅ Predicciones Generadas y Guardadas"
        )
        return response

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] Critical error in predict_today: {e}")
        # SECURITY: No exponer detalles del error al cliente
        return PredictionResponse(
            date=today,
            total_games=0,
            predictions=[],
            model_accuracy="ERROR",
            status="❌ Error interno del servidor. Intente nuevamente más tarde."
        )


@app.get("/teams")
async def list_teams():
    """Lista todos los equipos NBA soportados"""
    from src.Utils.Dictionaries import team_index_current
    return {
        "total": len(set(team_index_current.values())),
        "teams": list(team_index_current.keys())
    }


@app.get("/pronosticos-hoy", response_model=PredictionResponse)
async def pronosticos_hoy(include_ai: bool = True):
    """Alias en español de /predict-today para el frontend"""
    return await predict_today(include_ai)


@app.post("/save-predictions")
async def save_daily_predictions():
    """Guarda las predicciones del día en BD"""
    from history_db import save_prediction
    from datetime import datetime
    
    # Obtener predicciones actuales
    response = await predict_today(include_ai=False)
    predictions = response.predictions
    
    saved_count = 0
    for pred in predictions:
        try:
            save_prediction({
                'date': datetime.now().strftime("%Y-%m-%d"),
                'match_id': f"{pred.home_team} vs {pred.away_team}",
                'home_team': pred.home_team,
                'away_team': pred.away_team,
                'winner': pred.winner,
                'win_probability': pred.win_probability,
                'market_odds': pred.market_odds_home if pred.winner == pred.home_team else pred.market_odds_away,
                'ev_value': pred.ev_value,
                'kelly_stake_pct': pred.kelly_stake_pct,
                'warning_level': pred.warning_level
            })
            saved_count += 1
        except Exception as e:
            print(f"Error saving prediction: {e}")
    
    return {"status": "saved", "count": saved_count}


@app.post("/update-history")
async def update_history_endpoint(date: str, results: dict):
    """
    Actualiza resultados reales del día especificado.
    
    Body example:
    {
        "date": "2026-01-21",
        "results": {
            "Lakers vs Celtics": "Celtics",
            "Warriors vs Suns": "Warriors"
        }
    }
    """
    from history_db import update_results
    
    update_results(date, results)
    return {"status": "updated", "date": date, "matches": len(results)}




@app.get("/history")
async def get_history_endpoint(days: int = 7):
    """Obtiene historial de predicciones"""
    # from history_db import get_history
    import history_db
    return {"predictions": history_db.get_history(days)}


# ===========================================
# SCHEDULER ENDPOINTS: Manual trigger and status
# ===========================================
@app.get("/api/update-pending")
async def trigger_update_pending():
    """
    Fuerza la actualización de predicciones pendientes.
    Ejecuta manualmente lo que el scheduler hace automáticamente.
    """
    run_pending_updates()
    return {
        "status": "completed",
        "last_update": LAST_UPDATE_TIME,
        "message": "Actualización de predicciones pendientes activada manualmente"
    }


@app.get("/api/scheduler-status")
async def get_scheduler_status():
    """
    Muestra el estado del scheduler y las últimas actualizaciones.
    Útil para monitoreo y debugging.
    """
    jobs = []
    if scheduler.running:
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            })
    
    return {
        "scheduler_running": scheduler.running,
        "jobs": jobs,
        "last_update_time": LAST_UPDATE_TIME,
        "recent_updates": UPDATE_RESULTS[-5:] if UPDATE_RESULTS else []
    }


# ===========================================
# MVP v1.0: ENDPOINT DE DEBUGGING - SOLO EN MODO DESARROLLO
# ===========================================
# SECURITY: Este endpoint solo funciona si DEBUG_MODE=true en variables de entorno
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

@app.get("/debug/simulate-match")
async def debug_simulate_match(home: str, away: str):
    """
    ONLY AVAILABLE IN DEBUG MODE.
    Set DEBUG_MODE=true environment variable to enable.
    """
    if not DEBUG_MODE:
        raise HTTPException(
            status_code=403,
            detail="Debug endpoint disabled in production. Set DEBUG_MODE=true to enable."
        )
    """
    MVP v1.0: Simula el pipeline completo para UN partido y devuelve trace detallado.
    
    Uso: GET /debug/simulate-match?home=Lakers&away=Celtics
    
    Devuelve cada paso del proceso de decisión para auditoría completa.
    """
    trace = {
        "match": f"{home} vs {away}",
        "timestamp": datetime.now().isoformat(),
        "steps": {}
    }
    
    try:
        # PASO 1: Simulación XGBoost
        np.random.seed(hash(home + away) % 2**32)
        home_prob = 0.45 + np.random.random() * 0.2
        winner_is_home = home_prob > 0.5
        xgboost_raw = round(max(home_prob, 1 - home_prob), 4)
        
        trace["steps"]["1_xgboost_raw"] = xgboost_raw
        
        # PASO 2: Búsqueda de noticias
        news_result = await search_news_async(home, away)
        
        if news_result is None:
            trace["steps"]["2_news_found"] = []
            trace["steps"]["2_news_status"] = "NO_NEWS_FOUND (búsqueda falló o vacía)"
        else:
            # Extraer keywords de lesiones
            injuries = []
            keywords = ["out", "questionable", "GTD", "injury", "injured", "doubtful"]
            for line in news_result.split("\n"):
                for kw in keywords:
                    if kw.lower() in line.lower():
                        injuries.append(line[:80] + "...")
                        break
            trace["steps"]["2_news_found"] = injuries[:5]
            trace["steps"]["2_news_status"] = f"Encontradas {len(news_result.split(chr(10)))} noticias"
        
        # PASO 3: Análisis IA
        match_data_for_ai = {
            "home_team": home,
            "away_team": away,
            "winner": home if winner_is_home else away,
            "win_probability": round(xgboost_raw * 100, 1),
            "warning_level": "NORMAL"
        }
        
        ai_result = await analyze_with_impact(match_data_for_ai)
        trace["steps"]["3_ai_raw_response"] = ai_result
        
        # PASO 4: Ajuste por IA
        sentiment_score = ai_result.get("sentiment_score", 0)
        news_adjustment = sentiment_score * 0.10
        trace["steps"]["4_ai_adjustment_value"] = round(news_adjustment, 4)
        
        # PASO 5: Cuotas implícitas (simuladas)
        odds_data = fetch_market_odds(home, away)
        winner_odds = odds_data["home_odds"] if winner_is_home else odds_data["away_odds"]
        
        # Convertir cuota americana a probabilidad implícita
        if winner_odds and winner_odds != 0:
            if winner_odds > 0:
                implied_prob = 100 / (winner_odds + 100)
            else:
                implied_prob = abs(winner_odds) / (abs(winner_odds) + 100)
        else:
            implied_prob = 0.5
            
        trace["steps"]["5_odds_implied_prob"] = round(implied_prob, 4)
        trace["steps"]["5_market_odds_raw"] = winner_odds
        
        # PASO 6: Decisión final
        final_prob = xgboost_raw + news_adjustment
        final_prob = max(0.0, min(1.0, final_prob))
        
        # Calcular EV
        if winner_odds:
            if winner_odds > 0:
                decimal_odds = (winner_odds / 100) + 1
            else:
                decimal_odds = (100 / abs(winner_odds)) + 1
            ev = (final_prob * decimal_odds) - 1
        else:
            decimal_odds = 2.0
            ev = 0
        
        # Discrepancia
        discrepancy = abs(final_prob - implied_prob)
        
        # Decisión del Kill Switch
        if discrepancy > 0.20:
            action = "DO_NOT_BET (Discrepancia > 20%)"
            risk = "EXTREME"
        elif ev < 0:
            action = "NO BET (EV Negativo)"
            risk = "HIGH"
        else:
            action = "BET" if ev > 0.05 else "CAUTION (EV bajo)"
            risk = "NORMAL" if ev > 0.05 else "MEDIUM"
        
        trace["steps"]["6_final_decision"] = {
            "prob_final": round(final_prob * 100, 2),
            "discrepancy_pct": round(discrepancy * 100, 2),
            "ev_pct": round(ev * 100, 2),
            "risk_level": risk,
            "action": action
        }
        
        return trace
        
    except Exception as e:
        trace["error"] = str(e)
        return trace


# Servir archivos estáticos (frontend)
static_path = BASE_DIR / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/dashboard")
async def serve_dashboard():
    """Sirve el dashboard HTML"""
    index_path = BASE_DIR / "static" / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Dashboard no encontrado")




@app.get("/history/full")
async def get_full_history(days: int = 30):
    """Devuelve historial detallado linea por linea (History DB)"""
    import history_db
    history = history_db.get_history(days)
    return {
        "history": history
    }


@app.get("/match-details/{home_team}/{away_team}")
async def get_match_details(home_team: str, away_team: str):
    """
    Devuelve detalles completos de un partido:
    - Precisión de predicción por equipo
    - Últimos resultados de cada equipo
    - Análisis IA (si disponible)
    """
    import history_db
    home_accuracy = history_db.get_team_prediction_accuracy(home_team)
    away_accuracy = history_db.get_team_prediction_accuracy(away_team)
    
    home_form = history_db.get_team_recent_results(home_team, 5)
    away_form = history_db.get_team_recent_results(away_team, 5)
    
    # Generate AI analysis for this matchup
    ai_analysis = None
    if groq_client:
        try:
            prompt = f"""Analiza brevemente el partido entre {home_team} (local) y {away_team} (visitante).
            Incluye:
            1. Fortalezas y debilidades de cada equipo
            2. Factores clave del partido
            3. Predicción general
            Sé conciso (máximo 150 palabras)."""
            
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.7
            )
            ai_analysis = response.choices[0].message.content
        except Exception as e:
            print(f"[WARN] AI analysis failed: {e}")
            ai_analysis = "Análisis no disponible en este momento."
    
    return {
        "home_team": home_team,
        "away_team": away_team,
        "home_accuracy": home_accuracy,
        "away_accuracy": away_accuracy,
        "home_form": home_form,
        "away_form": away_form,
        "ai_analysis": ai_analysis
    }


if __name__ == "__main__":
    import uvicorn
    # Inicializar base de datos de historial
    import history_db
    history_db.init_history_db()
    
    # HACK: Registrar BoosterWrapper para joblib
    sys.modules['__main__'].BoosterWrapper = BoosterWrapper
    
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
# ===========================================
# FOOTBALL INTEGRATION (Branch: football-mode)
# ===========================================
import football_api

class FootballMatchPrediction(BaseModel):
    date: str
    league: str
    match_id: str
    home_team: str
    away_team: str
    prediction: str # '1', 'X', '2' or Team Name
    prob_home: float
    prob_draw: float
    prob_away: float
    odd_home: Optional[float] = None
    odd_draw: Optional[float] = None
    odd_away: Optional[float] = None
    status: str = "PENDING"
    
@app.get("/predict-football", response_model=list[FootballMatchPrediction])
async def predict_football(league: Optional[str] = None):
    """
    Obtiene predicciones de fútbol para el día actual.
    """
    # 1. Obtener fixtures
    fixtures = football_api.football_api.get_fixtures()
    
    # Mock data for MVP if no fixtures found (or scraper failed)
    if not fixtures:
        # Mocking a few games for UI testing
        mock_games = [
            {"home": "Manchester City", "away": "Liverpool", "league": "ENG-Premier League"},
            {"home": "Real Madrid", "away": "Barcelona", "league": "ESP-La Liga"},
            {"home": "Juventus", "away": "AC Milan", "league": "ITA-Serie A"}
        ]
        
        predictions = []
        for game in mock_games:
            if league and league not in game['league']:
                continue
                
            pred = football_api.football_api.predict_match(game['home'], game['away'], game['league'])
            
            # Create Pydantic model
            f_pred = FootballMatchPrediction(
                date=datetime.now().strftime("%Y-%m-%d"),
                league=game['league'],
                match_id=f"{game['home']} vs {game['away']}",
                home_team=game['home'],
                away_team=game['away'],
                prediction=pred['prediction'],
                prob_home=pred['probs']['home'],
                prob_draw=pred['probs']['draw'],
                prob_away=pred['probs']['away'],
                odd_home=2.1,
                odd_draw=3.4,
                odd_away=3.2,
                status="PENDING"
            )
            
            # Save to DB
            history_db.save_football_prediction(f_pred.dict())
            predictions.append(f_pred)
            
        return predictions

    return []

@app.get("/history/football")
async def get_football_history_endpoint(limit: int = 50):
    return {"history": history_db.get_football_history(limit)}
