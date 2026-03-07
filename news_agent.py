"""
NBA News Research Agent - Groq (web search integrado) o DeepSeek (con duckduckgo).
Fetches and caches relevant news for each NBA match of the day.
Evita 413 (prompt largo) y 429 (rate limit) con prompt corto, fallback DeepSeek y round-robin.
"""
import asyncio
import json
import os
import re
import time
from datetime import datetime

from groq import Groq, APIConnectionError
from tenacity import retry, stop_after_attempt, retry_if_exception, wait_exponential

import history_db

GROQ_API_KEY = (os.getenv("GROQ_API_KEY") or "").strip()
DEEPSEEK_API_KEY = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
# auto=round-robin si ambos; groq|deepseek=forzar uno
NEWS_PROVIDER = (os.getenv("NEWS_PROVIDER") or "auto").strip().lower()
GROQ_MODEL = "groq/compound-mini"
DEEPSEEK_MODEL = "deepseek-chat"
THROTTLE_SECONDS = 6.0
THROTTLE_AFTER_GROQ = 12.0
MAX_RETRIES = 3
DEEPSEEK_SEARCH_RESULTS = 8


def _search_web_duckduckgo(home_team: str, away_team: str) -> str:
    """Busca noticias NBA con duckduckgo. Snippets cortos para contexto optimizado."""
    try:
        from duckduckgo_search import DDGS
        query = f"NBA {home_team} vs {away_team} news injuries 2025"
        snippets = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=DEEPSEEK_SEARCH_RESULTS):
                title = r.get("title", "")
                body = r.get("body", "")
                if title or body:
                    s = f"{title}: {body[:150]}" if body else title
                    snippets.append(s)
        return "\n".join(snippets[:6]) if snippets else "Sin resultados."
    except Exception as e:
        return f"Error: {e}"


def _build_prompt_groq(home_team: str, away_team: str, date_str: str) -> str:
    """Prompt ultra corto para evitar 413. Noticias concretas: lesiones, rachas, impacto."""
    return f"""NBA {home_team} vs {away_team} {date_str}. Busca: lesiones clave, rachas recientes.
JSON: {{"headline":"...","key_points":["p1","p2","p3"],"injuries":[{{"player":"","team":"","status":"out/questionable/probable"}}],"impact_assessment":"...","confidence_modifier":"higher|neutral|lower"}}
Español. Concreto. Sin datos: key_points ["Sin noticias"], injuries []."""


def _build_prompt_deepseek(home_team: str, away_team: str, date_str: str, web_context: str) -> str:
    """Prompt optimizado para noticias concretas: lesiones, rachas, impacto en pronóstico."""
    return f"""Partido NBA: {home_team} vs {away_team} ({date_str}).

BÚSQUEDA:
{web_context}

Extrae lo MÁS RELEVANTE para el pronóstico. Responde SOLO JSON:
{{"headline":"{home_team} vs {away_team}: [resumen]","key_points":["hecho 1 concreto","hecho 2","hecho 3"],"injuries":[{{"player":"nombre","team":"equipo","status":"out/questionable/probable"}}],"impact_assessment":"1-2 frases sobre impacto","confidence_modifier":"higher|neutral|lower"}}

Reglas: Español. Máx 3 key_points concretos (lesiones, rachas, load management). Sin datos: key_points ["Sin noticias"], injuries []."""


def _parse_response(content: str) -> dict:
    """Extract JSON from Groq response, handling markdown fences."""
    text = content.strip()
    if text.startswith("```"):
        first_nl = text.index("\n")
        last_fence = text.rfind("```")
        text = text[first_nl + 1:last_fence].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "headline": "No se pudo procesar la respuesta del agente",
            "key_points": [text[:300]],
            "injuries": [],
            "impact_assessment": text[:500],
            "confidence_modifier": "neutral",
        }


def _is_retryable_error(e: Exception) -> bool:
    """Errores de conexión/red que merecen reintento. 429/413 se manejan en caller."""
    if isinstance(e, (APIConnectionError, ConnectionError, OSError)):
        return True
    msg = str(e).lower()
    if "connection" in msg or "timeout" in msg or "network" in msg:
        return True
    if "429" in msg or "413" in msg or "request_too_large" in msg:
        return False
    return False


def _parse_retry_after_seconds(e: Exception) -> float:
    """Extrae segundos de 'Please try again in 130ms' o '3.204s' del error 429."""
    msg = str(e)
    m = re.search(r"try again in (\d+(?:\.\d+)?)\s*(ms|s)?", msg, re.I)
    if not m:
        return 5.0
    val = float(m.group(1))
    unit = (m.group(2) or "s").lower()
    return val / 1000.0 if unit == "ms" else val


def _use_groq() -> bool:
    return (NEWS_PROVIDER == "groq" or (NEWS_PROVIDER == "auto" and GROQ_API_KEY)) and bool(GROQ_API_KEY)


def _use_deepseek() -> bool:
    return (NEWS_PROVIDER == "deepseek" or (NEWS_PROVIDER == "auto" and DEEPSEEK_API_KEY)) and bool(DEEPSEEK_API_KEY)


