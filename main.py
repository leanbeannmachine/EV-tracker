import requests
from datetime import datetime, timedelta, timezone
import telegram
import random
import time

# ==== CONFIG ====
API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"

# Threshold for edge % to consider a bet valuable
EDGE_THRESHOLD = 3.5

# Markets to check and their friendly names
MARKET_NAMES = {
    "h2h": "Moneyline",
    "spreads": "Spread",
    "totals": "Total Points",
    "double_chance": "Double Chance"
}

# Initialize Telegram bot
bot = telegram.Bot(token=BOT_TOKEN)


def format_american_odds(odds):
    try:
        odds = int(odds)
        return f"+{odds}" if odds > 0 else str(odds)
    except (TypeError, ValueError):
        return str(odds)


def implied_prob(odds):
    try:
        odds = int(odds)
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0


def fetch_fixtures():
    now = datetime.now(timezone.utc)
    in_3_days = now + timedelta(days=3)

    start_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = in_3_days.strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "api_token": API_KEY,
        "include": "odds.bookmakers.markets",
        "filter[starts_between]": f"{start_str},{end_str}",
        "sort": "starting_at",
        "per_page": 50
    }

    url = "https://api.sportmonks.com/v3/football/fixtures"

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"API request error: {e}")
        return None


def generate_reason(market, outcome, edge):
    """Basic reason generator for demo purposes"""
    reasons = [
        f"Value detected in {MARKET_NAMES.get(market, market)} market",
        f"Market inefficiency suggests {outcome['name']} is undervalued",
        f"Statistical edge of {edge:.1f}% detected",
        f"Good risk/reward based on recent trends"
    ]
    return random.choice(reasons)


def process_and_send_bets():
    data = fetch_fixtures()
    if not data or "data" not in data:
        bot.send_message(chat_id=CHAT_ID, text="No fixtures found or error occurred.")
        return

    fixtures = data["data"]
    sent_bets = 0

    for fixture in fixtures:
        fixture_id = fixture.get("id")
        home_team = fixture.get("home_team")
        away_team = fixture.get("away_team")
        start_time = fixture.get("starting_at")
        odds_data = fixture.get("odds", {})
        bookmakers = odds_data.get("data", [])

        if not bookmakers:
            continue

        for bookmaker in bookmakers:
            # You can filter by bookmaker if needed, or just take all
            markets = bookmaker.get("markets", [])
            for market in markets:
                market_key = market.get("key")
                outcomes = market.get("outcomes", [])

                for outcome in outcomes:
                    price = outcome.get("price")
                    if price is None:
                        continue

                    prob = implied_prob(price)
                    if prob == 0:
                        continue

                    edge = (1 - prob) * 100
                    if edge < EDGE_THRESHOLD:
                        continue

                    odds_str = format_american_odds(price)
                    reason = generate_reason(market_key, outcome, edge)

                    message = (
                        f"⚽️ *{home_team}* vs *{away_team}*\n"
                        f"⏰ Starts at: {start_time}\n"
                        f"📊 Market: {MARKET_NAMES.get(market_key, market_key)}\n"
                        f"🎯 Bet: {outcome['name']} @ {odds_str}\n"
                        f"💡 Reason: {reason}\n"
                        f"📈 Edge: {edge:.1f}%"
                    )

                    bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
                    sent_bets += 1
                    # Optional: sleep a bit to avoid spamming too fast
                    time.sleep(1)

    if sent_bets == 0:
        bot.send_message(chat_id=CHAT_ID, text="No good value bets available for the next 3 days.")


if __name__ == "__main__":
    process_and_send_bets()
