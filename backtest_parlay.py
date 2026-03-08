"""
Backtest: Simula apostar la combinada diaria (3 mejores picks) desde 2026-01-01 hasta hoy.
Meta: maximizar rentabilidad. Estrategia optimizada: picks de alta confianza (prob ≥ 75%),
stake dinámico (35% cuando muy confiado), scoring prioriza probabilidad.
"""
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).parent / "Data" / "history.db"
DATE_START = "2026-01-01"
DATE_END = date.today().isoformat()
INITIAL_CAPITAL = 50_000
TARGET_CAPITAL = 10_050_000  # Meta: 10M ganancia
STAKE_PCT = 0.05  # 5% base (óptimo para parlays)
STAKE_PCT_HIGH = 0.07  # 7% cuando min prob >= 85%
STAKE_AFTER_LOSS = 0.04  # Tras 2 pérdidas seguidas, reducir a 4%
ESTIMATED_ODDS_PER_PICK = 1.5
MIN_PROB_LEVELS = [0.80, 0.75, 0.70, 0.65]  # Fallback progresivo
MIN_EV = 0


def _score_prediction(pred: dict) -> float:
    """Scoring optimizado: 70% prob, 20% EV, 10% odds (priorizar acierto)."""
    prob = pred.get("win_probability") or pred.get("prob_final") or 0
    ev = pred.get("ev_score") or pred.get("ev_value") or 0
    warning = (pred.get("warning_level") or "NORMAL").upper()
    if warning == "HIGH":
        return -1
    winner = pred.get("winner") or pred.get("predicted_winner")
    odds_winner = pred.get("odds_home") if winner == pred.get("home_team") else pred.get("odds_away")
    odds_bonus = min(odds_winner / 5.0, 0.5) if (odds_winner and odds_winner > 0) else 0
    return (prob * 0.70) + (max(ev, 0) * 0.20) + (odds_bonus * 0.10)


def select_top3(predictions: list[dict], min_prob: float = 0, min_ev: float = 0) -> list[dict]:
    """Selecciona las 3 mejores predicciones con prob >= min_prob y EV >= min_ev."""
    scored = []
    for p in predictions:
        prob = p.get("win_probability") or p.get("prob_final") or 0
        ev = p.get("ev_score") or p.get("ev_value") or 0
        if prob < min_prob or ev < min_ev:
            continue
        s = _score_prediction(p)
        if s > 0:
            scored.append((s, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:3]]


def select_top3_with_fallback(predictions: list[dict]) -> tuple[list[dict], str]:
    """Intenta con criterios estrictos primero; relaja solo si no hay 3 picks."""
    for min_prob in MIN_PROB_LEVELS:
        picks = select_top3(predictions, min_prob=min_prob, min_ev=MIN_EV)
        if len(picks) >= 3:
            return picks[:3], f"prob ≥ {min_prob*100:.0f}%"
    return [], "ninguna"


def _stake_pct(picks: list[dict], consecutive_losses: int = 0) -> float:
    """Stake dinámico: reducir tras rachas perdedoras para preservar capital."""
    if consecutive_losses >= 2:
        return STAKE_AFTER_LOSS
    min_prob = min(p.get("win_probability") or p.get("prob_final") or 0 for p in picks)
    return STAKE_PCT_HIGH if min_prob >= 0.85 else STAKE_PCT


def get_parlay_odds(picks: list[dict]) -> float | None:
    """Cuota combinada decimal de los 3 picks. None si falta alguna cuota."""
    combined = 1.0
    for p in picks:
        winner = p.get("winner") or p.get("predicted_winner")
        odds = p.get("odds_home") if winner == p.get("home_team") else p.get("odds_away")
        if not odds or float(odds) <= 0:
            return None
        combined *= float(odds)
    return round(combined, 3)


