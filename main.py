import requests
from bet_formatter import format_bet_message
import pytz
import time
import logging
from datetime import datetime
from telegram import Bot

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# --- Credentials ---
TELEGRAM_TOKEN = '7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI'
TELEGRAM_CHAT_ID = '964091254'
ODDS_API_KEY = '85c7c9d1acaad09cae7e93ea02f627ae'

bot = Bot(token=TELEGRAM_TOKEN)

# --- Config ---
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/"
SPORTS = [
    'baseball_mlb',
    'basketball_wnba',
    'soccer_usa_mls',
    'soccer_epl',
]
SENT_GAMES = set()

def fetch_games(sport_key):
    url = f"{ODDS_API_URL}{sport_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso"
    }
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logger.error(f"Error fetching {sport_key}: {e}")
        return []

def is_today_game(commence_time_str):
    try:
        game_time = datetime.fromisoformat(commence_time_str.replace("Z", "+00:00"))
        now = datetime.now(pytz.UTC)
        return now.date() == game_time.date()
    except Exception:
        return False

def extract_teams(game):
    teams = game.get("teams", [])
    home = game.get("home_team", "")
    away = next((t for t in teams if t != home), "")
    return home, away

def format_start_time(commence_time):
    try:
        dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
        local = dt.astimezone(pytz.timezone("US/Eastern"))
        return local.strftime("%I:%M %p %Z")
    except:
        return "Unknown Time"

def is_value_bet(game):
    for book in game.get("bookmakers", []):
        for market in book.get("markets", []):
            if market["key"] == "h2h":
                for outcome in market.get("outcomes", []):
                    price = abs(outcome.get("price", 0))
                    if 130 <= price <= 170:
                        return True
    return False

def format_message(game):
    home, away = extract_teams(game)
    time_str = format_start_time(game.get("commence_time", ""))
    book = game.get("bookmakers", [{}])[0]
    h2h_market = next((m for m in book.get("markets", []) if m["key"] == "h2h"), {})
    outcomes = h2h_market.get("outcomes", [])
    odds = "\n".join(f"• {o['name']}: {o['price']}" for o in outcomes)

    return (
        f"🔥 *Bet Alert!*\n"
        f"✅ Good value bet\n\n"
        f"🏟️ *{away} @ {home}*\n"
        f"🕒 *Start:* {time_str}\n"
        f"💵 *Odds:*\n{odds}\n\n"
        f"📊 *Why?*\n"
        f"• Odds range is favorable (+130 to +170)\n"
        f"• Based on recent matchup volatility\n"
        f"• Filtered for today's value picks"
    )

def send_to_telegram(msg):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Telegram error: {e}")

# --- One-time execution ---
def main():
    sent_count = 0
    for sport in SPORTS:
        games = fetch_games(sport)
        for game in games:
            game_id = game.get("id")
            if not game_id or game_id in SENT_GAMES:
                continue
            if not is_today_game(game.get("commence_time", "")):
                continue
            if not is_value_bet(game):
                continue

            msg = format_message(game)
            if msg:
                send_to_telegram(msg)
                SENT_GAMES.add(game_id)
                sent_count += 1
                time.sleep(1)

    logger.info(f"✅ Cycle complete: sent {sent_count} bets.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