def _use_groq_for_match(match_index: int) -> bool:
    """Con ambos configurados: DeepSeek para todos (evita 413). Solo Groq si no hay DeepSeek."""
    if NEWS_PROVIDER != "auto" or not (GROQ_API_KEY and DEEPSEEK_API_KEY):
        return _use_groq()
    return False


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    retry=retry_if_exception(_is_retryable_error),
    wait=wait_exponential(multiplier=1, min=3, max=15),
    reraise=True,
)
def _fetch_with_groq(home_team: str, away_team: str, date_str: str) -> dict:
    """Groq compound con búsqueda web integrada."""
    client = Groq(api_key=GROQ_API_KEY, default_headers={"Groq-Model-Version": "latest"})
    prompt = _build_prompt_groq(home_team, away_team, date_str)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1024,
    )
    return _parse_response(response.choices[0].message.content)


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    retry=retry_if_exception(_is_retryable_error),
    wait=wait_exponential(multiplier=1, min=3, max=15),
    reraise=True,
)
def _fetch_with_deepseek(home_team: str, away_team: str, date_str: str) -> dict:
    """DeepSeek con búsqueda web via duckduckgo."""
    from openai import OpenAI
    web_context = _search_web_duckduckgo(home_team, away_team)
    prompt = _build_prompt_deepseek(home_team, away_team, date_str, web_context)
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1024,
    )
    return _parse_response(response.choices[0].message.content)


def fetch_single_match_news(home_team: str, away_team: str, date_str: str, match_index: int = 0) -> dict:
    """Obtiene noticias usando Groq o DeepSeek según configuración (round-robin si ambos)."""
    use_groq = _use_groq_for_match(match_index)
    if use_groq:
        try:
            return _fetch_with_groq(home_team, away_team, date_str)
        except Exception as e:
            err_str = str(e).lower()
            is_413 = "413" in err_str or "request_too_large" in err_str
            is_429 = "429" in err_str or "rate_limit" in err_str
            if (is_413 or is_429) and _use_deepseek():
                return _fetch_with_deepseek(home_team, away_team, date_str)
            if is_429 and not _use_deepseek():
                wait_s = _parse_retry_after_seconds(e)
                time.sleep(wait_s)
                return _fetch_with_groq(home_team, away_team, date_str)
            raise
    if _use_deepseek():
        return _fetch_with_deepseek(home_team, away_team, date_str)
    raise ValueError(
        "Ningún proveedor configurado. Añade GROQ_API_KEY o DEEPSEEK_API_KEY en GitHub Secrets. "
        "Opcional: NEWS_PROVIDER=groq|deepseek|auto"
    )


def _cached_news_has_errors(news_list: list[dict]) -> bool:
    """True si las noticias cacheadas tienen errores (ej. Connection error)."""
    for n in news_list or []:
        kp = n.get("key_points") or []
        if any("Error al consultar" in str(p) for p in kp):
            return True
        if "No disponible" in str(n.get("headline", "")) and "Connection" in str(n.get("impact_assessment", "")):
            return True
    return False


async def fetch_news_for_matches(date_str: str, predictions: list[dict]) -> list[dict]:
    """
    Fetch news for all NBA matches and cache in DB.
    Round-robin Groq/DeepSeek si ambos configurados. Throttle mayor tras Groq.
    """
    if not _use_groq() and not _use_deepseek():
        print("[NEWS] Ni GROQ_API_KEY ni DEEPSEEK_API_KEY configuradas. Omitiendo noticias.")
        return []
    both = GROQ_API_KEY and DEEPSEEK_API_KEY and NEWS_PROVIDER == "auto"
    print(f"[NEWS] Proveedor: {'Round-robin Groq+DeepSeek' if both else ('Groq' if _use_groq() else 'DeepSeek')}")

    cached = history_db.get_news_for_date(date_str) if history_db.news_exist_for_date(date_str) else []
    if cached and not _cached_news_has_errors(cached):
        print(f"[NEWS] Noticias ya cacheadas para {date_str}, omitiendo.")
        return cached
    if cached and _cached_news_has_errors(cached):
        print(f"[NEWS] Noticias cacheadas con errores para {date_str}, re-intentando fetch.")

    results = []
    for i, pred in enumerate(predictions):
        home = pred.get("home_team", "")
        away = pred.get("away_team", "")
        match_id = pred.get("match_id", f"{date_str}_{away}_{home}".replace(" ", "_"))
        used_groq = _use_groq_for_match(i)

        try:
            print(f"[NEWS] Investigando: {home} vs {away} ...")
            news = await asyncio.to_thread(
                fetch_single_match_news, home, away, date_str, i
            )
            history_db.save_match_news(date_str, match_id, news)
            results.append({"match_id": match_id, **news})
            print(f"[NEWS] OK: {news.get('headline', '?')[:60]}")
        except Exception as e:
            print(f"[NEWS] Error para {home} vs {away}: {e}")
            fallback = {
                "headline": "No disponible",
                "key_points": ["Error al consultar noticias"],
                "injuries": [],
                "impact_assessment": str(e)[:200],
                "confidence_modifier": "neutral",
            }
            history_db.save_match_news(date_str, match_id, fallback)
            results.append({"match_id": match_id, **fallback})

        throttle = THROTTLE_AFTER_GROQ if used_groq else THROTTLE_SECONDS
        time.sleep(throttle)

    print(f"[NEWS] Completado: {len(results)} partidos investigados.")
    return results
