from datetime import datetime, timedelta, timezone
import requests
import telegram

# 🔐 Your credentials (already filled in)
API_KEY = "183b79e95844e2300faa30f9383890b5"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# 📊 Leagues to track
LEAGUES = [
    "soccer_argentina_primera_division",
    "soccer_brazil_campeonato",
    "soccer_usa_mls",
    "basketball_wnba"
]

BOOKMAKER = "bovada"
REGION = "us"
MARKET = "h2h"
THRESHOLD = 3.5  # Minimum edge % to alert

# 📅 Define this week's window (starting from June 4, 2025)
WEEK_START = datetime(2025, 6, 4, tzinfo=timezone.utc)
WEEK_END = WEEK_START + timedelta(days=6)

# 🧮 Helpers
def format_american_odds(odds):
    odds = int(odds)
    return f"+{odds}" if odds > 0 else str(odds)

def implied_prob(odds):
    odds = int(odds)
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

# 🔍 Value detection
def get_value_bets():
    messages = []
    for league in LEAGUES:
        url = (
            f"https://api.the-odds-api.com/v4/sports/{league}/odds/?"
            f"apiKey={API_KEY}&regions={REGION}&markets={MARKET}&bookmakers={BOOKMAKER}&oddsFormat=american"
        )
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Error fetching odds for {league}: {response.status_code}")
                continue

            data = response.json()
            for match in data:
                try:
                    commence_time = datetime.fromisoformat(match["commence_time"].replace("Z", "+00:00"))
                    if commence_time < WEEK_START or commence_time > WEEK_END:
                        continue  # Skip matches not within this week

                    home_team = match.get("home_team", "Home")
                    away_team = match.get("away_team", "Away")
                    readable_time = commence_time.strftime("%A, %b %d at %I:%M %p UTC")

                    for bookmaker in match.get("bookmakers", []):
                        for market in bookmaker.get("markets", []):
                            for outcome in market.get("outcomes", []):
                                team = outcome.get("name")
                                odds = outcome.get("price")
                                if team is None or odds is None:
                                    continue

                                prob = implied_prob(odds)
                                edge = (1 - prob) * 100

                                if edge >= THRESHOLD:
                                    odds_display = format_american_odds(odds)
                                    quality = "🟢 Good Bet" if edge >= 5 else "🟡 Okay Bet"
                                    reason = (
                                        "This bet has a strong positive expected value."
                                        if edge >= 5 else
                                        "This bet has moderate positive expected value."
                                    )

                                    msg = (
                                        f"📅 {readable_time}\n"
                                        f"{home_team} vs {away_team}\n"
                                        f"💰 Bet: {team}\n"
                                        f"📈 Odds: {odds_display} (American)\n"
                                        f"🧠 Edge: {edge:.2f}% {quality}\n"
                                        f"📌 Reason: {reason}"
                                    )
                                    messages.append(msg)
                except Exception as e:
                    print(f"Error parsing match in {league}: {e}")
        except Exception as e:
            print(f"Error in league {league}: {e}")
    return messages

# 📤 Send alerts to Telegram
def send_to_telegram(messages):
    if not messages:
        print("No value bets found.")
        return
    bot = telegram.Bot(token=BOT_TOKEN)
    for msg in messages:
        try:
            bot.send_message(chat_id=CHAT_ID, text=msg)
        except Exception as e:
            print(f"Failed to send message: {e}")

# 🟢 Main execution
if __name__ == "__main__":
    value_bets = get_value_bets()
    send_to_telegram(value_bets)
