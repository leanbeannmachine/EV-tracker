import requests
import json
import time
from datetime import datetime
import pytz
import random
import os
import logging
import sys

# Setup logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

# 🔑 API Keys and Bot Config
ODDSAPI_KEY = '85c7c9d1acaad09cae7e93ea02f627ae'
TELEGRAM_BOT_TOKEN = '7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI'
TELEGRAM_CHAT_ID = '964091254'

# Constants
MAX_BETS_PER_CYCLE = 10
MIN_BETS_PER_CYCLE = 5
PAUSE_MINUTES = 15
SENT_BETS_FILE = 'sent_bets.json'

# Load sent bets to avoid duplicates
def load_sent_bets():
    if os.path.exists(SENT_BETS_FILE):
        with open(SENT_BETS_FILE, 'r') as f:
            return set(json.load(f))
    return set()

# Save sent bets after each cycle
def save_sent_bets(sent_bets):
    with open(SENT_BETS_FILE, 'w') as f:
        json.dump(list(sent_bets), f)

# Fetch today's MLB games from OddsAPI
def fetch_today_games():
    url = f'https://api.the-odds-api.com/v4/sports/baseball_mlb/odds'
    params = {
        'apiKey': ODDSAPI_KEY,
        'regions': 'us',
        'markets': 'h2h,spreads,totals',
        'oddsFormat': 'american',
        'dateFormat': 'iso',
        'daysFrom': 0,  # only today
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        games = response.json()
        logging.info(f"Fetched {len(games)} games from OddsAPI")
        return games
    except Exception as e:
        logging.error(f"Error fetching games: {e}")
        return []

# Convert UTC ISO time to local time string like "6:46 PM"
def format_game_time(utc_time_str):
    try:
        utc_dt = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        local_tz = pytz.timezone('US/Eastern')  # Change as needed
        local_dt = utc_dt.astimezone(local_tz)
        return local_dt.strftime('%-I:%M %p')
    except Exception as e:
        logging.error(f"Error formatting time: {e}")
        return utc_time_str

# Analyze last 5 games trends - Placeholder (simulate)
def get_team_trends(team_name):
    # This should call your own data source or API to fetch real trends
    # For demo: randomly assign hot/cold or neutral
    heat = random.choices(['🔥', '❄️', '⚪️'], weights=[0.4, 0.3, 0.3])[0]
    # Example: 4-1 or 1-4 record last 5 games
    record = f"{random.randint(1,4)}-{random.randint(0,5)}"
    return f"{heat} {record} ATS last 5"

# Determine bet quality emoji and reasoning based on odds value and simple heuristics
def rate_odds(odd_value):
    try:
        odd_int = int(odd_value)
        if odd_int >= 150 or odd_int <= -150:
            return '✅'
        elif 110 <= abs(odd_int) < 150:
            return '⚠️'
        else:
            return '❌'
    except:
        return '⚪️'

# Format the full bet message string
def format_bet_message(game):
    try:
        home = game['home_team']
        away = game['away_team']
        commence_time = format_game_time(game['commence_time'])
        bookmaker = game['bookmakers'][0] if game.get('bookmakers') else {'title': 'Unknown'}

        moneyline = {}
        spread = {}
        total = {}

        # Extract odds
        for market in bookmaker.get('markets', []):
            if market['key'] == 'h2h':
                for outcome in market['outcomes']:
                    moneyline[outcome['name']] = outcome['price']
            elif market['key'] == 'spreads':
                for outcome in market['outcomes']:
                    spread[outcome['name']] = f"{outcome['point']} @ {outcome['price']}"
            elif market['key'] == 'totals':
                for outcome in market['outcomes']:
                    total[outcome['name']] = f"{outcome['point']} @ {outcome['price']}"

        # Compose message lines
        lines = []
        lines.append(f"📊 MLB Bet Preview")
        lines.append(f"🕒 {commence_time} Local Time")
        lines.append(f"⚔️ {away} @ {home}")
        lines.append(f"🏦 {bookmaker['title']}")

        # Moneyline section
        lines.append("")
        lines.append(f"💰 Moneyline:")
        for team in [away, home]:
            emoji = rate_odds(moneyline.get(team, '0'))
            lines.append(f"- {team}: {moneyline.get(team, 'N/A')} {emoji}")

        # Spread section
        lines.append("")
        lines.append(f"🟩 Spread:")
        for team in [away, home]:
            val = spread.get(team, 'N/A')
            odds = val.split('@')[-1].strip() if val != 'N/A' else 'N/A'
            emoji = rate_odds(odds)
            lines.append(f"- {team} {val} {emoji}")

        # Total section
        lines.append("")
        lines.append(f"📈 Total:")
        over_key = f"Over {list(total.keys())[0].split(' ')[1]}" if total else "Over"
        under_key = f"Under {list(total.keys())[0].split(' ')[1]}" if total else "Under"
        # Use keys from total dict for over and under
        for key in total:
            odds = total[key].split('@')[-1].strip()
            emoji = rate_odds(odds)
            lines.append(f"- {key}: {odds} {emoji}")

        # Trends section
        lines.append("")
        lines.append(f"📊 Trends:")
        lines.append(f"- {away}: {get_team_trends(away)}")
        lines.append(f"- {home}: {get_team_trends(home)}")

        # Lean (basic example, can be improved)
        lean = f"{away} Moneyline ✅" if moneyline.get(away, 0) > 0 else f"{home} Moneyline ✅"
        lines.append("")
        lines.append(f"🔎 Lean: {lean}")
        lines.append(f"📌 Bet smart. Look for 🔒 low-risk run lines.")

        return "\n".join(lines)

    except Exception as e:
        logging.error(f"Error formatting bet message: {e}")
        return ""

# Send message to Telegram
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            logging.error(f"Telegram send failed: {response.text}")
    except Exception as e:
        logging.error(f"Telegram send error: {e}")

# Main function to send bets in cycles
def send_bets():
    sent_bets = load_sent_bets()
    while True:
        games = fetch_today_games()
        if not games:
            logging.info("No games fetched, retrying in 5 minutes...")
            time.sleep(300)
            continue

        random.shuffle(games)  # Randomize order for fresh picks
        bets_sent_this_cycle = 0

        for game in games:
            # Unique bet ID example: combine teams + commence time
            bet_id = f"{game.get('home_team')}_{game.get('away_team')}_{game.get('commence_time')}"
            if bet_id in sent_bets:
                continue  # Skip duplicate bets

            message = format_bet_message(game)
            if message:
                send_telegram_message(message)
                logging.info(f"Sent bet: {bet_id}")
                sent_bets.add(bet_id)
                bets_sent_this_cycle += 1

            if bets_sent_this_cycle >= MAX_BETS_PER_CYCLE:
                break

        save_sent_bets(sent_bets)
        logging.info(f"Cycle complete: sent {bets_sent_this_cycle} bets. Sleeping for {PAUSE_MINUTES} minutes.")
        time.sleep(PAUSE_MINUTES * 60)


if __name__ == "__main__":
    send_bets()
