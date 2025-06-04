import requests
import os

# Your OddsAPI key (already provided)
API_KEY = "183b79e95844e2300faa30f9383890b5"

# Your Telegram Bot token and chat ID (replace with your actual values)
BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"
# 1. Fetch soccer odds from OddsAPI
def fetch_odds():
    url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "eu",      # European sportsbooks
        "markets": "h2h",     # Head-to-head (moneyline)
        "oddsFormat": "decimal"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Failed to fetch odds: {e}")
        return []

# 2. Format bets to send to Telegram
def format_bets(bets):
    formatted = []
    for game in bets:
        teams = game['home_team'], [team for team in game['bookmakers'][0]['markets'][0]['outcomes'] if team['name'] != game['home_team']][0]['name']
        bookmaker = game['bookmakers'][0]
        market = bookmaker['markets'][0]
        outcomes = market['outcomes']
        lines = [f"{o['name']} @ {o['price']}" for o in outcomes]
        msg = f"🏟️ *{game['home_team']} vs {game['away_team']}*\n📅 {game['commence_time']}\n\n" + "\n".join(lines)
        formatted.append(msg)
    return formatted

# 3. Send message to Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("✅ Message sent to Telegram")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")

# 4. Main flow
def main():
    print("🔎 Fetching odds...")
    bets = fetch_odds()
    if not bets:
        print("⚠️ No bets found.")
        return

    formatted_bets = format_bets(bets[:5])  # Only send first 5 to avoid spam
    for bet in formatted_bets:
        send_telegram_message(bet)

if __name__ == "__main__":
    main()
