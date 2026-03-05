"""
NBA News Research Agent using Groq compound model with web search.
Fetches and caches relevant news for each NBA match of the day.
"""
import asyncio
import json
import os
import time
from datetime import datetime

from groq import Groq

import history_db

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "groq/compound"
THROTTLE_SECONDS = 2.5


def _build_prompt(home_team: str, away_team: str, date_str: str) -> str:
    return f"""Eres un analista experto de la NBA. Investiga las noticias más recientes y relevantes para el partido NBA **{home_team} vs {away_team}** programado para el **{date_str}**.

Busca en la web información actualizada sobre:
- Lesiones confirmadas o dudas de jugadores clave de ambos equipos
- Rachas de victorias/derrotas recientes de ambos equipos
- Noticias de último momento (trades, suspensiones, load management, descansos)
- Condiciones especiales (back-to-back, viajes largos, rivalidades históricas)
- Rendimiento reciente de jugadores estrella

Responde EXCLUSIVAMENTE con un JSON válido (sin markdown, sin texto fuera del JSON) con esta estructura:
{{
  "headline": "título breve del contexto clave del partido",
  "key_points": ["punto relevante 1", "punto relevante 2", "punto relevante 3"],
  "injuries": [{{"player": "nombre", "team": "equipo", "status": "out/questionable/probable"}}],
  "impact_assessment": "párrafo breve explicando cómo estas noticias afectan el pronóstico del partido",
  "confidence_modifier": "higher|neutral|lower"
}}

Reglas:
- Responde siempre en español.
- Si no encuentras noticias relevantes, devuelve key_points con ["Sin noticias relevantes encontradas"] e injuries vacío.
- El campo confidence_modifier indica si las noticias refuerzan (higher), no afectan (neutral) o debilitan (lower) la confianza en el favorito."""


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


def fetch_single_match_news(home_team: str, away_team: str, date_str: str) -> dict:
    """Call Groq compound model with web search for a single match."""
    client = Groq(api_key=GROQ_API_KEY)
    prompt = _build_prompt(home_team, away_team, date_str)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=2048,
    )

    raw = response.choices[0].message.content
    return _parse_response(raw)


async def fetch_news_for_matches(date_str: str, predictions: list[dict]) -> list[dict]:
    """
    Fetch news for all NBA matches and cache in DB.
    Runs sequentially with throttle to respect Groq rate limits.
    Skips if news already exist for this date.
    """
    if history_db.news_exist_for_date(date_str):
        print(f"[NEWS] Noticias ya cacheadas para {date_str}, omitiendo.")
        return history_db.get_news_for_date(date_str)

    results = []
    for pred in predictions:
        home = pred.get("home_team", "")
        away = pred.get("away_team", "")
        match_id = pred.get("match_id", f"{date_str}_{away}_{home}".replace(" ", "_"))

        try:
            print(f"[NEWS] Investigando: {home} vs {away} ...")
            news = await asyncio.to_thread(
                fetch_single_match_news, home, away, date_str
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

        time.sleep(THROTTLE_SECONDS)

    print(f"[NEWS] Completado: {len(results)} partidos investigados.")
    return results
