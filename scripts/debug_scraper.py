"""Debug: Check what sbrscrape returns vs what's in the DB."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

import sbrscrape
import history_db
from datetime import datetime, timezone, timedelta

TZ = timezone(timedelta(hours=-5))
today = datetime.now(TZ).strftime('%Y-%m-%d')

print("SCRAPER (today, no date arg):")
sb = sbrscrape.Scoreboard(sport="NBA")
games = sb.games
print(f"  Count: {len(games)}")
for i, g in enumerate(games):
    print(f"  [{i}] {g.get('away_team','?')} @ {g.get('home_team','?')}")

print(f"\nDB predictions for {today}:")
preds = history_db.get_predictions_by_date_light(today)
print(f"  Count: {len(preds)}")
for i, p in enumerate(preds):
    print(f"  [{i}] {p.get('away_team','?')} @ {p.get('home_team','?')}")

# Also check what the generate function would do
print(f"\nScraper date used internally: default (today)")
print(f"Match? Scraper={len(games)} vs DB={len(preds)}")
if len(preds) >= len(games) and len(games) > 0:
    print("  -> generate_nba_predictions would SKIP (existing >= scraped)")
elif len(games) == 0:
    print("  -> generate_nba_predictions would SKIP (no games found)")
else:
    print("  -> generate_nba_predictions would REGENERATE")
