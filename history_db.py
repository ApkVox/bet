import os
import json
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv

# Fake DB_PATH for compatibility with existing code that prints it
DB_PATH = "Supabase (Cloud)"

# Load environment variables
load_dotenv()

# We only initialize supabase if the keys are present
_supabase_client = None

def _get_supabase():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
        
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("[WARNING] SUPABASE_URL or SUPABASE_KEY not set. Data persistence will fail.")
        return None
        
    try:
        from supabase import create_client, Client
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception as e:
        print(f"[ERROR] Failed to initialize Supabase client: {e}")
        return None


def _truncate_data(data: dict, max_len: int = 5000) -> dict:
    """Evita errores 413 truncando campos de texto largos."""
    if not isinstance(data, dict): return data
    new_data = data.copy()
    for k, v in new_data.items():
        if isinstance(v, str) and len(v) > max_len:
            new_data[k] = v[:max_len] + "..."
        elif isinstance(v, list):
            new_data[k] = [x[:1000] + "..." if isinstance(x, str) and len(x) > 1000 else x for x in v]
    return new_data


def init_history_db():
    """No-op for Supabase. Tables are managed via Supabase SQL Editor."""
    client = _get_supabase()
    if client:
        print("[OK] Supabase client initialized")
    else:
        print("[ERROR] Could not initialize Supabase connection.")


def save_prediction(prediction_data: dict):
    client = _get_supabase()
    if not client: return
    
    data = {
        'date': prediction_data['date'],
        'match_id': prediction_data['match_id'],
        'home_team': prediction_data['home_team'],
        'away_team': prediction_data['away_team'],
        'predicted_winner': prediction_data['winner'],
        'prob_model': prediction_data['win_probability'],
        'prob_final': prediction_data['win_probability'],
        'odds': prediction_data['market_odds'],
        'ev_value': prediction_data['ev_value'],
        'kelly_stake': prediction_data['kelly_stake_pct'],
        'warning_level': prediction_data['warning_level'],
        'odds_home': prediction_data.get('home_odds'),
        'odds_away': prediction_data.get('away_odds'),
        'result': 'PENDING'
    }
    try:
        client.table('predictions').upsert(data, on_conflict='match_id').execute()
    except Exception as e:
        print(f"[DB ERROR] save_prediction: {e}")


def save_historical_prediction(prediction_data: dict):
    client = _get_supabase()
    if not client: return
    
    data = {
        'date': prediction_data['date'],
        'match_id': prediction_data['match_id'],
        'home_team': prediction_data['home_team'],
        'away_team': prediction_data['away_team'],
        'predicted_winner': prediction_data['winner'],
        'prob_model': prediction_data['win_probability'],
        'prob_final': prediction_data['win_probability'],
        'odds': prediction_data['market_odds'],
        'ev_value': prediction_data['ev_value'],
        'kelly_stake': prediction_data['kelly_stake_pct'],
        'warning_level': prediction_data['warning_level'],
        'result': prediction_data.get('result', 'PENDING'),
        'profit': prediction_data.get('profit', 0.0)
    }
    try:
        client.table('predictions').upsert(data, on_conflict='match_id').execute()
    except Exception as e:
        print(f"[DB ERROR] save_historical_prediction: {e}")


def update_results(date: str, results: dict):
    """Actualiza resultados reales y calcula profit."""
    client = _get_supabase()
    if not client: return

    for match_id, actual_winner in results.items():
        try:
            res = client.table('predictions').select('kelly_stake, odds, predicted_winner, odds_home, odds_away, home_team').eq('date', date).eq('match_id', match_id).execute()
            
            if not res.data:
                continue
            
            row = res.data[0]
            kelly_stake = row.get('kelly_stake') or 0
            odds_american = row.get('odds')
            predicted_winner = row.get('predicted_winner')
            odds_home = row.get('odds_home')
            odds_away = row.get('odds_away')
            home_team = row.get('home_team')
            
            is_win = (predicted_winner == actual_winner)
            
            profit = 0
            if is_win:
                decimal_odds = odds_home if predicted_winner == home_team else odds_away
                if decimal_odds and decimal_odds > 1:
                    profit = kelly_stake * (decimal_odds - 1)
                elif odds_american:
                    am = float(odds_american)
                    profit = kelly_stake * (am / 100) if am > 0 else kelly_stake * (100 / abs(am))
            else:
                profit = -kelly_stake
                
            _update_prediction_result(date, match_id, is_win, profit)
        except Exception as e:
            print(f"[DB ERROR] update_results on match {match_id}: {e}")


