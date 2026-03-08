"""
NBA News Research Agent - DeepSeek + DuckDuckGo.
Solo busca noticias para partidos NBA. El sistema de fútbol no incluye noticias aún.
"""
import asyncio
import json
import os
import time

import history_db

DEEPSEEK_API_KEY = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
DEEPSEEK_MODEL = "deepseek-chat"
THROTTLE_SECONDS = 8.0
MAX_RETRIES = 3
SEARCH_RESULTS = 6
MAX_CONTEXT_CHARS = 1600


def _get_ddgs():
    """Obtiene la clase DDGS compatible con las versiones v5-v8 del paquete.
    El paquete fue renombrado de 'duckduckgo_search' a 'ddgs' en v8.
    """
    try:
        # Nuevo nombre del paquete (ddgs >= 8.x)
        from ddgs import DDGS
        return DDGS
    except ImportError:
        pass
    try:
        # Nombre antiguo (duckduckgo_search < 8.x)
        from duckduckgo_search import DDGS
        return DDGS
    except ImportError:
        return None


def _search_web(home_team: str, away_team: str, date_str: str) -> str:
    """Búsqueda web con DuckDuckGo."""
    DDGS = _get_ddgs()
    if DDGS is None:
        return "Sin resultados (duckduckgo_search / ddgs no instalado)."
    year = time.strftime("%Y")
    query = f"NBA {home_team} vs {away_team} news injuries {date_str}"
    try:
        snippets = []
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=SEARCH_RESULTS))
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            s = f"{title}: {body[:160]}" if body else title
            if s.strip():
                snippets.append(s)
        text = "\n".join(snippets[:6])
        return text[:MAX_CONTEXT_CHARS] if len(text) > MAX_CONTEXT_CHARS else text or "Sin resultados."
    except Exception as e:
        return f"Sin resultados (error búsqueda: {type(e).__name__})"


def _build_prompt(home_team: str, away_team: str, date_str: str, web_context: str) -> str:
    """Prompt refinado para calidad profesional."""
    return f"""Partido NBA: {home_team} vs {away_team}
Fecha: {date_str}

CONTEXTO WEB:
{web_context}

INSTRUCCIONES:
1. Analiza si hay noticias REALES de HOY ({date_str}) o muy recientes.
2. 'injuries': Lista jugadores lesionados o en duda. 
   - 'status': DEBE ser "Baja", "Dudoso" o "Probable" (usa estos términos exactos).
   - IMPORTANTE: Si NO hay nombres específicos de jugadores en el contexto, deja la lista VACÍA []. 
   - Prohibido usar "Información no disponible" como nombre de jugador.
3. 'headline': Título profesional.
4. 'impact_assessment': Análisis táctico de las bajas o contexto.
5. 'key_points': 2-3 puntos clave del encuentro.

Responde SOLO JSON:
{{
  "headline": "...",
  "key_points": ["...", "..."],
  "injuries": [{{"player": "Nombre Real", "team": "...", "status": "Baja|Dudoso|Probable"}}],
  "impact_assessment": "...",
  "confidence_modifier": "higher|neutral|lower"
}}
Español. Si no hay noticias relevantes, 'headline' debe decir 'Sin novedades destacadas' y 'injuries' []."""


