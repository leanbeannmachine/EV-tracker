import requests
import datetime
import pytz
import os

# 🔐 CONFIG: Set your API key and Telegram details here
API_KEY = "183b79e95844e2300faa30f9383890b5"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# ✅ Leagues to monitor
LEAGUES = [
    "soccer_argentina_primera_division",
    "soccer_brazil_campeonato",
    "soccer_usa_mls",
    "basketball_wnba"
]

BOOKMAKER = "bovada"
REGION = "us"
MIN_EDGE = 5.0  # Only show bets with at least 5% edge

# 📤 Telegram Message Sender
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=data)

# 🇺🇸 American Odds Formatter
def format_american_odds(odds):
    odds = int(odds)
    return f"+{odds}" if odds > 0 else str(odds)

# 📈 Convert American odds to implied probability
def implied_prob(odds):
    odds = int(odds)
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

# 📌 Main Fetch and Send Logic
def fetch_and_send_bets():
    now = datetime.datetime.now(pytz.utc)
    messages = []

    for league in LEAGUES:
        url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={API_KEY}&regions={REGION}&markets=h2h&bookmakers={BOOKMAKER}"

        try:
            res = requests.get(url)
            if res.status_code != 200:
                print(f"Error fetching odds for {league}: {res.status_code}")
                continue

            data = res.json()
            for match in data:
                try:
                    teams = match["teams"]
                    commence_time = datetime.datetime.fromisoformat(match["commence_time"].replace("Z", "+00:00"))

                    if commence_time < now:
                        continue  # Skip past games

                    bookmaker = match["bookmakers"][0]
                    outcomes = bookmaker["markets"][0]["outcomes"]

                    for outcome in outcomes:
                        team = outcome["name"]
                        odds = outcome["price"]
                        prob = implied_prob(odds)
                        edge = (1 / prob) - 1

                        # Filter only good bets (green zone)
                        if edge * 100 >= MIN_EDGE:
                            american_odds = format_american_odds(odds)
                            edge_percent = edge * 100

                            color = "🟢 Good Bet" if edge_percent >= 10 else "🟡 Okay Bet"
                            reason = "This bet has a positive expected value and is a strong value play." if edge_percent >= 10 else "This bet is okay but not elite."

                            messages.append(
                                f"{teams[0]} vs {teams[1]}\n"
                                f"Bet: {team}\n"
                                f"Odds: {american_odds} (American)\n"
                                f"Edge: {edge_percent:.2f}% {color}\n"
                                f"Reason: {reason}"
                            )
                            print(f"{team} @ {american_odds} ➝ Prob: {prob:.2f}, Edge: {edge:.2f}")

                except Exception as parse_err:
                    print(f"Error parsing match in {league}: {parse_err}")

        except Exception as fetch_err:
            print(f"Error in league {league}: {fetch_err}")

    # Send messages if we have them
    for msg in messages:
        send_telegram_message(msg)

# 🔁 Run Script
if __name__ == "__main__":
    fetch_and_send_bets()
