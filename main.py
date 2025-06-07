import requests
import logging
from datetime import datetime, timezone

# ===== SET UP LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

# ===== CONFIGURATION =====
THE_ODDS_API_KEY = "7b5d540e73c8790a95b84d3713e1a572"  # Replace with your actual key
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
SPORT = "baseball_mlb"  # The Odds API sport key for MLB

# ===== API ENDPOINTS =====
ODDS_URL = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"

# ===== FETCH MLB SCHEDULE =====
def get_mlb_schedule():
    try:
        today_utc = datetime.now(timezone.utc).date()
        params = {"date": today_utc, "sportId": 1}
        
        logger.info("📅 Fetching MLB schedule...")
        response = requests.get(SCHEDULE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        games = []
        
        for date in data.get('dates', []):
            for game in date.get('games', []):
                try:
                    # Parse game time
                    game_time_str = game['gameDate']
                    if game_time_str.endswith('Z'):
                        game_time_str = game_time_str[:-1] + '+00:00'
                    
                    games.append({
                        'mlb_id': str(game['gamePk']),
                        'home': game['teams']['home']['team']['name'],
                        'away': game['teams']['away']['team']['name'],
                        'time': game_time_str,
                        'status': game['status']['detailedState']
                    })
                except (KeyError, ValueError) as e:
                    logger.warning(f"⚠️ Game parsing error: {str(e)}")
                    continue
        
        logger.info(f"📊 Found {len(games)} MLB games for today")
        return games
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Network error fetching schedule: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Unexpected schedule error: {str(e)}")
    return []

# ===== FETCH ODDS DATA =====
def get_odds_data():
    try:
        logger.info("🎲 Fetching odds from The Odds API...")
        params = {
            "apiKey": THE_ODDS_API_KEY,
            "regions": "us",  # US odds
            "markets": "h2h,totals",  # Moneyline and Over/Under
            "oddsFormat": "american",
            "dateFormat": "iso"
        }
        response = requests.get(ODDS_URL, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Odds API error: {str(e)}")
    return []

# ===== MATCH GAMES WITH ODDS =====
def match_game_with_odds(game, odds_data):
    try:
        # Find matching game in odds data
        for odds_game in odds_data:
            home_team = odds_game['home_team']
            away_team = odds_game['away_team']
            
            # Check if teams match (case-insensitive)
            if (game['home'].lower() in home_team.lower() and 
                game['away'].lower() in away_team.lower()):
                return odds_game
    except Exception as e:
        logger.error(f"❌ Error matching odds: {str(e)}")
    return None

# ===== FORMAT ODDS =====
def format_odds(odds_game):
    if not odds_game:
        return "⚠️ No odds data available", "⚠️ No odds data available"
    
    try:
        money_line = "💰 "
        over_under = "📊 "
        
        # Find bookmaker (prioritize DraftKings or FanDuel)
        bookmaker = None
        for book in odds_game['bookmakers']:
            if book['key'] in ['draftkings', 'fanduel']:
                bookmaker = book
                break
        if not bookmaker and odds_game['bookmakers']:
            bookmaker = odds_game['bookmakers'][0]  # Fallback to first bookmaker
        
        if not bookmaker:
            return "⚠️ No odds available", "⚠️ No odds available"
        
        # Extract moneyline odds
        for market in bookmaker['markets']:
            if market['key'] == 'h2h':
                for outcome in market['outcomes']:
                    money_line += f"{outcome['name']}: {outcome['price']} "
        
        # Extract over/under
        for market in bookmaker['markets']:
            if market['key'] == 'totals':
                over_under += f"O/U {market['outcomes'][0]['point']}: "
                for outcome in market['outcomes']:
                    over_under += f"{outcome['name']} {outcome['price']} "
                break
        
        return money_line, over_under
        
    except Exception as e:
        logger.error(f"❌ Odds formatting error: {str(e)}")
        return "⚠️ Odds format error", "⚠️ Odds format error"

# ===== SEND TELEGRAM MESSAGE =====
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            logger.info("✅ Telegram message sent")
        else:
            logger.error(f"⚠️ Telegram error {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"❌ Telegram send error: {str(e)}")

# ===== FORMAT GAME TIME =====
def format_game_time(time_str):
    try:
        # Remove milliseconds if present
        if '.' in time_str:
            time_str = time_str.split('.')[0]
        # Ensure UTC timezone format
        if time_str.endswith('Z'):
            time_str = time_str[:-1] + '+00:00'
        elif '+' not in time_str:
            time_str += '+00:00'
            
        dt = datetime.fromisoformat(time_str)
        return dt.strftime("%I:%M %p UTC")
    except Exception as e:
        logger.warning(f"⚠️ Time format error: {str(e)}")
        return time_str

# ===== MAIN FUNCTION =====
def main():
    logger.info("🚀 Starting MLB betting report generator")
    
    # Get today's games
    games = get_mlb_schedule()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    if not games:
        message = f"⚾ <b>MLB Betting Report - {today_str}</b>\n\nNo games scheduled today."
        send_telegram_message(message)
        return
    
    # Get odds data
    odds_data = get_odds_data()
    logger.info(f"📊 Retrieved odds for {len(odds_data)} games")
    
    # Prepare report
    report = f"⚾ <b>MLB Betting Report - {today_str}</b>\n\n"
    games_with_odds = 0
    
    # Process each game
    for game in games:
        # Match game with odds
        odds_game = match_game_with_odds(game, odds_data)
        money_line, over_under = format_odds(odds_game)
        
        if "⚠️" not in money_line:
            games_with_odds += 1
        
        # Format game time
        game_time = format_game_time(game['time'])
        
        # Add to report
        report += (
            f"<b>{game['away']} @ {game['home']}</b>\n"
            f"⏰ {game_time} | Status: {game['status']}\n"
            f"{money_line}\n"
            f"{over_under}\n\n"
        )
    
    # Add summary footer
    report += f"<i>Successfully retrieved odds for {games_with_odds} of {len(games)} games</i>"
    
    # Send report
    logger.info(f"📝 Generated report: {len(games)} games ({games_with_odds} with odds)")
    send_telegram_message(report)
    logger.info("✅ Report completed successfully")

# ===== ENTRY POINT =====
if __name__ == "__main__":
    main()
