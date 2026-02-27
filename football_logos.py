import requests
import logging

logger = logging.getLogger(__name__)

# ESPN's Soccer API Endpoint for English Premier League
ESPN_API_URL = "http://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams"

# In-memory cache
_TEAM_MAP_CACHE = None

def _fetch_espn_teams() -> dict:
    """
    Fetches official names and logos for Premier League teams from ESPN.
    Returns a mapping: 
    { "Normalized Name": {"name": "Official Name", "logo": "url_to_logo"} }
    """
    try:
        response = requests.get(ESPN_API_URL, timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to fetch team logos from ESPN: Status {response.status_code}")
            return {}
            
        data = response.json()
        
        # ESPN JSON Structure: data['sports'][0]['leagues'][0]['teams']
        sports = data.get('sports', [])
        if not sports:
            return {}
            
        leagues = sports[0].get('leagues', [])
        if not leagues:
            return {}
            
        teams = leagues[0].get('teams', [])
        
        team_map = {}
        for t in teams:
            team_info = t.get('team', {})
            name = team_info.get('name', 'Unknown')
            logos = team_info.get('logos', [])
            logo_url = logos[0].get('href', '') if logos else ''
            
            # Map ESPN's full names (e.g. Manchester City) to our normalized dataset names (e.g. Man City)
            # using the existing logic in FootballProvider
            normalized_name = normalize_espn_name_to_model(name)
            
            # We store the genuine full name for display and the logo URL
            team_map[normalized_name] = {
                "name": name,
                "logo": logo_url
            }
            
        return team_map
    except Exception as e:
        logger.error(f"Exception fetching ESPN logos: {e}")
        return {}


def normalize_espn_name_to_model(espn_name: str) -> str:
    """ Maps ESPN name format to our CSV Model formats """
    mapping = {
        "Manchester City": "Man City",
        "Manchester United": "Man United",
        "Leicester City": "Leicester",
        "Leeds United": "Leeds",
        "Norwich City": "Norwich",
        "Newcastle United": "Newcastle",
        "Wolverhampton Wanderers": "Wolves",
        "Brighton & Hove Albion": "Brighton",
        "West Ham United": "West Ham",
        "Tottenham Hotspur": "Tottenham",
        "Liverpool": "Liverpool",
        "Chelsea": "Chelsea",
        "Arsenal": "Arsenal",
        "Everton": "Everton",
        "Fulham": "Fulham",
        "Brentford": "Brentford",
        "Crystal Palace": "Crystal Palace",
        "Southampton": "Southampton",
        "Aston Villa": "Aston Villa",
        "Watford": "Watford",
        "Burnley": "Burnley",
        "Luton Town": "Luton",
        "Sheffield United": "Sheffield United",
        "AFC Bournemouth": "Bournemouth",
        "Nottingham Forest": "Nott'm Forest",
        "Sunderland AFC": "Sunderland",
        "Ipswich Town": "Ipswich",
    }
    return mapping.get(espn_name, espn_name)


def get_team_info(model_name: str) -> dict:
    """
    Returns dict mapping the internal model_name to authentic {name, logo, alt_logo}
    """
    global _TEAM_MAP_CACHE
    if _TEAM_MAP_CACHE is None:
        _TEAM_MAP_CACHE = _fetch_espn_teams()
        
    return _TEAM_MAP_CACHE.get(model_name, {
        "name": model_name,
        "logo": None 
    })
