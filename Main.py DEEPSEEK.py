import requests
import os
import logging
from datetime import datetime, timedelta

# ===== SET UP LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ===== CONFIGURATION =====
def get_env_var(name, required=True):
    value = os.getenv(name)
    if not value and required:
        logging.error(f"❌ Missing required environment variable: {name}")
        raise ValueError(f"Missing environment variable: {name}")
    return value.strip('"').strip("'")

try:
    ODDS_API_KEY = "7b5d540e73c8790a95b84d3713e1a572"
    SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
    TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
    TELEGRAM_CHAT_ID = "964091254"
except ValueError:
    logging.error("❌ Critical error - missing required environment variables. Exiting.")
    exit(1)

# ===== API ENDPOINTS =====
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
SPORTMONKS_API_URL = "https://api.sportmonks.com/v3/baseball/fixtures"

# ===== MLB LEAGUE ID =====
MLB_LEAGUE_ID = 1  # Major League Baseball

# ===== TEST ODDS API KEY =====
def test_odds_api_key():
    """Test Odds API key before proceeding"""
    try:
        test_url = "https://api.the-odds-api.com/v4/sports"
        response = requests.get(
            test_url,
            params={"apiKey": ODDS_API_KEY},
            timeout=10
        )
        if response.status_code == 401:
            logging.error("❌ Odds API key is invalid (401 Unauthorized)")
            return False
        response.raise_for_status()
        logging.info("✅ Odds API key validated")
        return True
    except Exception as e:
        logging.error(f"❌ Odds API test failed: {str(e)}")
        return False

# ===== FETCH MLB FIXTURE DATA =====
def get_fixture_data():
    try:
        # Get current time in UTC
        now = datetime.utcnow()
        logging.info(f"⏰ Current UTC time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Calculate date range - TODAY and TOMORROW only
        start_date = now.date()
        end_date = (now + timedelta(days=1)).date()
        
        logging.info(f"🔍 Fetching MLB fixtures from {start_date} to {end_date}...")
        
        # Fetch MLB fixtures
        response = requests.get(
            SPORTMONKS_API_URL,
            params={
                "api_token": SPORTMONKS_API_KEY,
                "include": "participants,venue",
                "per_page": 50,
                "leagues": str(MLB_LEAGUE_ID),
                "filters": "upcoming",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            },
            timeout=15
        )
        
        # Handle API errors
        if response.status_code == 401:
            logging.error("❌ SportMonks API returned 401 Unauthorized - check your API key")
            return []
        if response.status_code != 200:
            logging.error(f"⚠️ SportMonks API error: {response.status_code} - {response.text[:200]}")
            return []
        
        response.raise_for_status()
        data = response.json()
        fixtures = data.get('data', [])
        
        # Filter out games that have already started
        current_time = datetime.utcnow()
        valid_fixtures = []
        for fixture in fixtures:
            start_time_str = fixture.get('starting_at', '')
            if start_time_str:
                try:
                    # Parse fixture time (UTC format)
                    fixture_time = datetime.strptime(start_time_str.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                    if fixture_time > current_time:
                        valid_fixtures.append(fixture)
                except ValueError:
                    continue
        
        # Log some debug information
        if valid_fixtures:
            logging.info(f"📊 Found {len(valid_fixtures)} upcoming MLB fixtures")
            for fixture in valid_fixtures:
                start_time = fixture.get('starting_at', 'N/A')
                participants = fixture.get('participants', [])
                home = participants[0]['name'] if participants else 'Unknown'
                away = participants[1]['name'] if len(participants) > 1 else 'Unknown'
                logging.info(f"  ⚾ {home} vs {away} at {start_time}")
        else:
            logging.info("ℹ️ No upcoming MLB fixtures found in API response")
            
        return valid_fixtures

    except requests.RequestException as e:
        logging.error(f"❌ Network error fetching fixtures: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"❌ Unexpected error in get_fixture_data: {str(e)}")
        return []

# ===== FETCH MLB ODDS DATA =====
def get_odds_data():
    try:
        logging.info("🎲 Fetching MLB odds data...")
        response = requests.get(
            ODDS_API_URL,
            params={
                "regions": "us",  # Use US region for baseball
                "markets": "h2h,totals",  # Moneyline and Over/Under
                "oddsFormat": "american",  # American odds for baseball
                "apiKey": ODDS_API_KEY
            },
            timeout=15
        )
        
        # Handle API errors
        if response.status_code == 401:
            logging.error("❌ Odds API returned 401 Unauthorized - check your API key")
            return None
        if response.status_code != 200:
            logging.error(f"⚠️ Odds API error: {response.status_code} - {response.text[:200]}")
            return None
            
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"❌ Network error fetching odds: {str(e)}")
        return None
    except Exception as e:
        logging.error(f"❌ Unexpected error in get_odds_data: {str(e)}")
        return None

# ===== ANALYZE MLB BETTING MARKETS =====
def analyze_mlb_betting(odds_data, home_team, away_team):
    if not odds_data:
        return "⚠️ No odds data available", "⚠️ No odds data available"
    
    try:
        money_line_analysis = "⚠️ Moneyline data not found"
        over_under_analysis = "⚠️ Over/Under data not found"
        
        for match in odds_data:
            if match.get('home_team') == home_team and match.get('away_team') == away_team:
                # Money Line Analysis
                home_odds = []
                away_odds = []
                
                # Over/Under Analysis
                over_odds = []
                under_odds = []
                total_points = None
                
                for bookmaker in match.get('bookmakers', []):
                    for market in bookmaker.get('markets', []):
                        # Money Line (H2H)
                        if market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home_team:
                                    home_odds.append(outcome['price'])
                                elif outcome['name'] == away_team:
                                    away_odds.append(outcome['price'])
                        
                        # Over/Under
                        elif market['key'] == 'totals':
                            for outcome in market['outcomes']:
                                if outcome['name'] == 'Over':
                                    over_odds.append(outcome['price'])
                                    total_points = outcome['point']
                                elif outcome['name'] == 'Under':
                                    under_odds.append(outcome['price'])
                
                # Money Line Analysis