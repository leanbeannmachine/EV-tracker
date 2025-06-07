import requests
import logging
from datetime import datetime, timedelta, timezone

# ===== SET UP LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ===== CONFIGURATION =====
SPORTRADAR_API_KEY = "sosfspGNzXZb5zVvL46yDkqNVzOwVa8rgi0t11uRY"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# ===== API ENDPOINTS =====
ODDS_URL = "http://api.sportradar.us/mlb/trial/v7/en/games/{game_id}/odds.json"

# ===== FETCH MLB SCHEDULE =====
def get_mlb_schedule():
    try:
        # Use UTC time with timezone awareness
        today_utc = datetime.now(timezone.utc).date()
        url = f"https://statsapi.mlb.com/api/v1/schedule?date={today_utc}&sportId=1"
        
        logging.info("📅 Fetching MLB schedule from official API...")
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()
        
        games = []
        
        for date in data.get('dates', []):
            for game in date.get('games', []):
                try:
                    # Parse game time as timezone-aware datetime
                    game_time_str = game['gameDate']
                    if game_time_str.endswith('Z'):
                        game_time_str = game_time_str[:-1] + '+00:00'
                    game_time = datetime.fromisoformat(game_time_str)
                    
                    # Extract Sportradar ID if available
                    sportradar_id = None
                    for link in game.get('links', []):
                        if link['relation'] == 'sportradar':
                            sportradar_id = link['href'].split('/')[-1]
                            break
                    
                    games.append({
                        'id': sportradar_id,
                        'mlb_id': str(game['gamePk']),
                        'home': game['teams']['home']['team']['name'],
                        'away': game['teams']['away']['team']['name'],
                        'time': game['gameDate'],  # Keep original string
                        'status': game['status']['detailedState']
                    })
                except (KeyError, ValueError) as e:
                    logging.warning(f"⚠️ Could not parse game data: {str(e)}")
                    continue
        
        logging.info(f"📊 Found {len(games)} MLB games for today")
        return games
        
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Network error fetching schedule: {str(e)}")
    except Exception as e:
        logging.error(f"❌ Unexpected error fetching schedule: {str(e)}")
    return []

# ===== FETCH GAME ODDS =====
def get_game_odds(game_id):
    if not game_id:
        logging.warning("⚠️ No Sportradar ID available for odds lookup")
        return None
        
    try:
        logging.info(f"🎲 Fetching odds for game {game_id}...")
        response = requests.get(
            ODDS_URL.format(game_id=game_id),
            params={"api_key": SPORTRADAR_API_KEY},
            timeout=10
        )
        
        if response.status_code != 200:
            logging.warning(f"⚠️ Odds not available for game {game_id}: {response.status_code}")
            return None
            
        return response.json()
    
    except Exception as e:
        logging.error(f"❌ Error fetching odds: {str(e)}")
        return None

# ===== ANALYZE ODDS =====
def analyze_odds(odds_data):
    if not odds_data or not odds_data.get('markets'):
        return "⚠️ No odds data available", "⚠️ No odds data available"
    
    try:
        money_line = "💰 "
        over_under = "📊 "
        
        # Find moneyline market
        for market in odds_data['markets']:
            if market['name'] == 'moneyline':
                for outcome in market.get('books', [{}])[0].get('outcomes', []):
                    money_line += f"{outcome['name']}: {outcome['odds']} "
            
            elif market['name'] == 'total' and 'points' in market:
                over_under += f"O/U {market['points']}: "
                for outcome in market.get('books', [{}])[0].get('outcomes', []):
                    over_under += f"{outcome['name']} {outcome['odds']} "
        
        return money_line, over_under
        
    except Exception as e:
        logging.error(f"❌ Error analyzing odds: {str(e)}")
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

# ===== FORMAT GAME TIME =====
def format_game_time(time_str):
    try:
        # Handle both 'Z' suffix and timezone offset
        if time_str.endswith('Z'):
            time_str = time_str[:-1] + '+00:00'
        dt = datetime.fromisoformat(time_str)
        return dt.strftime("%I:%M %p UTC")
    except Exception as e:
        logging.warning(f"⚠️ Could not parse time {time_str}: {str(e)}")
        return time_str

# ===== MAIN FUNCTION =====
def main():
    logging.info("🚀 Starting MLB betting analysis")
    
    # Get today's games
    games = get_mlb_schedule()
    
    if not games:
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        message = f"⚾ <b>MLB Betting Report - {today_str}</b>\n\nNo games scheduled for today."
        logging.info(message)
        send_telegram_message(message)
        return
    
    # Prepare report
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    report = f"⚾ <b>MLB Betting Report - {today_str}</b>\n\n"
    games_with_odds = 0
    
    # Process each game
    for game in games:
        # Get odds data if Sportradar ID is available
        odds_data = get_game_odds(game['id']) if game['id'] else None
        
        # Analyze odds
        money_line, over_under = analyze_odds(odds_data)
        if "No odds" not in money_line:
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
    
    # Send report
    logging.info(f"📝 Generated report with {len(games)} games ({games_with_odds} with odds)")
    send_telegram_message(report)
    logging.info("✅ Analysis complete")

# ===== ENTRY POINT =====
if __name__ == "__main__":
    main()
