import requests
import logging

logger = logging.getLogger(__name__)

# ESPN's Soccer API Endpoint for English Premier League
ESPN_API_URL = "http://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams"

# Fallback: nombre completo + escudo oficial Premier League (cuando ESPN falla o no devuelve logo)
# Clave = nombre normalizado del modelo (FootballProvider). Valor = nombre para mostrar + URL badge.
_PL_BADGE_BASE = "https://resources.premierleague.com/premierleague/badges/50"
FALLBACK_TEAM_INFO = {
    "Man City": {"name": "Manchester City", "logo": f"{_PL_BADGE_BASE}/t43.png"},
    "Man United": {"name": "Manchester United", "logo": f"{_PL_BADGE_BASE}/t1.png"},
    "Man Utd": {"name": "Manchester United", "logo": f"{_PL_BADGE_BASE}/t1.png"},
    "Tottenham": {"name": "Tottenham Hotspur", "logo": f"{_PL_BADGE_BASE}/t6.png"},
    "Spurs": {"name": "Tottenham Hotspur", "logo": f"{_PL_BADGE_BASE}/t6.png"},
    "Leicester": {"name": "Leicester City", "logo": f"{_PL_BADGE_BASE}/t13.png"},
    "Leeds": {"name": "Leeds United", "logo": f"{_PL_BADGE_BASE}/t2.png"},
    "Norwich": {"name": "Norwich City", "logo": f"{_PL_BADGE_BASE}/t45.png"},
    "Newcastle": {"name": "Newcastle United", "logo": f"{_PL_BADGE_BASE}/t4.png"},
    "Wolves": {"name": "Wolverhampton Wanderers", "logo": f"{_PL_BADGE_BASE}/t39.png"},
    "Brighton": {"name": "Brighton & Hove Albion", "logo": f"{_PL_BADGE_BASE}/t36.png"},
    "West Ham": {"name": "West Ham United", "logo": f"{_PL_BADGE_BASE}/t21.png"},
    "Liverpool": {"name": "Liverpool", "logo": f"{_PL_BADGE_BASE}/t14.png"},
    "Chelsea": {"name": "Chelsea", "logo": f"{_PL_BADGE_BASE}/t8.png"},
    "Arsenal": {"name": "Arsenal", "logo": f"{_PL_BADGE_BASE}/t3.png"},
    "Everton": {"name": "Everton", "logo": f"{_PL_BADGE_BASE}/t11.png"},
    "Fulham": {"name": "Fulham", "logo": f"{_PL_BADGE_BASE}/t54.png"},
    "Brentford": {"name": "Brentford", "logo": f"{_PL_BADGE_BASE}/t94.png"},
    "Crystal Palace": {"name": "Crystal Palace", "logo": f"{_PL_BADGE_BASE}/t31.png"},
    "Southampton": {"name": "Southampton", "logo": f"{_PL_BADGE_BASE}/t20.png"},
    "Aston Villa": {"name": "Aston Villa", "logo": f"{_PL_BADGE_BASE}/t7.png"},
    "Watford": {"name": "Watford", "logo": f"{_PL_BADGE_BASE}/t57.png"},
    "Burnley": {"name": "Burnley", "logo": f"{_PL_BADGE_BASE}/t90.png"},
    "Luton": {"name": "Luton Town", "logo": f"{_PL_BADGE_BASE}/t102.png"},
    "Sheffield United": {"name": "Sheffield United", "logo": f"{_PL_BADGE_BASE}/t49.png"},
    "Bournemouth": {"name": "AFC Bournemouth", "logo": f"{_PL_BADGE_BASE}/t91.png"},
    "Nott'm Forest": {"name": "Nottingham Forest", "logo": f"{_PL_BADGE_BASE}/t17.png"},
    "Sunderland": {"name": "Sunderland AFC", "logo": f"{_PL_BADGE_BASE}/t56.png"},
    "Ipswich": {"name": "Ipswich Town", "logo": f"{_PL_BADGE_BASE}/t40.png"},
    "Stoke": {"name": "Stoke City", "logo": f"{_PL_BADGE_BASE}/t110.png"},
    "Swansea": {"name": "Swansea City", "logo": f"{_PL_BADGE_BASE}/t72.png"},
    "Cardiff": {"name": "Cardiff City", "logo": f"{_PL_BADGE_BASE}/t83.png"},
    "Huddersfield": {"name": "Huddersfield Town", "logo": f"{_PL_BADGE_BASE}/t111.png"},
    "West Brom": {"name": "West Bromwich Albion", "logo": f"{_PL_BADGE_BASE}/t35.png"},
}

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
    Returns dict with official display name and logo for the team.
    Uses ESPN API when available; otherwise fallback con nombres completos y escudos Premier League.
    """
    global _TEAM_MAP_CACHE
    if _TEAM_MAP_CACHE is None:
        _TEAM_MAP_CACHE = _fetch_espn_teams()

    # 1) Intentar datos de ESPN
    info = _TEAM_MAP_CACHE.get(model_name)
    if info and info.get("logo"):
        return {"name": info["name"], "logo": info["logo"]}

    # 2) Fallback: nombre completo + escudo oficial (Man United → Manchester United, Tottenham → Tottenham Hotspur, etc.)
    fallback = FALLBACK_TEAM_INFO.get(model_name)
    if fallback:
        return {"name": fallback["name"], "logo": fallback["logo"]}

    return {"name": model_name, "logo": None}