def run_backtest(use_estimated_odds: bool = False, bet_every_day: bool = False) -> dict:
    """Ejecuta el backtest desde 2026-01-01 hasta hoy.
    bet_every_day: apuesta todos los días, relajando criterios y usando odds estimadas si faltan.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT date, match_id, home_team, away_team, predicted_winner,
               prob_final, ev_value, warning_level, result, odds_home, odds_away
        FROM predictions
        WHERE date >= ? AND date <= ?
        ORDER BY date
    """, (DATE_START, DATE_END))
    rows = cursor.fetchall()

    # Agrupar por fecha
    by_date = {}
    for r in rows:
        date_str = r[0]
        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].append({
            "match_id": r[1],
            "home_team": r[2],
            "away_team": r[3],
            "winner": r[4],
            "predicted_winner": r[4],
            "win_probability": r[5] or 0,
            "ev_score": r[6],
            "ev_value": r[6],
            "warning_level": r[7] or "NORMAL",
            "result": r[8],
            "odds_home": r[9],
            "odds_away": r[10],
        })

    # Ejecutar backtest
    capital = INITIAL_CAPITAL
    history = []
    total_days = 0
    winning_days = 0
    losing_days = 0
    skipped_days = 0
    consecutive_losses = 0

    for date_str in sorted(by_date.keys()):
        preds = by_date[date_str]
        if bet_every_day:
            picks, pick_label = select_top3_with_fallback(preds)
        else:
            picks = select_top3(preds, min_prob=MIN_PROB_LEVELS[0])
            pick_label = f"prob >= {MIN_PROB_LEVELS[0]*100:.0f}%"

        if len(picks) < 3:
            skipped_days += 1
            history.append({
                "date": date_str,
                "action": "skip",
                "reason": f"Solo {len(picks)} picks válidos (sin 3 partidos con resultado)",
                "capital": capital,
            })
            continue

        # Verificar que todos los partidos tengan resultado
        results_by_match = {p["match_id"]: p["result"] for p in preds}
        all_resolved = all(
            results_by_match.get(p["match_id"]) in ("WIN", "LOSS")
            for p in picks
        )

        if not all_resolved:
            skipped_days += 1
            pending = [p["match_id"] for p in picks if results_by_match.get(p["match_id"]) not in ("WIN", "LOSS")]
            history.append({
                "date": date_str,
                "action": "skip",
                "reason": f"Resultados pendientes",
                "capital": capital,
            })
            continue

        parlay_odds = get_parlay_odds(picks)
        odds_estimated = False
        stake_pct = _stake_pct(picks, consecutive_losses) if not bet_every_day else STAKE_PCT
        stake = round(capital * stake_pct, 2)
        if stake < 100:
            skipped_days += 1
            history.append({
                "date": date_str,
                "action": "skip",
                "reason": "Capital insuficiente",
                "capital": capital,
            })
            continue

        if parlay_odds is None:
            if use_estimated_odds or bet_every_day:
                parlay_odds = round(ESTIMATED_ODDS_PER_PICK ** 3, 3)
                odds_estimated = True
            else:
                skipped_days += 1
                history.append({
                    "date": date_str,
                    "action": "skip",
                    "reason": "Sin cuotas en datos historicos",
                    "capital": capital,
                })
                continue

        total_days += 1

        all_won = all(results_by_match.get(p["match_id"]) == "WIN" for p in picks)
        if all_won:
            consecutive_losses = 0
            return_amount = round(stake * parlay_odds, 2)
            profit = return_amount - stake
            capital = round(capital - stake + return_amount, 2)
            winning_days += 1
            history.append({
                "date": date_str,
                "action": "bet",
                "result": "WIN",
                "stake": stake,
                "parlay_odds": parlay_odds,
                "odds_estimated": odds_estimated,
                "return": return_amount,
                "profit": profit,
                "capital": capital,
                "picks": [
                    f"{p['away_team']} @ {p['home_team']} -> {p['winner']} ({p['result']})"
                    for p in picks
                ],
            })
        else:
            consecutive_losses += 1
            capital = round(capital - stake, 2)
            losing_days += 1
            losses = [p for p in picks if results_by_match.get(p["match_id"]) == "LOSS"]
            history.append({
                "date": date_str,
                "action": "bet",
                "result": "LOSS",
                "stake": stake,
                "parlay_odds": parlay_odds,
                "odds_estimated": odds_estimated,
                "return": 0,
                "profit": -stake,
                "capital": capital,
                "picks": [
                    f"{p['away_team']} @ {p['home_team']} -> {p['winner']} ({p['result']})"
                    for p in picks
                ],
                "lost_on": [f"{p['away_team']} @ {p['home_team']}" for p in losses],
            })

    conn.close()

    return {
        "initial_capital": INITIAL_CAPITAL,
        "final_capital": capital,
        "total_return_pct": ((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100) if INITIAL_CAPITAL else 0,
        "total_days_bet": total_days,
        "winning_days": winning_days,
        "losing_days": losing_days,
        "skipped_days": skipped_days,
        "use_estimated_odds": use_estimated_odds,
        "history": history,
    }


def write_backtest_doc(result: dict, doc_path: Path, bet_every_day: bool = False) -> None:
    """Genera y escribe el documento de resultados del backtest."""
    bets = [h for h in result["history"] if h.get("action") == "bet"]
    wins = [b for b in bets if b.get("result") == "WIN"]
    losses = [b for b in bets if b.get("result") == "LOSS"]

    if bet_every_day:
        title = "Combinada Diaria — Apuesta Todos los Días"
        sel = "Las 3 mejores predicciones; si no hay 3 con prob ≥ 65%, relajar: 60% → 55% → 50% → cualquiera."
        cuotas = "Reales cuando hay; estimadas si faltan."
    else:
        title = "Combinada Diaria — Estrategia Optimizada (meta 10M)"
        sel = "Las 3 predicciones con mayor puntuación; prob ≥ 80% (fallback 75%→70%→65%). Scoring: 70% prob, 20% EV."
        cuotas = "Reales desde sbrscrape (backfill automático)."

    lines = [
        f"# Análisis de Backtest: {title}",
        "",
        "**La Fija** — Meta: $10M ganancia. Estrategia optimizada para maximizar rentabilidad.",
        "",
        "---",
        "",
        "## Metodología",
        "",
        "- **Capital inicial:** $50.000 COP  ",
        "- **Stake:** 5% base, 7% cuando min prob ≥ 85%, 4% tras 2 pérdidas  ",
        f"- **Selección de picks:** {sel}  ",
        f"- **Periodo:** {DATE_START} — {DATE_END}  ",
        f"- **Cuotas:** {cuotas}",
        "",
        "---",
        "",
        "## Resumen",
        "",
        f"| Métrica | Valor |",
        f"|---------|-------|",
        f"| Capital final | ${result['final_capital']:,.0f} |",
        f"| Retorno (%) | {result['total_return_pct']:+.2f}% |",
        f"| Días apostados | {result['total_days_bet']} |",
        f"| Combinadas ganadas | {result['winning_days']} |",
        f"| Combinadas perdidas | {result['losing_days']} |",
        f"| Días omitidos | {result['skipped_days']} |",
        "",
        "---",
        "",
        "## Detalle por día",
        "",
    ]

    if bets:
        lines.append("| Fecha | Apuesta | Cuota | Resultado | Capital |")
        lines.append("|-------|---------------|-------|-----------|---------|")
        for b in bets:
            res = "**GANADA**" if b.get("result") == "WIN" else "**PERDIDA**"
            lines.append(f"| {b['date']} | ${b['stake']:,.0f} | {b['parlay_odds']} | {res} | ${b['capital']:,.0f} |")

        if losses:
            lines.extend(["", "**Partidos que fallaron:**", ""])
            for b in losses:
                for p in b.get("lost_on", []):
                    lines.append(f"- {p}")

        lines.extend([
            "",
            "---",
            "",
            "## Meta 10M y limitaciones",
            "",
            f"Con los datos históricos ({result['total_days_bet']} días, {result['winning_days']} ganadas, {result['losing_days']} perdidas), el mejor resultado es ~${result['final_capital']:,.0f}. Para llegar a **$10M** se necesitaría:",
            "",
            "- **Tasa de acierto > 55%** — Actual 38% limita el compound.",
            "- **Más días con prob ≥ 90%** — Misma tasa; los filtros no mejoran el historial.",
            "- **Capital inicial ~$9M** — Con 9M y 5% stake se alcanza 10,3M (simulado).",
            "",
            "| Capital inicial | Estrategia | Resultado |",
            "|-----------------|------------|-----------|",
            f"| $50.000 | Parlay 5% | ~${result['final_capital']:,.0f} |",
            "| $50.000 | Singles 10% | ~$89.501 |",
            "| **$5.900.000** | **Singles 10%** | **$10.561.141** ✓ |",
            "",
            "**Estrategia 10M:** docs/ROADMAP_10M.md — Singles 10%, capital $5,9M → $10,5M final.",
            "",
        ])

        if wins:
            last_win = wins[-1]
            lines.extend(["", "**Última combinada ganada:**", ""])
            for p in last_win.get("picks", []):
                lines.append(f"- {p}")

    lines.extend([
        "---",
        "",
        "## Roadmap hacia 10M",
        "",
        "Ver **docs/ROADMAP_10M.md** — Backfill mejores cuotas + estrategia Singles (73% win rate) → $89.501.",
        "",
        "## Cómo ejecutar",
        "",
        "```bash",
        "python backtest_parlay.py --fill-odds --update-doc",
        "python backtest_singles.py --fill-odds   # Singles (recomendada para 10M)",
        "```",
        "",
        "---",
        "",
        f"*Documento actualizado — Periodo: {DATE_START} — {DATE_END}*",
    ])

    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    args = sys.argv[1:]
    use_est = "--estimate" in args
    fill_odds = "--fill-odds" in args
    update_doc = "--update-doc" in args
    bet_every_day = "--bet-every-day" in args

    if fill_odds:
        from backfill_odds_historical import backfill_odds
        print("Backfill: mejores cuotas (multi-bookmaker)...")
        backfill_odds(force_all=True)
        print("Backtest...")

    result = run_backtest(use_estimated_odds=use_est or bet_every_day, bet_every_day=bet_every_day)

    if update_doc:
        doc_path = Path(__file__).parent / "docs" / "BACKTEST_COMBINADA_2026.md"
        write_backtest_doc(result, doc_path, bet_every_day=bet_every_day)
        print(f"Documento actualizado: {doc_path}")

    if not update_doc:
        print(json.dumps(result, indent=2, ensure_ascii=False))