def delete_football_history():
    """Borra todo el historial de predicciones de fútbol."""
    client = _get_supabase()
    if not client: return
    try:
        # Borrar todo
        client.table('football_predictions').delete().neq('match_id', 'FORCE_DELETE_ALL').execute()
        print("✅ Historial de fútbol eliminado correctamente.")
    except Exception as e:
        print(f"[DB ERROR] delete_football_history: {e}")


def save_football_prediction(prediction_data: dict, match_id: str, date: str):
    client = _get_supabase()
    if not client: return
    
    probs = prediction_data.get('probs', {})
    data = {
        'date': date,
        'league': prediction_data.get('league', 'ENG-Premier League'),
        'match_id': match_id,
        'home_team': prediction_data['home_team'],
        'away_team': prediction_data['away_team'],
        'prediction': prediction_data['prediction'],
        'prob_home': probs.get('home', 0),
        'prob_draw': probs.get('draw', 0),
        'prob_away': probs.get('away', 0),
        'result': 'PENDING'
    }
    try:
        client.table('football_predictions').upsert(data, on_conflict='match_id').execute()
    except Exception as e:
        print(f"[DB ERROR] save_football_prediction: {e}")


def get_football_history(days: int = 30) -> list[dict]:
    client = _get_supabase()
    if not client: return []
    
    date_threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    try:
        res = client.table('football_predictions')\
            .select('*')\
            .gte('date', date_threshold)\
            .order('date', desc=True)\
            .order('created_at', desc=True)\
            .execute()
        
        return [
            {
                "date": row['date'],
                "league": row.get('league'),
                "match_id": row['match_id'],
                "home_team": row['home_team'],
                "away_team": row['away_team'],
                "prediction": row['prediction'],
                "probs": {
                    "home": row.get('prob_home', 0),
                    "draw": row.get('prob_draw', 0),
                    "away": row.get('prob_away', 0)
                },
                "result": row.get('result'),
                "created_at": row.get('created_at')
            }
            for row in res.data
        ]
    except Exception as e:
        print(f"[DB ERROR] get_football_history: {e}")
        return []


def get_history(days: int = 7) -> list[dict]:
    client = _get_supabase()
    if not client: return []
    
    date_threshold = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    try:
        res = client.table('predictions')\
            .select('date, match_id, home_team, away_team, predicted_winner, prob_final, odds, ev_value, kelly_stake, result, profit')\
            .gte('date', date_threshold)\
            .order('date', desc=True)\
            .execute()
            
        return [
            {
                "date": row['date'],
                "match": row['match_id'],
                "home_team": row['home_team'],
                "away_team": row['away_team'],
                "predicted_winner": row['predicted_winner'],
                "probability": row['prob_final'],
                "odds": row['odds'],
                "ev": row['ev_value'],
                "kelly_stake": row['kelly_stake'],
                "result": row['result'],
                "profit": row.get('profit', 0)
            }
            for row in res.data
        ]
    except Exception as e:
        print(f"[DB ERROR] get_history: {e}")
        return []


def get_team_prediction_accuracy(team_name: str) -> dict:
    client = _get_supabase()
    if not client: return {"team": team_name, "total_bets": 0, "wins": 0, "accuracy": 0}
    
    try:
        res = client.table('predictions')\
            .select('result')\
            .neq('result', 'PENDING')\
            .or_(f"home_team.ilike.%{team_name}%,away_team.ilike.%{team_name}%")\
            .execute()
            
        total = len(res.data)
        wins = sum(1 for row in res.data if row['result'] == 'WIN')
        
        return {
            "team": team_name,
            "total_bets": total,
            "wins": wins,
            "accuracy": round((wins / total * 100) if total > 0 else 0, 1)
        }
    except Exception as e:
        print(f"[DB ERROR] get_team_prediction_accuracy: {e}")
        return {"team": team_name, "total_bets": 0, "wins": 0, "accuracy": 0}


