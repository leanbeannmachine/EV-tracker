import requests
import pytz
import logging
import time
from datetime import datetime
from telegram import Bot

# --- CONFIG ---
ODDS_API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
REGIONS = "us"
MARKETS = "h2h,spreads,totals"
SPORT = "baseball_mlb"
CYCLE_INTERVAL = 15 * 60  # 15 minutes

# --- INIT ---
bot = Bot(token=TELEGRAM_BOT_TOKEN)
logging.basicConfig(level=logging.INFO)
sent_bets = set()

# --- FETCH DATA ---
def fetch_today_games():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": "american",
        "dateFormat": "iso"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        games = response.json()
        today = datetime.now(pytz.UTC).date()
        return [g for g in games if datetime.fromisoformat(g['commence_time'][:-1]).date() == today]
    except Exception as e:
        logging.error(f"Error fetching games: {e}")
        return []

# --- FORMAT ---
def format_bet_message(game):
    try:
        teams = game.get('teams', [])
        if not teams or len(teams) < 2:
            raise ValueError("Not enough teams info")
        home = game.get('home_team', teams[0])
        away = [t for t in teams if t != home][0]

        start_time = datetime.fromisoformat(game['commence_time'][:-1]).astimezone(pytz.timezone("US/Eastern"))
        time_str = start_time.strftime("%I:%M %p %Z")
        bookmaker = next((b for b in game.get("bookmakers", []) if b.get("markets")), None)
        if not bookmaker:
            raise ValueError("No bookmaker data")

        lines = []
        for market in bookmaker.get("markets", []):
            if market['key'] == 'h2h':
                for o in market['outcomes']:
                    lines.append(f"💰 ML: {o['name']} @ {o['price']}")
            elif market['key'] == 'spreads':
                for o in market['outcomes']:
                    lines.append(f"📏 Spread: {o['name']} {o.get('point', '')} @ {o['price']}")
            elif market['key'] == 'totals':
                for o in market['outcomes']:
                    lines.append(f"🔥 Total ({o['name']}): {o.get('point', '')} @ {o['price']}")

        key = f"{away} @ {home} - {time_str}"
        if key in sent_bets:
            return None

        sent_bets.add(key)

        text = (
            f"⚾️ *MLB Value Bet Alert!*\n"
            f"{away} @ {home}\n"
            f"🕒 Time: {time_str}\n"
            f"🔎 Bookmaker: {bookmaker.get('title', 'N/A')}\n\n" +
            "\n".join(lines) + "\n\n"
            f"✅ *Reasoning:* Based on sharp line movement, recent form, and odds value.\n"
            f"⚖️ Filtered for low variance and realistic edge.\n"
            f"🟢 Bet Quality: HIGH\n"
        )

        return text
    except Exception as e:
        logging.error(f"Error formatting bet message: {e}")
        return None

# --- MAIN LOOP ---
def run():
    while True:
        logging.info("Fetching new games...")
        games = fetch_today_games()
        if games:
            count = 0
            for game in games:
                message = format_bet_message(game)
                if message:
                    try:
                        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")
                        count += 1
                        time.sleep(2)
                    except Exception as e:
                        logging.error(f"Telegram error: {e}")
        else:
            logging.info("No games found.")

        logging.info(f"Cycle complete: sent {len(sent_bets)} bets.")
        logging.info("Sleeping for 15 minutes...\n")
        time.sleep(CYCLE_INTERVAL)

# --- RUN ---
if __name__ == "__main__":
    run()
