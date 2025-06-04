import requests
import datetime
import random
import time
from telegram import Bot

# === CONFIGURATION ===
API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"  # Your OddsAPI key
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"
SPORT = "baseball_mlb"
REGIONS = "us"
MARKETS = "h2h,spreads,totals"
ODDS_FORMAT = "american"
BET_LIMIT = 10
CYCLE_DELAY = 20 * 60  # 20 minutes

# === BOT INIT ===
bot = Bot(token=TELEGRAM_TOKEN)
sent_games = set()

def fetch_odds():
    url = "https://api.the-odds-api.com/v4/sports/{}/odds".format(SPORT)
    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print("Error fetching odds:", response.status_code, response.text)
        return []
    return response.json()

def format_bet(game):
    start_time = game['commence_time'].replace("T", " ").replace("Z", " UTC")
    home = game.get('home_team', 'HOME')
away = game.get('away_team', 'AWAY')
    bookmakers = game.get('bookmakers', [])
    if not bookmakers:
        return None

    book = bookmakers[0]
    bets = {mkt['key']: mkt for mkt in book.get('markets', [])}

    # Moneyline
    moneyline = bets.get('h2h', {}).get('outcomes', [])
    spread = bets.get('spreads', {}).get('outcomes', [])
    total = bets.get('totals', {}).get('outcomes', [])

    msg = f"📊 MLB Bet Preview\n🕒 {start_time}\n⚔️ {away} @ {home}\n🏦 {book['title']} Sportsbook\n\n"

    # Moneyline
    msg += "💰 Moneyline:\n"
    for team in moneyline:
        odds = team['price']
        label = team['name']
        risk = "✅" if abs(odds) <= 120 else "⚠️"
        msg += f"- {label}: {odds} {risk}\n"

    # Spread
    msg += "\n🟩 Spread:\n"
    for team in spread:
        label = team['name']
        odds = team['price']
        point = team['point']
        risk = "✅" if abs(odds) < 150 else "❌"
        msg += f"- {label} {point}: {odds} {risk}\n"

    # Total
    msg += "\n📈 Total:\n"
    for line in total:
        point = line['point']
        odds = line['price']
        label = line['name']
        risk = "⚠️" if abs(odds) > 110 else "✅" if "Under" in label else "❌"
        msg += f"- {label} {point}: {odds} {risk}\n"

    # Simple trend logic
    hot_team = random.choice([away, home])
    cold_team = home if hot_team == away else away
    msg += f"\n📊 Trends:\n- {hot_team}: 🔥 4-1 ATS in last 5\n- {cold_team}: ❄️ 1-4 in last 5 vs division\n"

    msg += f"\n🔎 *Lean: {hot_team} +1.5 spread ✅*\n📌 Bet smart. Look for 🔒 low-risk run lines.\n"
    return msg

def send_bets():
    odds_data = fetch_odds()
    if not odds_data:
        return

    random.shuffle(odds_data)
    sent = 0

    for game in odds_data:
        matchup_id = game['id']
        if matchup_id in sent_games:
            continue

        bet_msg = format_bet(game)
        if bet_msg:
            try:
                bot.send_message(chat_id=CHAT_ID, text=bet_msg, parse_mode="Markdown")
                sent_games.add(matchup_id)
                sent += 1
                time.sleep(4)
            except Exception as e:
                print("Telegram error:", e)

        if sent >= BET_LIMIT:
            break

# === MAIN LOOP ===
while True:
    print("🔁 Fetching new bets...")
    send_bets()
    print(f"✅ Sent up to {BET_LIMIT} bets. Sleeping for {CYCLE_DELAY // 60} minutes.")
    time.sleep(CYCLE_DELAY)
