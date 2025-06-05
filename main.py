import requests
import time
from bet_formatter import format_bet_message

# 🔐 Replace with your credentials
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"
ODDS_API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"

# ✅ Pull real bets from OddsAPI
def fetch_real_bets():
    url = "https://api.the-odds-api.com/v4/sports/soccer/odds"
    params = {
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
        "apiKey": ODDS_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"❌ Error fetching bets: {e}")
        return []

# 📊 Filter bets based on value
def filter_value_bets(data):
    good_bets = []

    for match in data:
        for bookmaker in match.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    if outcome.get("price") >= 130 and outcome.get("price") <= 170:
                        bet = {
                            "league": match.get("sport_key", "Unknown League"),
                            "teams": f"{match['home_team']} vs {match['away_team']}",
                            "odds": f"+{outcome['price']}",
                            "win_prob": round(100 / (abs(outcome['price']) / 100), 1),
                            "quality": "green",
                            "reasoning": "Odds show clear value in current lines vs implied probability.",
                            "start_time": match.get("commence_time", "Unknown Time")
                        }
                        good_bets.append(bet)

    return good_bets

# 🚀 Send message to Telegram
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to send to Telegram: {e}")

def main():
    print("📡 Fetching real bets...")
    bets_data = fetch_real_bets()

    if not bets_data:
        print("❌ No data returned.")
        return

    good_bets = filter_value_bets(bets_data)

    if not good_bets:
        print("⚠️ No high-quality bets found.")
        return

    for bet in good_bets:
        message = format_bet_message(bet)
        print("✅ Sending:\n", message)
        send_to_telegram(message)
        time.sleep(2)

if __name__ == "__main__":
    main()
