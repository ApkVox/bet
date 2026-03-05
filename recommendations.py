"""
NBA Betting Recommendations Engine.
Selects the best bets of the day and builds a parlay (combinada)
using prediction data + Groq analysis.
"""
import asyncio
import json
import os
import time

from groq import Groq

import history_db

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = "groq/compound"


def _score_prediction(pred: dict) -> float:
    """Score a prediction for recommendation ranking.
    Higher = better candidate for the parlay."""
    prob = pred.get("win_probability") or pred.get("prob_final") or 0
    ev = pred.get("ev_score") or pred.get("ev_value") or 0
    warning = (pred.get("warning_level") or "NORMAL").upper()

    if warning == "HIGH":
        return -1

    odds_winner = pred.get("odds_home") if pred.get("winner") == pred.get("home_team") else pred.get("odds_away")
    odds_bonus = 0
    if odds_winner and odds_winner > 0:
        odds_bonus = min(odds_winner / 5.0, 0.5)

    return (prob * 0.55) + (max(ev, 0) * 0.35) + (odds_bonus * 0.10)


def select_candidates(predictions: list[dict], top_n: int = 5) -> list[dict]:
    """Pre-filter and rank predictions, returning the top N candidates."""
    scored = []
    for p in predictions:
        s = _score_prediction(p)
        if s > 0:
            scored.append((s, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:top_n]]


def calculate_parlay(odds_list: list[float], amount: float) -> dict:
    """Calculate parlay return from decimal odds."""
    combined = 1.0
    for o in odds_list:
        if o and o > 0:
            combined *= o
    potential = amount * combined
    profit = potential - amount
    return {
        "combined_odds": round(combined, 3),
        "stake": amount,
        "potential_return": round(potential, 2),
        "profit": round(profit, 2),
    }


def _build_reco_prompt(candidates: list[dict], news_by_match: dict) -> str:
    matches_text = ""
    for i, c in enumerate(candidates, 1):
        home = c.get("home_team", "?")
        away = c.get("away_team", "?")
        winner = c.get("winner", "?")
        prob = c.get("win_probability", 0)
        odds_h = c.get("odds_home") or "N/A"
        odds_a = c.get("odds_away") or "N/A"
        ev = c.get("ev_score") or c.get("ev_value") or 0
        mid = c.get("match_id", "")
        news_headline = news_by_match.get(mid, {}).get("headline", "Sin noticias")

        matches_text += f"""
{i}. **{home} vs {away}**
   - Ganador predicho: {winner} ({prob}%)
   - Cuota local: {odds_h} | Cuota visitante: {odds_a}
   - EV: {ev}
   - Noticias: {news_headline}
"""

    return f"""Eres un analista experto en apuestas NBA. Analiza los siguientes partidos candidatos y selecciona los 3 MEJORES para una apuesta combinada (parlay) del día.

PARTIDOS CANDIDATOS:
{matches_text}

Criterios de selección:
1. Alta probabilidad de acierto
2. Cuotas que ofrezcan valor (EV positivo o cercano)
3. Noticias que refuercen la predicción (sin lesiones clave del favorito)
4. Diversificación de riesgo (no concentrar todo en favoritos extremos)

Responde EXCLUSIVAMENTE con un JSON válido (sin markdown, sin texto fuera del JSON):
{{
  "selected_indices": [1, 2, 3],
  "reasoning": "explicación breve de por qué estos 3 partidos forman la mejor combinada",
  "individual_analyses": [
    {{"match": "Equipo1 vs Equipo2", "pick": "ganador elegido", "confidence": "alta|media", "reason": "razón breve"}}
  ],
  "risk_level": "bajo|medio|alto",
  "parlay_assessment": "evaluación general de la combinada"
}}

Responde siempre en español."""


def _parse_reco_response(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        first_nl = text.index("\n")
        last_fence = text.rfind("```")
        text = text[first_nl + 1:last_fence].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "selected_indices": [1, 2, 3],
            "reasoning": text[:400],
            "individual_analyses": [],
            "risk_level": "medio",
            "parlay_assessment": "No se pudo procesar el análisis del agente.",
        }


def generate_recommendations_sync(date_str: str) -> dict:
    """
    Main entry: read predictions + news from DB, select candidates,
    call Groq for final analysis, persist and return result.
    """
    existing = history_db.get_daily_recommendations(date_str)
    if existing:
        recos = existing.get("recommendations", [])
        has_odds = any(r.get("odds") for r in recos)
        if has_odds or not recos:
            return existing
        print(f"[RECO] Recomendaciones para {date_str} tienen cuotas NULL, regenerando...")
        history_db.delete_daily_recommendations(date_str)

    predictions = history_db.get_predictions_by_date_light(date_str)
    if not predictions:
        return {"recommendations": [], "parlay_analysis": "No hay partidos disponibles.", "parlay_odds": 0}

    candidates = select_candidates(predictions)
    if len(candidates) < 2:
        return {"recommendations": [], "parlay_analysis": "Insuficientes partidos con valor para recomendar.", "parlay_odds": 0}

    news_list = history_db.get_news_for_date(date_str)
    news_by_match = {n["match_id"]: n for n in news_list}

    try:
        client = Groq(api_key=GROQ_API_KEY)
        prompt = _build_reco_prompt(candidates, news_by_match)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2048,
        )
        analysis = _parse_reco_response(response.choices[0].message.content)
    except Exception as e:
        print(f"[RECO] Error Groq: {e}")
        analysis = {
            "selected_indices": list(range(1, min(4, len(candidates) + 1))),
            "reasoning": "Selección automática por puntuación (agente no disponible).",
            "individual_analyses": [],
            "risk_level": "medio",
            "parlay_assessment": str(e)[:200],
        }

    selected_indices = analysis.get("selected_indices", [1, 2, 3])
    selected = []
    for idx in selected_indices:
        if 1 <= idx <= len(candidates):
            selected.append(candidates[idx - 1])

    if not selected:
        selected = candidates[:3]

    reco_items = []
    odds_for_parlay = []
    for item in selected:
        winner = item.get("winner", "")
        odds_val = item.get("odds_home") if winner == item.get("home_team") else item.get("odds_away")
        if odds_val:
            odds_for_parlay.append(float(odds_val))

        individual = next(
            (a for a in analysis.get("individual_analyses", [])
             if item.get("home_team", "") in a.get("match", "")),
            {}
        )

        reco_items.append({
            "match_id": item.get("match_id", ""),
            "home_team": item.get("home_team", ""),
            "away_team": item.get("away_team", ""),
            "pick": winner,
            "win_probability": item.get("win_probability", 0),
            "odds": odds_val,
            "confidence": individual.get("confidence", "media"),
            "reason": individual.get("reason", ""),
        })

    parlay = calculate_parlay(odds_for_parlay, 50000) if odds_for_parlay else {"combined_odds": 0}

    result = {
        "recommendations": reco_items,
        "parlay_analysis": analysis.get("parlay_assessment", analysis.get("reasoning", "")),
        "parlay_odds": parlay.get("combined_odds", 0),
        "risk_level": analysis.get("risk_level", "medio"),
        "reasoning": analysis.get("reasoning", ""),
    }

    history_db.save_daily_recommendations(date_str, result)
    print(f"[RECO] Guardadas {len(reco_items)} recomendaciones para {date_str}")
    return result


async def generate_recommendations(date_str: str) -> dict:
    return await asyncio.to_thread(generate_recommendations_sync, date_str)
