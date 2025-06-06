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

# ===== TEST API KEYS =====
def test_api_keys():
    """Test API keys before proceeding"""
    # Test SportMonks API key using a simple endpoint
    try:
        test_url = "https://api.sportmonks.com/v3/core/version"
        response = requests.get(
            test_url,
            params={"api_token": SPORTMONKS_API_KEY},
            timeout=10
        )
        if response.status_code == 401:
            logging.error("❌ SportMonks API key is invalid (401 Unauthorized)")
            return False
        response.raise_for_status()
        logging.info("✅ SportMonks API key validated")
        return True
    except Exception as e:
        logging.error(f"❌ SportMonks API test failed: {str(e)}")
        return False

    # Test Odds API key
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
        logging.info("🔍 Fetching MLB fixture data...")
        
        # Calculate date range
        today = datetime.utcnow().date()
        end_date = today + timedelta(days=3)  # Next 3 days
        
        # Fetch MLB fixtures
        response = requests.get(
            SPORTMONKS_API_URL,
            params={
                "api_token": SPORTMONKS_API_KEY,
                "include": "participants,venue",
                "per_page": 50,
                "leagues": str(MLB_LEAGUE_ID),
                "filters": "upcoming",
                "start_date": today.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
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
        
        # Log some debug information
        if fixtures:
            logging.info(f"📊 Found {len(fixtures)} MLB fixtures")
            for fixture in fixtures:
                start_time = fixture.get('starting_at', 'N/A')
                participants = fixture.get('participants', [])
                home = participants[0]['name'] if participants else 'Unknown'
                away = participants[1]['name'] if len(participants) > 1 else 'Unknown'
                logging.info(f"  ⚾ {home} vs {away} on {start_time}")
        else:
            logging.info("ℹ️ No MLB fixtures found in API response")
            
        return fixtures

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
                if home_odds and away_odds:
                    best_home = max(home_odds)
                    best_away = max(away_odds)
                    
                    if best_home < best_away:
                        money_line_analysis = f"🏠 {home_team} WIN (Best: {best_home:+d})"
                    else:
                        money_line_analysis = f"✈️ {away_team} WIN (Best: {best_away:+d})"
                
                # Over/Under Analysis
                if over_odds and under_odds and total_points:
                    best_over = max(over_odds)
                    best_under = max(under_odds)
                    
                    # Simple analysis - which has better value
                    if best_over < best_under:
                        over_under_analysis = f"⬆️ OVER {total_points} (Best: {best_over:+d})"
                    else:
                        over_under_analysis = f"⬇️ UNDER {total_points} (Best: {best_under:+d})"
                
                break  # Found our match, exit loop
        
        return money_line_analysis, over_under_analysis
        
    except Exception as e:
        logging.error(f"❌ Error analyzing betting markets: {str(e)}")
        return "⚠️ Analysis error", "⚠️ Analysis error"

# ===== FORMAT TELEGRAM MESSAGE =====
def format_telegram_message(odds_data, fixture_data):
    if not fixture_data:
        return "⚠️ No upcoming MLB games found in the next 3 days"
    
    try:
        # Sort fixtures by date
        fixture_data.sort(key=lambda x: x.get('starting_at', ''))
        fixture = fixture_data[0]
        
        participants = fixture.get('participants', [])
        if len(participants) < 2:
            return "⚠️ Fixture data incomplete"
        
        home = participants[0].get('name', 'Home Team')
        away = participants[1].get('name', 'Away Team')
        start_time = fixture.get('starting_at', '')
        venue = fixture.get('venue', {}).get('name', 'Unknown Stadium')
        
        # Format date and time (convert to Eastern Time)
        if "T" in start_time:
            date_str = start_time.split("T")[0]
            time_part = start_time.split("T")[1]
            utc_time = datetime.strptime(f"{date_str} {time_part[:5]}", "%Y-%m-%d %H:%M")
            et_time = utc_time - timedelta(hours=4)  # UTC to ET conversion
            time_str = et_time.strftime("%I:%M %p ET")
        else:
            date_str = start_time[:10] if len(start_time) >= 10 else "N/A"
            time_str = "N/A"
        
        # Analyze betting markets
        money_line, over_under = analyze_mlb_betting(odds_data, home, away)
        
        # Build message with simple formatting (no Markdown)
        message = f"""
⚾ MLB BETTING RECOMMENDATION ⚾
🏟️ Matchup: {home} vs {away}
📍 Venue: {venue}
📅 Date: {date_str} | ⏰ Time: {time_str}
─────────────────
        
💰 MONEY LINE:
   {money_line}
        
📊 OVER/UNDER:
   {over_under}
─────────────────
💡 TIP: Based on best available odds across bookmakers
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
    logging.info("🚀 Starting MLB Betting Alert Script...")
    
    # Test API keys first
    if not test_api_keys():
        error_msg = "❌ API key verification failed. Exiting."
        logging.error(error_msg)
        send_telegram_message(error_msg)  # Using simple text
        exit(1)
    
    # Get data from APIs
    logging.info("🔍 Fetching MLB fixture data...")
    fixture_data = get_fixture_data()
    
    if not fixture_data:
        warning_msg = "⚠️ No upcoming MLB games found in the next 3 days"
        logging.warning(warning_msg)
        send_telegram_message(warning_msg)
        logging.info("🏁 Script completed")
        exit(0)
    
    logging.info("🎲 Fetching MLB odds data...")
    odds_data = get_odds_data()
    
    # Format message
    message = format_telegram_message(odds_data, fixture_data)
    logging.info(f"💬 Formatted message:\n{message}")
    
    # Send to Telegram
    if not send_telegram_message(message):
        logging.error("❌ Failed to send Telegram message")
    
    logging.info("🏁 Script completed successfully")
