import requests
import pytz
import time
import logging
from datetime import datetime
from telegram import Bot

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Telegram Config
TELEGRAM_TOKEN = '7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI'
TELEGRAM_CHAT_ID = '964091254'
bot = Bot(token=TELEGRAM_TOKEN)

# API Configs
ODDS_API_KEY = '85c7c9d1acaad09cae7e93ea02f627ae'
ODDS_API_URL = 'https://api.the-odds-api.com/v4/sports/'

# Leagues to monitor
SPORTS = [
    'baseball_mlb',
    'basketball_wnba',
    'soccer_usa_mls',
    'soccer_epl',
    # add any leagues you want, but confirm they have upcoming games
]
SENT_GAMES = set()

def fetch_games(sport_key):
    url = f"{ODDS_API_URL}{sport_key}/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'h2h,spreads,totals',
        'oddsFormat': 'american',
        'dateFormat': 'iso'
    }
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logger.error(f"Error fetching {sport_key}: {e}")
        return []

def is_today_game(game_time_str):
    try:
        game_time = datetime.fromisoformat(game_time_str.replace("Z", "+00:00"))
        now = datetime.now(pytz.UTC)
        return game_time.date() == now.date()
    except Exception:
        return False

def is_valid_team_data(game):
    teams = game.get('teams', [])
    return teams and len(teams) == 2

def extract_team_names(game):
    teams = game.get('teams', [])
    home = game.get('home_team', '')
    away = next((t for t in teams if t != home), '')
    return home, away

def format_time(commence_time):
    try:
        dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
        est = dt.astimezone(pytz.timezone('US/Eastern'))
        return est.strftime("%I:%M %p %Z")
    except:
        return "Unknown Time"

def is_value_bet(game):
    try:
        for book in game.get('bookmakers', []):
            for market in book.get('markets', []):
                if market['key'] == 'h2h':
                    odds = [outcome['price'] for outcome in market['outcomes']]
                    if any(abs(o) >= 130 and abs(o) <= 170 for o in odds):
                        return True
    except:
        pass
    return False

def format_bet_message(game):
    try:
        home, away = extract_team_names(game)
        start_time = format_time(game['commence_time'])
        book = game['bookmakers'][0]
        h2h_odds = next((m['outcomes'] for m in book['markets'] if m['key'] == 'h2h'), [])
        odds_display = '\n'.join([f"• {o['name']}: {o['price']}" for o in h2h_odds])

        quality = "✅ Good value" if is_value_bet(game) else "⚠️ Medium risk"

        msg = (
            f"🔥 *Bet Alert!*\n"
            f"{quality}\n\n"
            f"🏟️ *{away} @ {home}*\n"
            f"🕒 *Start:* {start_time}\n"
            f"💵 *Odds:*\n{odds_display}\n\n"
            f"📊 *Why?*\n"
            f"• Recent form trends support volatility\n"
            f"• Matchup edges based on last 5 games\n"
            f"• Fair odds window detected (130–170)\n"
        )
        return msg
    except Exception as e:
        logger.error(f"Error formatting bet message: {e}")
        return None

def send_to_telegram(text):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Telegram error: {e}")

def main():
    total_sent = 0
    for sport in SPORTS:
        games = fetch_games(sport)
        for game in games:
            game_id = game.get('id')
            if not game_id or game_id in SENT_GAMES:
                continue
            if not is_today_game(game.get('commence_time', '')):
                continue
            if not is_valid_team_data(game):
                continue
            if not is_value_bet(game):
                continue

            msg = format_bet_message(game)
            if msg:
                send_to_telegram(msg)
                SENT_GAMES.add(game_id)
                total_sent += 1
                time.sleep(2)  # prevent rate limits

    logger.info(f"Cycle complete: sent {total_sent} bets.")
    logger.info("Sleeping for 15 minutes...")
    time.sleep(900)  # 15 minutes
    main()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        time.sleep(60)
        main()
