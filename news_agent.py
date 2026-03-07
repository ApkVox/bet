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
MAX_CONTEXT_CHARS = 1200


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


def _search_web(home_team: str, away_team: str) -> str:
    """Búsqueda web con DuckDuckGo. Contexto corto para evitar prompts grandes."""
    DDGS = _get_ddgs()
    if DDGS is None:
        return "Sin resultados (duckduckgo_search / ddgs no instalado)."
    year = time.strftime("%Y")
    query = f"NBA {home_team} vs {away_team} news injuries {year}"
    try:
        snippets = []
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=SEARCH_RESULTS))
        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            s = f"{title}: {body[:120]}" if body else title
            if s.strip():
                snippets.append(s)
        text = "\n".join(snippets[:6])
        return text[:MAX_CONTEXT_CHARS] if len(text) > MAX_CONTEXT_CHARS else text or "Sin resultados."
    except Exception as e:
        return f"Sin resultados (error búsqueda: {type(e).__name__})"


def _build_prompt(home_team: str, away_team: str, date_str: str, web_context: str) -> str:
    """Prompt compacto: noticias concretas, JSON estricto."""
    return f"""Partido: {home_team} vs {away_team} ({date_str}).

BÚSQUEDA:
{web_context}

Extrae lo relevante. Responde SOLO JSON:
{{"headline":"...","key_points":["p1","p2","p3"],"injuries":[{{"player":"","team":"","status":"out/questionable/probable"}}],"impact_assessment":"...","confidence_modifier":"higher|neutral|lower"}}

Español. Máx 3 key_points. Sin datos: key_points ["Sin noticias"], injuries []."""


def _parse_response(content: str) -> dict:
    """Extrae JSON de la respuesta, maneja markdown."""
    text = content.strip()
    if text.startswith("```"):
        first_nl = text.index("\n")
        last_fence = text.rfind("```")
        text = text[first_nl + 1:last_fence].strip()
    try:
        return json.loads(text)
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
    web_context = _search_web(home_team, away_team)
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
        if any("Error" in str(p) for p in kp):
            return True
        if "No disponible" in str(n.get("headline", "")):
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
