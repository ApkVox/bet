import json
import sys
import os

# Add src to path if needed (but we use sbrscrape library)
try:
    from sbrscrape import Scoreboard
    
    sb = Scoreboard(sport="NBA")
    games = sb.games if hasattr(sb, 'games') else []
    
    # Transform to our format
    formatted_games = []
    
    # We need to replicate the logic from SbrOddsProvider roughly or just dump what we have
    # But main.py expects specific format.
    # Let's verify what SbrOddsProvider does.
    # It returns a dict: { "Home:Away": { ... } }
    
    dict_res = {}
    sportsbook = "fanduel"
    
    for game in games:
        # Get team names
        home_team_name = game['home_team'].replace("Los Angeles Clippers", "LA Clippers")
        away_team_name = game['away_team'].replace("Los Angeles Clippers", "LA Clippers")

        money_line_home_value = money_line_away_value = totals_value = None

        # Get money line bet values
        if sportsbook in game['home_ml']:
            money_line_home_value = game['home_ml'][sportsbook]
        if sportsbook in game['away_ml']:
            money_line_away_value = game['away_ml'][sportsbook]

        # Get totals bet value
        if sportsbook in game['total']:
            totals_value = game['total'][sportsbook]

        dict_res[home_team_name + ':' + away_team_name] = {
            'under_over_odds': totals_value,
            'home_score': game.get('home_score'),
            'away_score': game.get('away_score'),
            'status': game.get('status'),
            home_team_name: {'money_line_odds': money_line_home_value},
            away_team_name: {'money_line_odds': money_line_away_value}
        }
            
    print(json.dumps(dict_res))
    
except Exception as e:
    # Print error to stderr so stdout remains clean or empty
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