def _parse_response(content: str) -> dict:
    """Extrae JSON de la respuesta, maneja markdown."""
    text = content.strip()
    if text.startswith("```"):
        first_nl = text.index("\n")
        last_fence = text.rfind("```")
        text = text[first_nl + 1:last_fence].strip()
    try:
        data = json.loads(text)
        # Post-procesamiento: mapear estados y limpiar genéricos
        status_map = {
            "out": "Baja", "q": "Dudoso", "questionable": "Dudoso",
            "p": "Probable", "probable": "Probable", "confirmed": "Confirmado"
        }
        clean_injuries = []
        for inj in data.get("injuries", []):
            p_name = str(inj.get("player") or "")
            # Si el nombre es genérico o muy largo (placeholder), ignorar
            if any(x in p_name.lower() for x in ["not disponible", "no disponible", "información", "específica", "contexto", "..."]):
                continue
            if len(p_name) < 3 or len(p_name) > 40:
                continue
            
            # Limpiar estado
            st = str(inj.get("status") or "").lower()
            if "out" in st or "baja" in st: inj["status"] = "Baja"
            elif "q" in st or "duda" in st or "dudoso" in st: inj["status"] = "Dudoso"
            elif "p" in st or "prob" in st: inj["status"] = "Probable"
            elif "confirm" in st: inj["status"] = "Confirmado"
            else: inj["status"] = st.capitalize() if st else "Dudoso"
            clean_injuries.append(inj)
        
        data["injuries"] = clean_injuries
        return data
    except json.JSONDecodeError:
        return {
            "headline": "No se pudo procesar",
            "key_points": [text[:250]],
            "injuries": [],
            "impact_assessment": text[:400],
            "confidence_modifier": "neutral",
        }


def _fetch_news(home_team: str, away_team: str, date_str: str) -> dict:
    """Obtiene noticias para un partido usando DeepSeek."""
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY no configurada. Añádela en GitHub Secrets o .env")
    from openai import OpenAI
    web_context = _search_web(home_team, away_team, date_str)
    prompt = _build_prompt(home_team, away_team, date_str, web_context)
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024,
            )
            return _parse_response(response.choices[0].message.content)
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "rate" in err:
                time.sleep(5 * (attempt + 1))
                continue
            if attempt == MAX_RETRIES - 1:
                raise
            if "connection" in err or "timeout" in err:
                time.sleep(2 * (attempt + 1))
                continue
            raise
    raise RuntimeError("Máximo de reintentos alcanzado")


def _cached_has_errors(news_list: list[dict]) -> bool:
    """True si hay errores en el cache."""
    for n in news_list or []:
        kp = n.get("key_points") or []
        if any(err in str(p) for p in kp for err in ["Error", "Sin noticias", "No disponible"]):
            return True
        h = str(n.get("headline", ""))
        if any(err in h for err in ["No disponible", "Sin noticias", "Sin resultados", "No se pudo"]):
            return True
    return False


async def fetch_news_for_matches(date_str: str, predictions: list[dict]) -> list[dict]:
    """Busca noticias solo para partidos NBA del día. Fútbol no soportado."""
    if not DEEPSEEK_API_KEY:
        print("[NEWS] DEEPSEEK_API_KEY no configurada. Omitiendo noticias.")
        return []
    print("[NEWS] Proveedor: DeepSeek")

    cached = history_db.get_news_for_date(date_str) if history_db.news_exist_for_date(date_str) else []
    if cached and not _cached_has_errors(cached):
        print(f"[NEWS] Noticias cacheadas para {date_str}.")
        return cached
    if cached and _cached_has_errors(cached):
        print(f"[NEWS] Cache con errores, re-fetch para {date_str}.")

    results = []
    for pred in predictions:
        home = pred.get("home_team", "")
        away = pred.get("away_team", "")
        match_id = pred.get("match_id", f"{date_str}_{away}_{home}".replace(" ", "_"))
        try:
            print(f"[NEWS] {home} vs {away} ...")
            news = await asyncio.to_thread(_fetch_news, home, away, date_str)
            history_db.save_match_news(date_str, match_id, news)
            results.append({"match_id": match_id, **news})
            print(f"[NEWS] OK: {news.get('headline', '')[:50]}")
        except Exception as e:
            print(f"[NEWS] Error {home} vs {away}: {e}")
            fallback = {
                "headline": "No disponible",
                "key_points": ["Error al consultar noticias"],
                "injuries": [],
                "impact_assessment": str(e)[:180],
                "confidence_modifier": "neutral",
            }
            history_db.save_match_news(date_str, match_id, fallback)
            results.append({"match_id": match_id, **fallback})
        time.sleep(THROTTLE_SECONDS)

    print(f"[NEWS] Completado: {len(results)} partidos.")
    return results
