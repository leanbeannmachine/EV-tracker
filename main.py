import requests
import logging
from datetime import datetime, timedelta

# ===== SET UP LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ===== CONFIGURATION =====
ODDS_API_KEY = "7b5d540e73c8790a95b84d3713e1a572"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# ===== API ENDPOINTS =====
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
SPORTS_API_URL = "https://api.the-odds-api.com/v4/sports"

# ===== TEST ODDS API KEY =====
def test_odds_api_key():
    """Test Odds API key before proceeding"""
    try:
        response = requests.get(
            SPORTS_API_URL,
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

# ===== FETCH UPCOMING GAMES =====
def get_upcoming_games():
    try:
        logging.info("🔍 Fetching upcoming MLB games...")
        now = datetime.utcnow()
        start_date = now
        end_date = now + timedelta(days=2)  # Look 2 days ahead
        
        response = requests.get(
            ODDS_API_URL,
            params={
                "apiKey": ODDS_API_KEY,
                "regions": "us",
                "markets": "h2h,totals",
                "oddsFormat": "american",
                "dateFormat": "iso"
            },
            timeout=15
        )
        
        if response.status_code == 401:
            logging.error("❌ Odds API returned 401 Unauthorized - check your API key")
            return []
        if response.status_code != 200:
            logging.error(f"⚠️ Odds API error: {response.status_code} - {response.text[:200]}")
            return []
            
        games = response.json()
        
        # Filter games within the next 2 days
        valid_games = []
        for game in games:
            try:
                commence_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                if start_date < commence_time < end_date:
                    game['commence_time'] = commence_time  # Replace string with datetime object
                    valid_games.append(game)
            except Exception as e:
                logging.warning(f"⚠️ Could not parse date for game: {game.get('id')} - {str(e)}")
        
        logging.info(f"📊 Found {len(valid_games)} upcoming MLB games")
        for game in valid_games:
            logging.info(f"  ⚾ {game['home_team']} vs {game['away_team']} at {game['commence_time']}")
            
        return valid_games
        
    except Exception as e:
        logging.error(f"❌ Error fetching games: {str(e)}")
        return []

# ===== ANALYZE GAME ODDS =====
def analyze_game_odds(game):
    try:
        money_line = "⚠️ Moneyline data not found"
        over_under = "⚠️ Over/Under data not found"
        
        if not game.get('bookmakers'):
            return money_line, over_under
            
        home_odds = []
        away_odds = []
        over_odds = []
        under_odds = []
        total_points = None
        
        for bookmaker in game['bookmakers']:
            for market in bookmaker['markets']:
                # Moneyline (H2H) market
                if market['key'] == 'h2h':
                    for outcome in market['outcomes']:
                        if outcome['name'] == game['home_team']:
                            home_odds.append(outcome['price'])
                        elif outcome['name'] == game['away_team']:
                            away_odds.append(outcome['price'])
                
                # Totals (Over/Under) market
                elif market['key'] == 'totals':
                    for outcome in market['outcomes']:
                        if outcome['name'] == 'Over':
                            over_odds.append(outcome['price'])
                            total_points = outcome['point']
                        elif outcome['name'] == 'Under':
                            under_odds.append(outcome['price'])
        
        # Calculate averages if we have data
        if home_odds and away_odds:
            avg_home = sum(home_odds) / len(home_odds)
            avg_away = sum(away_odds) / len(away_odds)
            money_line = f"💰 Home: {avg_home:.2f} | Away: {avg_away:.2f}"
        
        if over_odds and under_odds and total_points is not None:
            avg_over = sum(over_odds) / len(over_odds)
            avg_under = sum(under_odds) / len(under_odds)
            over_under = f"📊 O/U {total_points}: Over {avg_over:.2f} | Under {avg_under:.2f}"
        
        return money_line, over_under
        
    except Exception as e:
        logging.error(f"❌ Error analyzing odds for game: {str(e)}")
        return "⚠️ Analysis error", "⚠️ Analysis error"

# ===== SEND TELEGRAM MESSAGE =====
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logging.info("✅ Message sent to Telegram")
        else:
            logging.error(f"⚠️ Failed to send Telegram message: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"❌ Telegram send error: {str(e)}")

# ===== MAIN FUNCTION =====
def main():
    logging.info("🚀 Starting MLB betting analysis")
    
    if not test_odds_api_key():
        logging.error("❌ Odds API key validation failed. Exiting.")
        return
    
    games = get_upcoming_games()
    
    if not games:
        logging.info("ℹ️ No upcoming games found")
        send_telegram_message("⚾ <b>MLB Betting Report</b>\n\nNo upcoming games found in the next 2 days.")
        return
    
    # Prepare report
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    report = f"⚾ <b>MLB Betting Report - {today_str}</b>\n\n"
    
    for game in games:
        home_team = game['home_team']
        away_team = game['away_team']
        game_time = game['commence_time'].strftime("%Y-%m-%d %H:%M UTC")
        
        money_line, over_under = analyze_game_odds(game)
        
        report += (
            f"<b>{home_team} vs {away_team}</b>\n"
            f"⏰ {game_time}\n"
            f"{money_line}\n"
            f"{over_under}\n\n"
        )
    
    logging.info(f"📝 Generated report with {len(games)} games")
    send_telegram_message(report)
    logging.info("✅ Analysis complete")

# ===== ENTRY POINT =====
if __name__ == "__main__":
    main()
