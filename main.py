import requests
import html
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
# Load and verify environment variables
def get_env_var(name, required=True):
    value = os.getenv(name)
    if not value and required:
        logging.error(f"❌ Missing required environment variable: {name}")
        raise ValueError(f"Missing environment variable: {name}")
    return value

try:
    ODDS_API_KEY = "7b5d540e73c8790a95b84d3713e1a572"
    SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
    TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
    TELEGRAM_CHAT_ID =  "964091254"
except ValueError:
    logging.error("❌ Critical error - missing required environment variables. Exiting.")
    exit(1)

# ===== API ENDPOINTS =====
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/upcoming/odds"
SPORTMONKS_API_URL = "https://api.sportmonks.com/v3/football/fixtures"

# ===== LEAGUE FILTERS =====
PREFERRED_LEAGUES = [
    "Premier League", 
    "La Liga",
    "Serie A",
    "Bundesliga",
    "Ligue 1",
    "Champions League",
    "Europa League"
]

# ===== COUNTRY FILTERS =====
PREFERRED_COUNTRIES = [
    "England",
    "Spain",
    "Italy",
    "Germany",
    "France"
]

# ===== TEST API KEYS =====
def test_api_keys():
    """Test API keys before proceeding"""
    # Test SportMonks API key
    test_url = "https://api.sportmonks.com/v3/football/leagues"
    try:
        response = requests.get(
            test_url,
            params={"api_token": SPORTMONKS_API_KEY, "per_page": 1},
            timeout=10
        )
        if response.status_code == 401:
            logging.error("❌ SportMonks API key is invalid (401 Unauthorized)")
            return False
        response.raise_for_status()
    except Exception as e:
        logging.error(f"❌ SportMonks API test failed: {str(e)}")
        return False
    
    # Test Odds API key
    test_url = "https://api.the-odds-api.com/v4/sports"
    try:
        response = requests.get(
            test_url,
            params={"apiKey": ODDS_API_KEY},
            timeout=10
        )
        if response.status_code == 401:
            logging.error("❌ Odds API key is invalid (401 Unauthorized)")
            return False
        response.raise_for_status()
    except Exception as e:
        logging.error(f"❌ Odds API test failed: {str(e)}")
        return False
    
    return True

