"""
Backfill: Obtiene cuotas reales desde sbrscrape para predicciones sin cuotas
desde 2026-01-01 hasta hoy. Usa las MEJORES cuotas entre todos los bookmakers
(bet365, betmgm, draftkings, etc.) para maximizar payout cuando ganamos.
"""
import sqlite3
import sbrscrape
from datetime import date
from pathlib import Path

from generate_daily_job import american_to_decimal

DB_PATH = Path(__file__).parent / "Data" / "history.db"
TODAY = date.today().isoformat()
BOOKMAKERS = ["bet365", "betmgm", "draftkings", "fanduel", "caesars", "fanatics"]


def normalize_team(name: str) -> str:
    return name.replace("Los Angeles Clippers", "LA Clippers")


def get_best_odds(odds_data) -> float | None:
    """Devuelve la MEJOR cuota decimal entre todos los bookmakers (mayor payout)."""
    if not isinstance(odds_data, dict) or not odds_data:
        return american_to_decimal(odds_data) if odds_data else None
    best = None
    for book in BOOKMAKERS:
        val = odds_data.get(book)
        if val is not None:
            dec = american_to_decimal(val)
            if dec and (best is None or dec > best):
                best = dec
    if best is None:
        for val in odds_data.values():
            dec = american_to_decimal(val)
            if dec and (best is None or dec > best):
                best = dec
    return round(best, 3) if best else None


def backfill_odds(verbose: bool = True, force_all: bool = False):
    """Rellena cuotas desde sbrscrape. force_all=True procesa TODAS las fechas (para actualizar a best odds)."""
    conn = sqlite3.connect(DB_PATH)
    if force_all:
        cursor = conn.execute("""
            SELECT DISTINCT date FROM predictions
            WHERE date >= '2026-01-01' AND date <= ?
            ORDER BY date
        """, (TODAY,))
    else:
        cursor = conn.execute("""
            SELECT DISTINCT date FROM predictions
            WHERE date >= '2026-01-01' AND date <= ?
              AND (odds_home IS NULL OR odds_away IS NULL)
            ORDER BY date
        """, (TODAY,))
    dates = [r[0] for r in cursor.fetchall()]

    if verbose and not dates and not force_all:
        print("Todas las predicciones ya tienen cuotas.")
        conn.close()
        return 0

    total_updated = 0
    prev_changes = conn.total_changes
    for date_str in dates:
        try:
            board = sbrscrape.Scoreboard(sport="NBA", date=date_str)
            games = getattr(board, "games", [])
            if not games:
                continue

            for g in games:
                home_raw = g["home_team"]
                away_raw = g["away_team"]
                home = normalize_team(home_raw)
                away = normalize_team(away_raw)
                match_id = f"{date_str}_{away}_{home}".replace(" ", "_")

                home_dec = get_best_odds(g.get("home_ml"))
                away_dec = get_best_odds(g.get("away_ml"))

                if home_dec and away_dec:
                    # Intentar por match_id (formato date_away_home)
                    conn.execute("""
                        UPDATE predictions SET odds_home = ?, odds_away = ?
                        WHERE match_id = ?
                    """, (home_dec, away_dec, match_id))
                    # Si no coincide, intentar por date + equipos (formato legacy "Home vs Away")
                    if conn.total_changes == prev_changes:
                        conn.execute("""
                            UPDATE predictions SET odds_home = ?, odds_away = ?
                            WHERE date = ? AND home_team = ? AND away_team = ?
                        """, (home_dec, away_dec, date_str, home, away))
                    if conn.total_changes > prev_changes:
                        total_updated += 1
                        prev_changes = conn.total_changes

            conn.commit()
            if verbose:
                print(f"  {date_str}: {len(games)} partidos procesados")

        except Exception as e:
            if verbose:
                print(f"  {date_str}: Error - {e}")

    conn.close()
    if verbose:
        print(f"\nTotal actualizaciones: {total_updated}")
    return total_updated


if __name__ == "__main__":
    import sys
    force = "--all" in sys.argv
    print(f"Backfill de cuotas desde sbrscrape (2026-01-01 hasta {TODAY})...")
    if force:
        print("Modo: actualizar TODAS las fechas con mejores cuotas (multi-bookmaker)")
    backfill_odds(force_all=force)
    print("Listo.")