def get_predictions_by_date_light(date: str) -> list[dict]:
    client = _get_supabase()
    if not client: return []
    
    try:
        res = client.table('predictions')\
            .select('date, match_id, home_team, away_team, predicted_winner, prob_final, odds, ev_value, kelly_stake, warning_level, result, odds_home, odds_away')\
            .eq('date', date)\
            .execute()
            
        predictions = []
        for row in res.data:
            p = {
                "match_id": row['match_id'],
                "home_team": row['home_team'],
                "away_team": row['away_team'],
                "winner": row['predicted_winner'],
                "win_probability": row['prob_final'] or 0,
                "under_over": "N/A",
                "ou_line": 0,
                "ou_probability": 0,
                "ai_analysis": None,
                "is_mock": False,
                "odds_home": row.get('odds_home'),
                "odds_away": row.get('odds_away'),
                "ev_score": row['ev_value'],
                "kelly_stake": row['kelly_stake'],
                "warning_level": row.get('warning_level'),
                "game_status": row.get('result'),
                "home_score": None,
                "away_score": None,
                "implied_prob": None,
                "discrepancy": None,
                "value_type": None,
                "sentiment_score": None,
                "key_injuries": None,
                "risk_analysis": None
            }
            predictions.append(p)
        return predictions
    except Exception as e:
        print(f"[DB ERROR] get_predictions_by_date_light: {e}")
        return []


def get_predictions_by_date(date: str) -> list[dict]:
    client = _get_supabase()
    if not client: return []
    
    try:
        res = client.table('predictions')\
            .select('date, match_id, home_team, away_team, predicted_winner, prob_final, odds, ev_value, kelly_stake, warning_level, result')\
            .eq('date', date)\
            .execute()
            
        predictions = []
        for row in res.data:
            p = {
                "date": row['date'],
                "match_id": row['match_id'],
                "home_team": row['home_team'],
                "away_team": row['away_team'],
                "winner": row['predicted_winner'],
                "win_probability": row['prob_final'],
                "market_odds_home": row['odds'] if row['predicted_winner'] == row['home_team'] else 0,
                "market_odds_away": row['odds'] if row['predicted_winner'] == row['away_team'] else 0,
                "ev_value": row['ev_value'],
                "kelly_stake_pct": row['kelly_stake'],
                "warning_level": row.get('warning_level'),
                "result": row.get('result')
            }
            predictions.append(p)
        return predictions
    except Exception as e:
        print(f"[DB ERROR] get_predictions_by_date: {e}")
        return []


def delete_predictions_for_date(date: str) -> int:
    client = _get_supabase()
    if not client: return 0
    try:
        res = client.table('predictions').delete().eq('date', date).eq('result', 'PENDING').execute()
        deleted = len(res.data) if res.data else 0
        print(f"[DB] Deleted {deleted} stale predictions for {date}")
        return deleted
    except Exception as e:
        print(f"[DB ERROR] delete_predictions_for_date: {e}")
        return 0


def get_team_recent_results(team_name: str, limit: int = 5) -> list:
    client = _get_supabase()
    if not client: return []
    try:
        res = client.table('predictions')\
            .select('date, match_id, predicted_winner, result')\
            .neq('result', 'PENDING')\
            .or_(f"home_team.ilike.%{team_name}%,away_team.ilike.%{team_name}%")\
            .order('date', desc=True)\
            .limit(limit)\
            .execute()
            
        return [
            {
                "date": row['date'],
                "match": row['match_id'],
                "predicted_winner": row['predicted_winner'],
                "result": row['result']
            }
            for row in res.data
        ]
    except Exception as e:
        print(f"[DB ERROR] get_team_recent_results: {e}")
        return []


