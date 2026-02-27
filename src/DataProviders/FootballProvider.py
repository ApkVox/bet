import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FootballProvider:
    """
    Provider for fetching live Football fixtures (Premier League).
    Scrapes data from OneFootball to get real-time schedule.
    """
    
    # Mapping from OneFootball/Common names to Model Training Data names (CSV)
    # Model uses: ['Arsenal', 'Aston Villa', 'Brentford', 'Brighton', 'Burnley', 'Chelsea', ... 'Man City', 'Man United', ...]
    TEAM_MAPPING = {
        "Manchester City": "Man City",
        "Manchester United": "Man United",
        "Man Utd": "Man United",
        "Leicester City": "Leicester",
        "Leeds United": "Leeds",
        "Norwich City": "Norwich",
        "Newcastle United": "Newcastle",
        "Wolverhampton Wanderers": "Wolves",
        "Brighton & Hove Albion": "Brighton",
        "West Ham United": "West Ham",
        "Tottenham Hotspur": "Tottenham",
        "Spurs": "Tottenham",
        "Liverpool FC": "Liverpool",
        "Chelsea FC": "Chelsea",
        "Arsenal FC": "Arsenal",
        "Everton FC": "Everton",
        "Fulham FC": "Fulham",
        "Brentford FC": "Brentford",
        "Crystal Palace FC": "Crystal Palace",
        "Southampton FC": "Southampton",
        "Aston Villa FC": "Aston Villa",
        "Watford FC": "Watford",
        "Burnley FC": "Burnley",
        "Luton Town": "Luton",
        "Sheffield United": "Sheffield United",
        "AFC Bournemouth": "Bournemouth",
        "Nottingham Forest": "Nott'm Forest",
        "Sunderland AFC": "Sunderland", # Just case
        "Stoke City": "Stoke",
        "Swansea City": "Swansea",
        "Cardiff City": "Cardiff",
        "Huddersfield Town": "Huddersfield",
        "West Bromwich Albion": "West Brom"
    }

    def __init__(self):
        self.base_url = "https://fixturedownload.com/feed/json/epl-2025"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

    def normalize_team_name(self, name: str) -> str:
        """
        Normalizes team name to match strict format expected by the model.
        Returns the mapped name or the original if no map exists.
        """
        # 1. Direct mapping
        if name in self.TEAM_MAPPING:
            return self.TEAM_MAPPING[name]
        
        # 2. Heuristics (optional cleanup)
        clean_name = name.strip()
        
        return clean_name

    def get_fixtures(self) -> List[Dict]:
        """
        Fetches fixtures from fixturedownload.com JSON API.
        Automatically identifies the 'Next Matchday' (RoundNumber) 
        and strictly returns its 10 matches mapped to their precise dates.
        """
        try:
            logger.info(f"Fetching fixtures from {self.base_url}")
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch fixtures: Status {response.status_code}")
                return []

            all_matches = response.json()
            from datetime import datetime
            
            # Find all pending matches (where score is None or not played yet)
            pending_matches = [m for m in all_matches if m.get('HomeTeamScore') is None]
            
            if not pending_matches:
                logger.info("No more pending matches found for this season.")
                return []
                
            # The next matchday is the lowest RoundNumber among pending matches
            next_round = min(m['RoundNumber'] for m in pending_matches)
            
            # Filter matches belonging exclusively to exactly this matchday
            matchday_fixtures = [m for m in pending_matches if m['RoundNumber'] == next_round]
            logger.info(f"Identified Next Matchday: Round {next_round} ({len(matchday_fixtures)} matches)")
            
            fixtures = []
            
            for m in matchday_fixtures:
                home_raw = m['HomeTeam']
                away_raw = m['AwayTeam']
                
                home_team = self.normalize_team_name(home_raw)
                away_team = self.normalize_team_name(away_raw)
                
                # 'DateUtc': '2026-02-27 20:00:00Z'
                raw_date = m.get('DateUtc', '')
                try:
                    # Parse to Python datetime to split correctly
                    parsed_dt = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%SZ")
                    match_date = parsed_dt.strftime("%Y-%m-%d")
                    match_time = parsed_dt.strftime("%H:%M")
                except Exception as e:
                    logger.warning(f"Error parsing DateUtc '{raw_date}': {e}")
                    match_date = str(datetime.now().date())
                    match_time = "00:00"
                
                fixtures.append({
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_raw": home_raw,
                    "away_raw": away_raw,
                    "time": match_time,
                    "date": match_date,
                    "league": "ENG-Premier League",
                    "round": next_round
                })
                
            return fixtures

        except Exception as e:
            logger.error(f"Error in get_fixtures: {e}")
            return []

if __name__ == "__main__":
    # Test the provider
    provider = FootballProvider()
    fixtures = provider.get_fixtures()
    print(f"Fixtures found: {len(fixtures)}")
    for f in fixtures:
        print(f"{f['home_team']} vs {f['away_team']} ({f['time']})")
