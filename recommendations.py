"""
NBA Betting Recommendations Engine - DeepSeek.
Solo NBA. Selecciona las mejores apuestas del día y genera combinada (parlay).
"""
import asyncio
import json
import os

import history_db

DEEPSEEK_API_KEY = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
MODEL = "deepseek-chat"


def _score_prediction(pred: dict) -> float:
    """Puntúa predicción para ranking. Mayor = mejor candidato."""
    prob = pred.get("win_probability") or pred.get("prob_final") or 0
    ev = pred.get("ev_score") or pred.get("ev_value") or 0
    if (pred.get("warning_level") or "").upper() == "HIGH":
        return -1
    odds_winner = pred.get("odds_home") if pred.get("winner") == pred.get("home_team") else pred.get("odds_away")
    odds_bonus = min(odds_winner / 5.0, 0.5) if odds_winner and odds_winner > 0 else 0
    return (prob * 0.55) + (max(ev, 0) * 0.35) + (odds_bonus * 0.10)


def select_candidates(predictions: list[dict], top_n: int = 5) -> list[dict]:
    """Pre-filtra y ordena predicciones, devuelve top N."""
    scored = [(s, p) for p in predictions if (s := _score_prediction(p)) > 0]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:top_n]]


def calculate_parlay(odds_list: list[float], amount: float) -> dict:
    """Calcula retorno de parlay desde cuotas decimales."""
    combined = 1.0
    for o in odds_list:
        if o and o > 0:
            combined *= o
    potential = amount * combined
    return {"combined_odds": round(combined, 3), "stake": amount, "potential_return": round(potential, 2), "profit": round(potential - amount, 2)}


def _build_prompt(candidates: list[dict], news_by_match: dict) -> str:
    """Prompt compacto para evitar 413."""
    lines = []
    for i, c in enumerate(candidates[:5], 1):
        mid = c.get("match_id", "")
        news = news_by_match.get(mid, {}).get("headline", "Sin noticias")[:80]
        lines.append(f"{i}. {c.get('home_team')} vs {c.get('away_team')} -> {c.get('winner')} ({c.get('win_probability',0)}%). Cuota: {c.get('odds_home') or c.get('odds_away')}. EV:{c.get('ev_score') or 0}. Noticias: {news}")
    matches_text = "\n".join(lines)
    return f"""Analista NBA. Partidos candidatos:
{matches_text}

Selecciona los 3 MEJORES para parlay. Responde SOLO JSON:
{{"selected_indices":[1,2,3],"reasoning":"...","individual_analyses":[{{"match":"...","pick":"...","confidence":"alta|media","reason":"..."}}],"risk_level":"bajo|medio|alto","parlay_assessment":"..."}}
Español."""


def _parse_reco_response(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        first_nl = text.index("\n")
        last_fence = text.rfind("```")
        text = text[first_nl + 1:last_fence].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"selected_indices": [1, 2, 3], "reasoning": text[:300], "individual_analyses": [], "risk_level": "medio", "parlay_assessment": "Error parsing."}


def generate_recommendations_sync(date_str: str) -> dict:
    """Lee predicciones + noticias, llama DeepSeek, persiste y retorna."""
    existing = history_db.get_daily_recommendations(date_str)
    if existing:
        recos = existing.get("recommendations", [])
        if any(r.get("odds") for r in recos) or not recos:
            return existing
        history_db.delete_daily_recommendations(date_str)

    predictions = history_db.get_predictions_by_date_light(date_str)
    if not predictions:
        return {"recommendations": [], "parlay_analysis": "No hay partidos.", "parlay_odds": 0}

    candidates = select_candidates(predictions)
    if len(candidates) < 2:
        return {"recommendations": [], "parlay_analysis": "Insuficientes partidos con valor.", "parlay_odds": 0}

    news_list = history_db.get_news_for_date(date_str)
    news_by_match = {n["match_id"]: n for n in news_list}

    analysis = {"selected_indices": [1, 2, 3], "reasoning": "Selección automática.", "individual_analyses": [], "risk_level": "medio", "parlay_assessment": ""}
    if DEEPSEEK_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
            prompt = _build_prompt(candidates, news_by_match)
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1024,
            )
            analysis = _parse_reco_response(response.choices[0].message.content)
        except Exception as e:
            print(f"[RECO] Error DeepSeek: {e}")
            analysis["parlay_assessment"] = str(e)[:150]

    selected_indices = analysis.get("selected_indices", [1, 2, 3])
    selected = [candidates[i - 1] for i in selected_indices if 1 <= i <= len(candidates)]
    if not selected:
        selected = candidates[:3]

    reco_items = []
    odds_for_parlay = []
    for item in selected:
        winner = item.get("winner", "")
        odds_val = item.get("odds_home") if winner == item.get("home_team") else item.get("odds_away")
        if odds_val:
            odds_for_parlay.append(float(odds_val))
        individual = next((a for a in analysis.get("individual_analyses", []) if item.get("home_team", "") in a.get("match", "")), {})
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
