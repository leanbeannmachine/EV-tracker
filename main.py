import requests
from datetime import datetime
from telegram import Bot

# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
ODDS_API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"
SPORT = "baseball_mlb"
REGION = "us"
MARKETS = "h2h,spreads,totals,player_props"

# === SETUP ===
bot = Bot(token=TELEGRAM_BOT_TOKEN)
today_iso = datetime.utcnow().date().isoformat()
base_url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"

# === STEP 1: FETCH TODAY’S GAMES ===
params = {
    "regions": REGION,
    "markets": MARKETS,
    "oddsFormat": "american",
    "dateFormat": "iso",
    "apiKey": ODDS_API_KEY
}
response = requests.get(base_url, params=params)

if response.status_code != 200:
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🚨 OddsAPI Error: {response.status_code}\n{response.text}")
    exit()

games = response.json()
sent_count = 0

# === STEP 2: PROCESS EACH GAME ===
for game in games:
    # Only include games starting today
    if not game.get("commence_time", "").startswith(today_iso):
        continue

    home = game.get("home_team")
    away = game.get("away_team")
    commence_time = game.get("commence_time")[:19].replace("T", " ")

    # Bookmaker odds
    for book in game.get("bookmakers", []):
        book_title = book.get("title", "N/A")

        msg = f"📊 *MLB Bet Preview*\n🕒 *{commence_time} UTC*\n⚔️ {away} @ {home}\n🏦 Bookmaker: {book_title}\n"

        has_lines = False

        for market in book.get("markets", []):
            key = market.get("key")
            outcomes = market.get("outcomes", [])

            if key == "spreads":
                for o in outcomes:
                    team = o["name"]
                    point = o["point"]
                    odds = o["price"]
                    msg += f"🟩 Spread - {team}: {point} @ {odds}\n"
                    has_lines = True

            elif key == "totals":
                for o in outcomes:
                    label = "Over" if o["name"] == "Over" else "Under"
                    point = o["point"]
                    odds = o["price"]
                    emoji = "📈" if label == "Over" else "📉"
                    msg += f"{emoji} {label} {point} runs: {odds}\n"
                    has_lines = True

            elif key == "player_props":
                standout_players = [p for p in outcomes if abs(p.get("price", 0)) >= 130]  # Filter only standout odds
                for p in standout_players:
                    name = p.get("name")
                    odds = p.get("price")
                    risk = "🟢 Good" if abs(odds) <= 150 else "⚠️ Medium"
                    msg += f"🎯 {name} prop @ {odds} ({risk})\n"
                    has_lines = True

        if has_lines:
            msg += "\n📌 Bet smart. Prioritize 🔒 safe value."
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="Markdown")
            sent_count += 1

# === IF NO GAMES SENT ===
if sent_count == 0:
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="📭 No standout MLB bets found for today.")
