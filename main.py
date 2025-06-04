import requests
import datetime
import pytz
import os
from telegram import Bot

# Your credentials
ODDS_API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# Time range setup
def get_current_utc_window():
    now = datetime.datetime.now(pytz.utc)
    three_days_later = now + datetime.timedelta(days=3)
    return now.isoformat(), three_days_later.isoformat()

# Odds formatting
def american_to_implied(odds):
    if odds < 0:
        return -odds / (-odds + 100)
    return 100 / (odds + 100)

def calculate_value(odds, implied_prob):
    fair_prob = american_to_implied(odds)
    return round((implied_prob - fair_prob) * 100, 2)

# Fetch bets from OddsAPI
def fetch_mlb_bets():
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/"
    params = {
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
        "apiKey": ODDS_API_KEY
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("❌ Error fetching bets:", e)
        return []

# Filter and format bets
def filter_and_format_bets(games):
    messages = []
    for game in games:
        teams = game.get("home_team") + " vs " + game.get("away_team")
        commence = game.get("commence_time", "")[:16].replace("T", " ")
        for bookmaker in game.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] != "h2h":
                    continue
                outcomes = market.get("outcomes", [])
                if len(outcomes) != 2:
                    continue
                a, b = outcomes
                prob_a = american_to_implied(a["price"])
                prob_b = american_to_implied(b["price"])
                margin = prob_a + prob_b

                if margin < 1.05:  # Bookmaker margin under 5%
                    label = a["name"] if prob_a > prob_b else b["name"]
                    odds = a["price"] if prob_a > prob_b else b["price"]
                    confidence = round(max(prob_a, prob_b) * 100, 2)
                    message = f"🔥 *MLB Value Bet*\n\n📅 {commence}\n🆚 {teams}\n🏆 Pick: *{label}* at odds {odds}\n🔍 Confidence: *{confidence}%*\n📈 Market edge: Low margin"
                    messages.append(message)
    return messages

# Telegram sender
def send_to_telegram(messages):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    for msg in messages:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="Markdown")

def main():
    games = fetch_mlb_bets()
    if not games:
        print("🚫 No bets found.")
        return
    messages = filter_and_format_bets(games)
    if messages:
        send_to_telegram(messages)
    else:
        print("🟡 No high-quality bets detected.")

if __name__ == "__main__":
    main()