def get_upcoming_football_predictions() -> list[dict]:
    client = _get_supabase()
    if not client: return []
    date_now = datetime.now().strftime('%Y-%m-%d')
    try:
        res = client.table('football_predictions')\
            .select('date, league, match_id, home_team, away_team, prediction, prob_home, prob_draw, prob_away, result, created_at')\
            .gte('date', date_now)\
            .eq('result', 'PENDING')\
            .order('date', desc=False)\
            .order('created_at', desc=True)\
            .execute()
            
        return [
            {
                "date": row['date'],
                "league": row.get('league'),
                "match_id": row['match_id'],
                "home_team": row['home_team'],
                "away_team": row['away_team'],
                "prediction": row['prediction'],
                "probs": {
                    "home": row.get('prob_home', 0),
                    "draw": row.get('prob_draw', 0),
                    "away": row.get('prob_away', 0)
                },
                "confidence_modifier": row.get('confidence_modifier', 'neutral'),
                "result": row['result'],
                "created_at": row.get('created_at')
            }
            for row in res.data
        ]
    except Exception as e:
        print(f"[DB ERROR] get_upcoming_football_predictions: {e}")
        return []


def update_prediction_odds(match_id: str, odds_home: float, odds_away: float) -> None:
    client = _get_supabase()
    if not client: return
    try:
        # Supabase update syntax: we only want to update if they are null.
        # We can fetch first or just do an update (which might overwrite if not careful).
        # Let's fetch first to check if they are null.
        res = client.table('predictions').select('odds_home, odds_away').eq('match_id', match_id).execute()
        if res.data:
            row = res.data[0]
            if row.get('odds_home') is None or row.get('odds_away') is None:
                client.table('predictions').update({'odds_home': odds_home, 'odds_away': odds_away}).eq('match_id', match_id).execute()
    except Exception as e:
        print(f"[DB ERROR] update_prediction_odds: {e}")


def get_all_prediction_dates() -> dict:
    client = _get_supabase()
    if not client: return {}
    try:
        # Supabase currently lacks simple GROUP BY in restful API without creating a view/rpc.
        # So we fetch all dates and count them.
        res = client.table('predictions').select('date').execute()
        counts = {}
        for row in res.data:
            d = row['date']
            counts[d] = counts.get(d, 0) + 1
        return counts
    except Exception as e:
        print(f"[DB ERROR] get_all_prediction_dates: {e}")
        return {}


def get_match_ids_for_date(date: str) -> set:
    client = _get_supabase()
    if not client: return set()
    try:
        res = client.table('predictions').select('match_id').eq('date', date).execute()
        return {row['match_id'] for row in res.data}
    except Exception as e:
        print(f"[DB ERROR] get_match_ids_for_date: {e}")
        return set()


# =============================================
# MATCH NEWS
# =============================================

def save_match_news(date: str, match_id: str, news_data: dict) -> None:
    client = _get_supabase()
    if not client: return
    
    # Extraer el deporte de news_data o por defecto nba
    sport = news_data.get('sport', 'nba')
    
    data = {
        'date': date,
        'match_id': match_id,
        'sport': sport,
        'headline': news_data.get('headline', ''),
        'key_points': news_data.get('key_points', []),
        'injuries': news_data.get('injuries', []),
        'impact_assessment': news_data.get('impact_assessment', ''),
        'confidence_modifier': news_data.get('confidence_modifier', 'neutral'),
        'raw_response': news_data
    }
    data = _truncate_data(data)
    try:
        client.table('match_news').upsert(data, on_conflict='match_id').execute()
    except Exception as e:
        print(f"[DB ERROR] save_match_news: {e}")


