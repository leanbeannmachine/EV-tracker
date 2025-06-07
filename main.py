import requests
import logging
from datetime import datetime, timedelta, timezone

# ===== SET UP LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

# ===== CONFIGURATION =====
SPORTRADAR_API_KEY = "sosfspGNzXZb5zVvL46yDkqNVzOwVa8rgi0t11uRY"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# ===== API ENDPOINTS =====
ODDS_URL = "https://api.sportradar.us/mlb/trial/v7/en/games/{game_id}/odds.json"

# ===== FETCH MLB SCHEDULE =====
def get_mlb_schedule():
    try:
        today_utc = datetime.now(timezone.utc).date()
        url = f"https://statsapi.mlb.com/api/v1/schedule?date={today_utc}&sportId=1"
        
        logger.info("📅 Fetching MLB schedule from official API...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        games = []
        
        for date in data.get('dates', []):
            for game in date.get('games', []):
                try:
                    # Parse game time correctly
                    game_time_str = game['gameDate']
                    if game_time_str.endswith('Z'):
                        game_time_str = game_time_str[:-1] + '+00:00'
                    
                    # Extract Sportradar ID with fallback to MLB ID
                    sportradar_id = None
                    for link in game.get('links', []):
                        if link['relation'] == 'sportradar':
                            sportradar_id = link['href'].split('/')[-1]
                            break
                    
                    # If Sportradar ID not found, use MLB ID as fallback
                    if not sportradar_id:
                        sportradar_id = f"mlb-{game['gamePk']}"
                        logger.warning(f"⚠️ Using fallback ID for game: {sportradar_id}")
                    
                    games.append({
                        'id': sportradar_id,
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

# ===== FETCH GAME ODDS =====
def get_game_odds(game_id):
    try:
        logger.info(f"🎲 Fetching odds for {game_id}...")
        response = requests.get(
            ODDS_URL.format(game_id=game_id),
            params={"api_key": SPORTRADAR_API_KEY},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            logger.warning(f"🔍 No odds found for {game_id}")
        else:
            logger.warning(f"⚠️ Odds API error {response.status_code} for {game_id}")
    
    except requests.exceptions.Timeout:
        logger.error(f"⌛ Timeout fetching odds for {game_id}")
    except Exception as e:
        logger.error(f"❌ Odds fetch error: {str(e)}")
    return None

# ===== ANALYZE ODDS =====
def analyze_odds(odds_data):
    if not odds_data:
        return "⚠️ No odds data available", "⚠️ No odds data available"
    
    try:
        money_line = "💰 "
        over_under = "📊 "
        
        # Extract moneyline odds
        for market in odds_data.get('markets', []):
            if market.get('name') == 'moneyline':
                book = market.get('books', [{}])[0]
                for outcome in book.get('outcomes', []):
                    money_line += f"{outcome.get('name', 'N/A')}: {outcome.get('odds', 'N/A')} "
                break
        
        # Extract over/under
        for market in odds_data.get('markets', []):
            if market.get('name') == 'total' and 'points' in market:
                book = market.get('books', [{}])[0]
                over_under += f"O/U {market['points']}: "
                for outcome in book.get('outcomes', []):
                    over_under += f"{outcome.get('name', 'N/A')} {outcome.get('odds', 'N/A')} "
                break
        
        return money_line, over_under
        
    except Exception as e:
        logger.error(f"❌ Odds analysis error: {str(e)}")
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
    
    games = get_mlb_schedule()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    if not games:
        message = f"⚾ <b>MLB Betting Report - {today_str}</b>\n\nNo games scheduled today."
        send_telegram_message(message)
        return
    
    report = f"⚾ <b>MLB Betting Report - {today_str}</b>\n\n"
    games_with_odds = 0
    
    for game in games:
        odds_data = get_game_odds(game['id'])
        money_line, over_under = analyze_odds(odds_data)
        
        if "No odds" not in money_line:
            games_with_odds += 1
        
        game_time = format_game_time(game['time'])
        
        report += (
            f"<b>{game['away']} @ {game['home']}</b>\n"
            f"⏰ {game_time} | Status: {game['status']}\n"
            f"{money_line}\n"
            f"{over_under}\n\n"
        )
    
    logger.info(f"📝 Generated report: {len(games)} games ({games_with_odds} with odds)")
    send_telegram_message(report)
    logger.info("✅ Report completed successfully")

# ===== ENTRY POINT =====
if __name__ == "__main__":
    main()
