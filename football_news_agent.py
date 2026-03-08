"""
Football News Research Agent - Premier League (DeepSeek + DuckDuckGo).
Busca noticias para partidos de la Premier League para mejorar la precisión del modelo Poisson.
"""
import asyncio
import json
import os
import time
import logging

import history_db

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
DEEPSEEK_MODEL = "deepseek-chat"
THROTTLE_SECONDS = 8.0
MAX_RETRIES = 3
SEARCH_RESULTS = 6
MAX_CONTEXT_CHARS = 1800

def _get_ddgs():
    try:
        from ddgs import DDGS
        return DDGS
    except ImportError:
        pass
    try:
        from duckduckgo_search import DDGS
        return DDGS
    except ImportError:
        return None

def _search_web(home_team: str, away_team: str, date_str: str) -> str:
    """Busca noticias específicas de la Premier League."""
    DDGS = _get_ddgs()
    if DDGS is None:
        return "Sin resultados (ddgs no instalado)."
    
    # Query optimizada para Premier League
    query = f"Premier League {home_team} vs {away_team} news injuries lineups {date_str}"
    try:
        snippets = []
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=SEARCH_RESULTS))
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            s = f"{title}: {body[:180]}" if body else title
            if s.strip():
                snippets.append(s)
        text = "\n".join(snippets[:6])
        return text[:MAX_CONTEXT_CHARS] if len(text) > MAX_CONTEXT_CHARS else text or "Sin resultados."
    except Exception as e:
        logger.error(f"Error en búsqueda web futbol: {e}")
        return f"Sin resultados (error búsqueda: {type(e).__name__})"

def _build_prompt(home_team: str, away_team: str, date_str: str, web_context: str) -> str:
    """Prompt especializado en fútbol inglés."""
    return f"""Partido Premier League: {home_team} vs {away_team}
Fecha: {date_str}

CONTEXTO WEB RECIENTE:
{web_context}

INSTRUCCIONES PROFESIONALES:
1. Analiza noticias reales de la Premier League para hoy ({date_str}).
2. Identifica bajas críticas (ej. Haaland, Salah, De Bruyne) o regresos importantes.
3. 'headline': Título conciso y profesional en español.
4. 'injuries': Jugadores clave lesionados o en duda.
   - 'status': "Baja", "Dudoso" o "Probable".
5. 'impact_assessment': Cómo afectan estas bajas al resultado esperado (ej. "Sin su goleador estrella, el {home_team} perderá mucha pegada").
6. 'confidence_modifier': 
   - "higher" si las noticias favorecen fuertemente al favorito del modelo.
   - "lower" si hay bajas críticas en el favorito que el modelo Poisson de datos históricos NO conoce.
   - "neutral" si no hay noticias que cambien significativamente el panorama.

Responde SOLO JSON:
{{
  "headline": "...",
  "key_points": ["...", "..."],
  "injuries": [{{"player": "Nombre", "team": "...", "status": "Baja|Dudoso|Probable"}}],
  "impact_assessment": "...",
  "confidence_modifier": "higher|neutral|lower"
}}
Español elegante. Si no hay noticias, usa 'Sin novedades relevantes' y injuries []."""

def _parse_response(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        first_nl = text.find("\n")
        last_fence = text.rfind("```")
        if first_nl != -1 and last_fence != -1:
            text = text[first_nl + 1:last_fence].strip()
    try:
        data = json.loads(text)
        # Limpieza básica de lesiones
        clean_injuries = []
        for inj in data.get("injuries", []):
            p_name = str(inj.get("player") or "")
            if len(p_name) > 2 and len(p_name) < 50 and "disponible" not in p_name.lower():
                clean_injuries.append(inj)
        data["injuries"] = clean_injuries
        return data
    except Exception:
        return {
            "headline": "Sin novedades destacadas",
            "key_points": ["No se detectaron noticias críticas de último minuto."],
            "injuries": [],
            "impact_assessment": "Modelo basado en estadísticas históricas sin modificaciones externas.",
            "confidence_modifier": "neutral"
        }

def _fetch_news(home_team: str, away_team: str, date_str: str) -> dict:
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY no configurada.")
    from openai import OpenAI
    web_context = _search_web(home_team, away_team, date_str)
    prompt = _build_prompt(home_team, away_team, date_str, web_context)
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return _parse_response(response.choices[0].message.content)
        except Exception as e:
            if attempt == MAX_RETRIES - 1: raise
            time.sleep(3 * (attempt + 1))
    return _parse_response("")

async def fetch_football_news(date_str: str, matches: list[dict]) -> list[dict]:
    """Busca noticias para partidos de fútbol para mejorar el modelo Poisson."""
    if not DEEPSEEK_API_KEY:
        logger.warning("[FOOTBALL-NEWS] DEEPSEEK_API_KEY no configurada.")
        return []

    results = []
    for match in matches:
        home = match.get("home_team", "")
        away = match.get("away_team", "")
        match_id = match.get("match_id")
        
        try:
            logger.info(f"[FOOTBALL-NEWS] Buscando: {home} vs {away}...")
            news = await asyncio.to_thread(_fetch_news, home, away, date_str)
            
            # Guardar en DB (usando sport='football')
            history_db.save_match_news(date_str, match_id, {**news, "sport": "football"})
            results.append({"match_id": match_id, **news})
        except Exception as e:
            logger.error(f"[FOOTBALL-NEWS] Error en {home} vs {away}: {e}")
            
    return results
