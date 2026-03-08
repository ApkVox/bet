import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from supabase import create_client, Client
import sqlite3
import os
from dotenv import load_dotenv
import json

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    sys.exit(1)

supabase: Client = create_client(url, key)
db_path = Path(__file__).resolve().parent.parent / "Data" / "history.db"

def migrate():
    if not db_path.exists():
        print(f"Error: Database {db_path} not found.")
        sys.exit(1)

    print(f"Migrating data from {db_path} to Supabase...")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Migrate predictions
    print("Migrating predictions (NBA)...")
    cur = conn.cursor()
    cur.execute("SELECT * FROM predictions")
    rows = cur.fetchall()
    predictions = [dict(row) for row in rows]
    
    # We remove 'id' if we want it to auto-generate, but here we can keep it or let supabase assign. Better to let Supabase assign its own ID.
    for p in predictions:
        p.pop('id', None) # remove id if present
        p.pop('home_score', None) # obsolete, causes PGRST204
        p.pop('away_score', None) # obsolete, causes PGRST204
    
    if predictions:
        # Supabase allows chunk inserting. Let's insert in chunks of 100.
        for i in range(0, len(predictions), 100):
            chunk = predictions[i:i+100]
            try:
                supabase.table('predictions').upsert(chunk, on_conflict='match_id').execute()
            except Exception as e:
                print(f"Error inserting chunk: {e}")
                
    print(f"Migrated {len(predictions)} NBA predictions.")

    # Migrate football_predictions
    print("Migrating football_predictions...")
    cur.execute("SELECT * FROM football_predictions")
    rows = cur.fetchall()
    football_preds = [dict(row) for row in rows]
    for p in football_preds:
        p.pop('id', None)

    if football_preds:
        for i in range(0, len(football_preds), 100):
            chunk = football_preds[i:i+100]
            try:
                supabase.table('football_predictions').upsert(chunk, on_conflict='match_id').execute()
            except Exception as e:
                print(f"Error inserting chunk: {e}")
                
    print(f"Migrated {len(football_preds)} football predictions.")

    # Migrate match_news
    print("Migrating match_news...")
    cur.execute("SELECT * FROM match_news")
    rows = cur.fetchall()
    news = [dict(row) for row in rows]
    for n in news:
        n.pop('id', None)
        # Parse JSON fields: key_points, injuries, raw_response
        try:
            n['key_points'] = json.loads(n['key_points']) if n['key_points'] else []
        except:
            n['key_points'] = []
            
        try:
            n['injuries'] = json.loads(n['injuries']) if n['injuries'] else []
        except:
            n['injuries'] = []
            
        try:
            n['raw_response'] = json.loads(n['raw_response']) if n['raw_response'] else {}
        except:
            n['raw_response'] = {}

    if news:
        for i in range(0, len(news), 100):
            chunk = news[i:i+100]
            try:
                supabase.table('match_news').upsert(chunk, on_conflict='match_id').execute()
            except Exception as e:
                print(f"Error inserting chunk: {e}")
                
    print(f"Migrated {len(news)} match news.")

    # Migrate daily_recommendations
    print("Migrating daily_recommendations...")
    cur.execute("SELECT * FROM daily_recommendations")
    rows = cur.fetchall()
    recs = [dict(row) for row in rows]
    for r in recs:
        r.pop('id', None)
        try:
            r['recommendations'] = json.loads(r['recommendations']) if r['recommendations'] else []
        except:
            r['recommendations'] = []

    if recs:
        for i in range(0, len(recs), 100):
            chunk = recs[i:i+100]
            try:
                supabase.table('daily_recommendations').upsert(chunk, on_conflict='date').execute()
            except Exception as e:
                print(f"Error inserting chunk: {e}")
                
    print(f"Migrated {len(recs)} daily recommendations.")

    conn.close()
    print("Migration finished successfully.")

if __name__ == "__main__":
    migrate()
