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


# Backtest 2022-23 -> 2025-26 (5.149 partidos fuera de muestra, prob = cuotas sin vig):
#   3 favoritos sin filtro -> combinada acierta 50% (cuota 2.03); real ene-may 2026: 45%.
#   2 picks con prob >= 70% -> combinada acierta 70% (cuota 1.38), hay combinada el 68% de los días;
#   si solo 1 pick llega al 70% se recomienda solo (acierta 77%). Ninguna regla tiene ROI > 0 (vig).
# Oct 2026 (806 días, 2022-10 -> 2026-10): 1 pick >= 75% acierta 86% (cuota 1.13, ROI -2.8%, peor racha 3)
#   frente a 72% de 2 picks >= 70% (ROI -4.8%). Se eligió perder menos veces.
# El modelo propio no mejora el acierto a igual prob. de mercado: el filtro usa solo las cuotas.
MIN_PROB = 75.0
MAX_LEGS = 1


def _pick_odds(pred: dict):
    return pred.get("odds_home") if pred.get("winner") == pred.get("home_team") else pred.get("odds_away")


def _market_prob(pred: dict):
    """Probabilidad (%) del pick según las cuotas decimales, sin el margen de la casa. Sin cuotas -> None."""
    oh, oa = pred.get("odds_home"), pred.get("odds_away")
    if not oh or not oa or oh <= 1 or oa <= 1:
        return None
    p_home = (1 / oh) / (1 / oh + 1 / oa)
    return 100 * (p_home if pred.get("winner") == pred.get("home_team") else 1 - p_home)


def select_picks(predictions: list[dict]) -> list[dict]:
    """Los MAX_LEGS picks más probables del día con prob. de mercado >= MIN_PROB (puede devolver 0 o 1)."""
    picks = []
    for p in predictions:
        prob = _market_prob(p)
        if prob is not None and prob >= MIN_PROB and (p.get("warning_level") or "").upper() != "HIGH":
            picks.append({**p, "market_prob": round(prob, 1)})
    picks.sort(key=lambda p: p["market_prob"], reverse=True)
    return picks[:MAX_LEGS]


def calculate_parlay(odds_list: list[float], amount: float) -> dict:
    """Calcula retorno de parlay desde cuotas decimales."""
    combined = 1.0
    for o in odds_list:
        if o and o > 0:
            combined *= o
    potential = amount * combined
    return {"combined_odds": round(combined, 3), "stake": amount, "potential_return": round(potential, 2), "profit": round(potential - amount, 2)}


def _build_prompt(picks: list[dict], news_by_match: dict) -> str:
    """Prompt ultra-compacto. La IA solo explica: los picks ya están elegidos por probabilidad."""
    lines = []
    for i, c in enumerate(picks, 1):
        news = news_by_match.get(c.get("match_id", ""), {}).get("headline", "Sin noticias")[:120]
        lines.append(f"{i}. {c.get('home_team')} vs {c.get('away_team')} -> {c.get('winner')} ({c['market_prob']}%). "
                     f"Cuota: {_pick_odds(c)}. Noticia: {news}")
    ctx = "\n".join(lines)
    return f"""Analista NBA. Picks del día:
{ctx}
Explica cada pick. Responde SOLO JSON minificado:
{{"reasoning":"(breve)","individual_analyses":[{{"match":"...","pick":"...","confidence":"alta|media","reason":"(1 frase)"}}],"risk_level":"bajo|medio|alto","parlay_assessment":"(breve)"}}
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
        return {"reasoning": text[:300], "individual_analyses": [], "risk_level": "medio", "parlay_assessment": "Error parsing."}


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

    selected = select_picks(predictions)
    if not selected:
        return {"recommendations": [], "parlay_analysis": f"Hoy ningún pick llega al {MIN_PROB:.0f}% de probabilidad.",
                "parlay_odds": 0}

    news_list = history_db.get_news_for_date(date_str)
    news_by_match = {n["match_id"]: n for n in news_list}

    analysis = {"reasoning": "Selección automática.", "individual_analyses": [], "risk_level": "medio", "parlay_assessment": ""}
    if DEEPSEEK_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
            prompt = _build_prompt(selected, news_by_match)
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

    reco_items = []
    odds_for_parlay = []
    for item in selected:
        winner = item.get("winner", "")
        odds_val = _pick_odds(item)
        odds_for_parlay.append(float(odds_val))
        individual = next((a for a in analysis.get("individual_analyses", []) if item.get("home_team", "") in a.get("match", "")), {})
        reco_items.append({
            "match_id": item.get("match_id", ""),
            "home_team": item.get("home_team", ""),
            "away_team": item.get("away_team", ""),
            "pick": winner,
            "win_probability": item["market_prob"],
            "odds": odds_val,
            "confidence": individual.get("confidence", "media"),
            "reason": individual.get("reason", ""),
        })

    parlay = calculate_parlay(odds_for_parlay, 50000)
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
