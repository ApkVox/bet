"""
Backtest: Apuestas SIMPLES (1 pick por vez).

Estrategia:
- Backfill: mejores cuotas (bet365, betmgm, draftkings, etc.)
- Singles: 3 picks/día como apuestas independientes
- Stake: 10% por pick | Min prob: 80%
- Capital inicial: $50.000 → ~$90k

Para meta 10M: python backtest_singles.py --fill-odds --capital 5900000
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
STAKE_PER_PICK = 0.10  # 10% por pick (óptimo)
MIN_PROB = 0.80


def _score_prediction(pred: dict) -> float:
    prob = pred.get("win_probability") or pred.get("prob_final") or 0
    ev = pred.get("ev_score") or pred.get("ev_value") or 0
    warning = (pred.get("warning_level") or "NORMAL").upper()
    if warning == "HIGH":
        return -1
    winner = pred.get("winner") or pred.get("predicted_winner")
    odds_winner = pred.get("odds_home") if winner == pred.get("home_team") else pred.get("odds_away")
    odds_bonus = min(odds_winner / 5.0, 0.5) if (odds_winner and odds_winner > 0) else 0
    return (prob * 0.70) + (max(ev, 0) * 0.20) + (odds_bonus * 0.10)


def select_top3(predictions: list[dict]) -> list[dict]:
    scored = []
    for p in predictions:
        prob = p.get("win_probability") or p.get("prob_final") or 0
        if prob < MIN_PROB:
            continue
        s = _score_prediction(p)
        if s > 0:
            scored.append((s, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:3]]


def run_backtest(initial_capital: int | None = None) -> dict:
    cap = initial_capital if initial_capital is not None else INITIAL_CAPITAL
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT date, match_id, home_team, away_team, predicted_winner,
               prob_final, ev_value, warning_level, result, odds_home, odds_away
        FROM predictions
        WHERE date >= ? AND date <= ?
        ORDER BY date
    """, (DATE_START, DATE_END))
    rows = cursor.fetchall()

    by_date = {}
    for r in rows:
        date_str = r[0]
        if date_str not in by_date:
            by_date[date_str] = []
        by_date[date_str].append({
            "match_id": r[1], "home_team": r[2], "away_team": r[3],
            "winner": r[4], "predicted_winner": r[4],
            "win_probability": r[5] or 0, "ev_score": r[6], "ev_value": r[6],
            "warning_level": r[7] or "NORMAL", "result": r[8],
            "odds_home": r[9], "odds_away": r[10],
        })

    capital = cap
    history = []
    total_bets = 0
    wins = 0
    losses = 0

    for date_str in sorted(by_date.keys()):
        preds = by_date[date_str]
        picks = select_top3(preds)

        for p in picks:
            if p["result"] not in ("WIN", "LOSS"):
                continue
            odds = p.get("odds_home") if p["winner"] == p["home_team"] else p.get("odds_away")
            if not odds or float(odds) <= 0:
                continue

            stake = round(capital * STAKE_PER_PICK, 2)
            if stake < 100:
                continue

            total_bets += 1
            if p["result"] == "WIN":
                ret = round(stake * float(odds), 2)
                capital = round(capital - stake + ret, 2)
                wins += 1
                history.append({
                    "date": date_str, "action": "bet", "result": "WIN",
                    "stake": stake, "odds": float(odds), "return": ret,
                    "capital": capital, "pick": f"{p['away_team']} @ {p['home_team']} -> {p['winner']}",
                })
            else:
                capital = round(capital - stake, 2)
                losses += 1
                history.append({
                    "date": date_str, "action": "bet", "result": "LOSS",
                    "stake": stake, "odds": float(odds), "return": 0,
                    "capital": capital, "pick": f"{p['away_team']} @ {p['home_team']} -> {p['winner']}",
                })

    conn.close()
    win_rate = (wins / total_bets * 100) if total_bets else 0
    return {
        "initial_capital": cap,
        "final_capital": capital,
        "total_return_pct": ((capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100) if INITIAL_CAPITAL else 0,
        "total_bets": total_bets,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": win_rate,
        "strategy": "singles",
        "history": history,
    }


if __name__ == "__main__":
    if "--fill-odds" in sys.argv:
        from backfill_odds_historical import backfill_odds
        print("Backfill: mejores cuotas (multi-bookmaker)...")
        backfill_odds(force_all=True)
        print("Backtest singles...")

    # Permitir capital por argumento: python backtest_singles.py --capital 50000
    cap_arg = INITIAL_CAPITAL
    if "--capital" in sys.argv:
        idx = sys.argv.index("--capital")
        if idx + 1 < len(sys.argv):
            cap_arg = int(sys.argv[idx + 1])

    result = run_backtest(initial_capital=cap_arg)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["final_capital"] >= 10_000_000:
        print("\n*** META 10M ALCANZADA ***")
