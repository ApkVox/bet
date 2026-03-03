import os
import requests

# NBA Team Abbreviations for ESPN's CDN
team_espn_codes = {
    'Atlanta Hawks': 'atl',
    'Boston Celtics': 'bos',
    'Brooklyn Nets': 'bkn',
    'Charlotte Hornets': 'cha',
    'Chicago Bulls': 'chi',
    'Cleveland Cavaliers': 'cle',
    'Dallas Mavericks': 'dal',
    'Denver Nuggets': 'den',
    'Detroit Pistons': 'det',
    'Golden State Warriors': 'gs',
    'Houston Rockets': 'hou',
    'Indiana Pacers': 'ind',
    'Los Angeles Clippers': 'lac',
    'LA Clippers': 'lac',
    'Los Angeles Lakers': 'lal',
    'Memphis Grizzlies': 'mem',
    'Miami Heat': 'mia',
    'Milwaukee Bucks': 'mil',
    'Minnesota Timberwolves': 'min',
    'New Orleans Pelicans': 'no',
    'New York Knicks': 'ny',
    'Oklahoma City Thunder': 'okc',
    'Orlando Magic': 'orl',
    'Philadelphia 76ers': 'phi',
    'Phoenix Suns': 'phx',
    'Portland Trail Blazers': 'por',
    'Sacramento Kings': 'sac',
    'San Antonio Spurs': 'sa',
    'Toronto Raptors': 'tor',
    'Utah Jazz': 'utah',
    'Washington Wizards': 'was'
}

# The target directory
OUTPUT_DIR = os.path.join("static", "img", "nba_logos")

def get_espn_logo_url(team_code):
    # ESPN provides high quality PNGs based on standard abbreviations
    return f"https://a.espncdn.com/i/teamlogos/nba/500/{team_code}.png"

def download_image(url, filename):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, stream=True)
        if response.status_code == 200:
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
        return False
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

if __name__ == "__main__":
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
    # Get unique teams (since LA Clippers is duplicated)
    unique_teams = {k: v for k, v in team_espn_codes.items() if k != 'LA Clippers'}
        
    print(f"Starting download of {len(unique_teams)} unique NBA logos from ESPN into '{OUTPUT_DIR}'...")
    
    success_count = 0
    
    for team_name, team_code in unique_teams.items():
        print(f"Fetching: {team_name}...", end=" ")
        
        logo_url = get_espn_logo_url(team_code)
        # Format filename nicely (e.g., "Los_Angeles_Lakers.png")
        filename = f"{team_name.replace(' ', '_')}.png"
        
        if download_image(logo_url, filename):
            print("Success.")
            success_count += 1
        else:
            print("Failed.")
            
    print(f"\nDone! Downloaded {success_count} logos.")