# ===== FETCH FIXTURE DATA =====
def get_fixture_data():
    try:
        logging.info("🔍 Fetching fixture data...")
        
        # Get UTC dates for filtering
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        day_after_tomorrow = today + timedelta(days=2)
        
        # Fetch fixtures directly with date filters
        response = requests.get(
            SPORTMONKS_API_URL,
            params={
                "api_token": SPORTMONKS_API_KEY,
                "include": "participants,league",
                "per_page": 50,
                "filters": "upcoming",
                "start_date": today.strftime("%Y-%m-%d"),
                "end_date": day_after_tomorrow.strftime("%Y-%m-%d")
            },
            timeout=15
        )
        
        # Handle API errors
        if response.status_code == 401:
            logging.error("❌ SportMonks API returned 401 Unauthorized")
            return []
        if response.status_code != 200:
            logging.error(f"⚠️ SportMonks API error: {response.status_code} - {response.text[:200]}")
            return []
        
        response.raise_for_status()
        data = response.json()
        fixtures = data.get('data', [])
        
        filtered = []
        logging.info(f"📊 Found {len(fixtures)} total fixtures from API")
        
        for fixture in fixtures:
            # Check if fixture is from preferred league and country
            league = fixture.get('league', {})
            league_name = league.get('name', '')
            country = league.get('country', {}).get('name', '')
            
            if PREFERRED_LEAGUES and league_name not in PREFERRED_LEAGUES:
                continue
            if PREFERRED_COUNTRIES and country not in PREFERRED_COUNTRIES:
                continue
                
            start_info = fixture.get('starting_at')
            if not start_info:
                continue
                
            try:
                # Handle both space and T separated formats
                if " " in start_info:  # Handle "YYYY-MM-DD HH:MM:SS"
                    date_str = start_info.split(" ")[0]
                else:  # Handle "YYYY-MM-DDTHH:MM:SS+00:00"
                    date_str = start_info.split("T")[0]
                
                fixture_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                # Add extra debug info
                debug_info = {
                    "id": fixture.get('id'),
                    "league": league_name,
                    "country": country,
                    "home": fixture['participants'][0]['name'] if fixture.get('participants') else "Unknown",
                    "away": fixture['participants'][1]['name'] if fixture.get('participants') and len(fixture['participants']) > 1 else "Unknown",
                    "date": str(fixture_date),
                }
                logging.info(f"✅ Included fixture: {debug_info}")
                filtered.append(fixture)
            except Exception as e:
                logging.error(f"⚠️ Failed to parse fixture date: {start_info} → {str(e)}")
                continue
                
        logging.info(f"🎯 Found {len(filtered)} filtered fixtures")
        return filtered

    except requests.RequestException as e:
        logging.error(f"❌ Network error fetching fixtures: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"❌ Unexpected error in get_fixture_data: {str(e)}")
        return []

# ===== FETCH ODDS DATA =====
def get_odds_data():
    try:
        logging.info("🎲 Fetching odds data...")
        response = requests.get(
            ODDS_API_URL,
            params={
                "regions": "eu",
                "markets": "h2h",
                "oddsFormat": "decimal",
                "apiKey": ODDS_API_KEY
            },
            timeout=15
        )
        
        # Handle API errors
        if response.status_code == 401:
            logging.error("❌ Odds API returned 401 Unauthorized")
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

# ===== ANALYZE BETTING MARKETS =====
def analyze_betting_markets(odds_data, home_team, away_team):
    if not odds_data:
        return "⚠️ No odds data available"
    
    try:
        for match in odds_data:
            if match.get('home_team') == home_team and match.get('away_team') == away_team:
                # Find best home and away odds
                home_odds = []
                away_odds = []
                
                for bookmaker in match.get('bookmakers', []):
                    for market in bookmaker.get('markets', []):
                        if market['key'] == 'h2h':
                            for outcome in market['outcomes']:
                                if outcome['name'] == home_team:
                                    home_odds.append(outcome['price'])
                                elif outcome['name'] == away_team:
                                    away_odds.append(outcome['price'])
                
                if not home_odds or not away_odds:
                    return "⚠️ Incomplete odds data"
                
                best_home = max(home_odds)
                best_away = max(away_odds)
                
                # Simple analysis - which team has better odds
                if best_home < best_away:
                    return f"🏠 {home_team} WIN (Best: {best_home:.2f})"
                else:
                    return f"✈️ {away_team} WIN (Best: {best_away:.2f})"
        
        return "⚠️ No matching odds found"
        
    except Exception as e:
        logging.error(f"❌ Error analyzing betting markets: {str(e)}")
        return "⚠️ Analysis error"

# ===== FORMAT TELEGRAM MESSAGE =====
def format_telegram_message(odds_data, fixture_data):
    if not fixture_data:
        return "⚠️ No upcoming fixtures found"
    
    try:
        fixture = fixture_data[0]
        participants = fixture.get('participants', [])
        
        if len(participants) < 2:
            return "⚠️ Fixture data incomplete"
        
        home = participants[0].get('name', 'Home Team')
        away = participants[1].get('name', 'Away Team')
        start_time = fixture.get('starting_at', '')
        league_name = fixture.get('league', {}).get('name', 'Unknown League')
        
        # Format date and time
        if "T" in start_time:
            date_str = start_time.split("T")[0]
            time_part = start_time.split("T")[1]
            time_str = time_part[:5] if len(time_part) >= 5 else "N/A"
        elif " " in start_time:
            parts = start_time.split(" ")
            date_str = parts[0] if len(parts) > 0 else "N/A"
            time_str = parts[1][:5] if len(parts) > 1 and len(parts[1]) >= 5 else "N/A"
        else:
            date_str = start_time[:10] if len(start_time) >= 10 else "N/A"
            time_str = "N/A"
        
        # Analyze betting market
        money_line = analyze_betting_markets(odds_data, home, away)
        
        # Build message
        message = f"""
🎯 *BETTING RECOMMENDATION* 🎯
⚽️ *{html.escape(home)} vs {html.escape(away)}*
🏆 *League:* {html.escape(league_name)}
📅 *Date:* {date_str} | ⏰ *Time:* {time_str} UTC
─────────────────
        
🟩 *MONEY LINE WINNER:*
   {money_line}
─────────────────
💡 *TIP:* Based on best available odds
"""
        return message
        
    except Exception as e:
        logging.error(f"❌ Error formatting message: {str(e)}")
        return "⚠️ Error formatting message"

# ===== SEND TO TELEGRAM =====
def send_telegram_message(message):
    try:
        logging.info("📤 Sending Telegram message...")
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=10)
        response_data = response.json()
        
        if response_data.get('ok'):
            logging.info("✅ Telegram message sent successfully!")
            return True
        else:
            logging.error(f"❌ Telegram API error: {response_data.get('description')}")
            return False
    except Exception as e:
        logging.error(f"❌ Failed to send Telegram message: {str(e)}")
        return False

# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    logging.info("🚀 Starting Betting Alert Script...")
    
    # Test API keys first
    if not test_api_keys():
        error_msg = "❌ API key verification failed. Exiting."
        logging.error(error_msg)
        send_telegram_message(error_msg)
        exit(1)
    
    # Get data from APIs
    fixture_data = get_fixture_data()
    odds_data = get_odds_data()
    
    if not fixture_data:
        warning_msg = "⚠️ No upcoming fixtures found"
        logging.warning(warning_msg)
        send_telegram_message(warning_msg)
        logging.info("🏁 Script completed")
        exit(0)
    
    # Format message
    message = format_telegram_message(odds_data, fixture_data)
    logging.info(f"💬 Formatted message:\n{message}")
    
    # Send to Telegram
    if not send_telegram_message(message):
        logging.error("❌ Failed to send Telegram message")
    
    logging.info("🏁 Script completed successfully")