def get_match_news(match_id: str) -> Optional[dict]:
    client = _get_supabase()
    if not client: return None
    try:
        res = client.table('match_news').select('*').eq('match_id', match_id).execute()
        if not res.data: return None
        row = res.data[0]
        return {
            "headline": row.get('headline'),
            "key_points": row.get('key_points', []),
            "injuries": row.get('injuries', []),
            "impact_assessment": row.get('impact_assessment'),
            "confidence_modifier": row.get('confidence_modifier'),
            "updated_at": (row.get('created_at') or "").replace('T', ' ')[:19],
            "created_at": row.get('created_at')
        }
    except Exception as e:
        print(f"[DB ERROR] get_match_news: {e}")
        return None


def get_news_for_date(date: str) -> list[dict]:
    client = _get_supabase()
    if not client: return []
    try:
        res = client.table('match_news').select('*').eq('date', date).execute()
        return [
            {
                "match_id": row['match_id'],
                "headline": row.get('headline'),
                "key_points": row.get('key_points', []),
                "injuries": row.get('injuries', []),
                "impact_assessment": row.get('impact_assessment'),
                "confidence_modifier": row.get('confidence_modifier'),
                "updated_at": (row.get('created_at') or "").replace('T', ' ')[:19],
                "created_at": row.get('created_at')
            }
            for row in res.data
        ]
    except Exception as e:
        print(f"[DB ERROR] get_news_for_date: {e}")
        return []


def news_exist_for_date(date: str) -> bool:
    client = _get_supabase()
    if not client: return False
    try:
        res = client.table('match_news').select('id', count='exact').eq('date', date).limit(1).execute()
        return res.count > 0
    except Exception as e:
        print(f"[DB ERROR] news_exist_for_date: {e}")
        return False


# =============================================
# DAILY RECOMMENDATIONS
# =============================================

def save_daily_recommendations(date: str, reco_data: dict) -> None:
    client = _get_supabase()
    if not client: return
    data = {
        'date': date,
        'sport': 'nba',
        'recommendations': reco_data.get('recommendations', []),
        'parlay_analysis': reco_data.get('parlay_analysis', ''),
        'parlay_odds': reco_data.get('parlay_odds', 0.0),
        'reasoning': reco_data.get('reasoning', ''),
        'result': 'pending'
    }
    data = _truncate_data(data)
    try:
        client.table('daily_recommendations').upsert(data, on_conflict='date').execute()
    except Exception as e:
        print(f"[DB ERROR] save_daily_recommendations: {e}")


def get_daily_recommendations(date: str) -> Optional[dict]:
    client = _get_supabase()
    if not client: return None
    try:
        res = client.table('daily_recommendations').select('*').eq('date', date).execute()
        if not res.data: return None
        row = res.data[0]
        return {
            "recommendations": row.get('recommendations', []),
            "parlay_analysis": row.get('parlay_analysis'),
            "parlay_odds": row.get('parlay_odds'),
            "created_at": row.get('created_at'),
            "reasoning": row.get('reasoning', ''),
            "result": row.get('result', 'pending')
        }
    except Exception as e:
        print(f"[DB ERROR] get_daily_recommendations: {e}")
        return None


def get_recommendations_history(limit: int = 14) -> list[dict]:
    client = _get_supabase()
    if not client: return []
    try:
        res = client.table('daily_recommendations').select('*').order('date', desc=True).limit(limit).execute()
        return [
            {
                "date": row['date'],
                "recommendations": row.get('recommendations', []),
                "parlay_analysis": row.get('parlay_analysis'),
                "parlay_odds": row.get('parlay_odds'),
                "created_at": row.get('created_at'),
                "result": row.get('result', 'pending')
            }
            for row in res.data
        ]
    except Exception as e:
        print(f"[DB ERROR] get_recommendations_history: {e}")
        return []


def delete_daily_recommendations(date: str) -> None:
    client = _get_supabase()
    if not client: return
    try:
        client.table('daily_recommendations').delete().eq('date', date).execute()
    except Exception as e:
        print(f"[DB ERROR] delete_daily_recommendations: {e}")


def update_recommendation_result(date: str, result: str) -> None:
    client = _get_supabase()
    if not client: return
    try:
        client.table('daily_recommendations').update({'result': result}).eq('date', date).execute()
    except Exception as e:
        print(f"[DB ERROR] update_recommendation_result: {e}")
