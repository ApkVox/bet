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
        "Leicester City": "Leicester",
        "Leeds United": "Leeds",
        "Norwich City": "Norwich",
        "Newcastle United": "Newcastle",
        "Wolverhampton Wanderers": "Wolves",
        "Brighton & Hove Albion": "Brighton",
        "West Ham United": "West Ham",
        "Tottenham Hotspur": "Tottenham",
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
        self.base_url = "https://onefootball.com/en/competition/premier-league-9/fixtures"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
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
        Scrapes upcoming Premier League fixtures from OneFootball.
        Returns a list of dicts:
        [
            {
                "home_team": "Team A", 
                "away_team": "Team B", 
                "time": "HH:MM", 
                "date": "YYYY-MM-DD",
                "league": "ENG-Premier League"
            }, ...
        ]
        """
        try:
            logger.info(f"Fetching fixtures from {self.base_url}")
            response = requests.get(self.base_url, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch fixtures: Status {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, "lxml")
            
            # Find match cards using the class observed in reference
            # Note: Class names like 'MatchCard_matchCard__iOv4G' might change. 
            # Ideally we look for structure, but for MVP we use the known selector.
            # OneFootball structure: it has date headers (e.g., class="Title_title__hngK1") 
            # and then lists of MatchCard_matchCard__iOv4G under them.
            # A more robust approach is to find all match cards, but also look at their parent containers or previous siblings.
            # Let's iterate through all elements that are either date headers or match cards.
            
            elements = soup.find_all(["h3", "a"])
            current_date = datetime.now().date()
            
            for elem in elements:
                if elem.name == "h3" and "Title_title" in " ".join(elem.get("class", [])):
                    # Es un header de fecha: "Today", "Tomorrow", "Saturday 27 Feb" etc.
                    date_text = elem.text.strip().lower()
                    if "today" in date_text or "hoy" in date_text:
                        current_date = datetime.now().date()
                    elif "tomorrow" in date_text or "mañana" in date_text:
                        from datetime import timedelta
                        current_date = (datetime.now() + timedelta(days=1)).date()
                    else:
                        # Para este MVP, si no es hoy o mañana, sumamos secuencialmente o usamos una lógica base
                        # Si es un header nuevo, asumimos que es un día más adelante (esto es heurística simple)
                        # Idealmente parseamos "27 Feb":
                        try:
                            # Intenta parsear fechas como "Saturday 1 Mar"
                            import re
                            match = re.search(r'\d+\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)', elem.text.strip(), re.IGNORECASE)
                            if match:
                                parsed = datetime.strptime(match.group() + f" {current_date.year}", "%d %b %Y")
                                current_date = parsed.date()
                        except:
                            pass
                    continue
                
                if elem.name == "a" and "MatchCard_matchCard__iOv4G" in " ".join(elem.get("class", [])):
                    try:
                        team_names = elem.find_all("span", class_="SimpleMatchCardTeam_simpleMatchCardTeam__name__7Ud8D")
                        if len(team_names) < 2:
                            continue
                            
                        home_raw = team_names[0].text.strip()
                        away_raw = team_names[1].text.strip()
                        
                        home_team = self.normalize_team_name(home_raw)
                        away_team = self.normalize_team_name(away_raw)
                        
                        time_elem = elem.find("span", class_="MatchCard_matchCard__status__rX10V")
                        match_time = time_elem.text.strip() if time_elem else "00:00"
                        
                        fixtures.append({
                            "home_team": home_team,
                            "away_team": away_team,
                            "home_raw": home_raw,
                            "away_raw": away_raw,
                            "time": match_time,
                            "date": str(current_date),
                            "league": "ENG-Premier League"
                        })
                        
                    except Exception as e:
                        logger.error(f"Error parsing match card: {e}")
                        continue
            
            logger.info(f"Found {len(fixtures)} fixtures")
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
