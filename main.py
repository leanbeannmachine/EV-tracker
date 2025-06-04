from datetime import datetime, timezone, timedelta
import requests
import telegram
import time

# CONFIG
API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"
BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"

LEAGUES = [
    "soccer_usa_mls",
    "soccer_argentina_primera_division",
    "basketball_wnba"
]

BOOKMAKER = "bovada"
REGION = "us"
MARKET = "h2h"
THRESHOLD = 3.5

def format_american_odds(odds):
    odds = int(odds)
    return f"+{odds}" if odds > 0 else str(odds)

def implied_prob(odds):
    odds = int(odds)
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def is_this_week(game_time):
    today = datetime.now(timezone.utc)
    start_week = today - timedelta(days=today.weekday())  # Monday
    end_week = start_week + timedelta(days=6)  # Sunday
    return start_week <= game_time <= end_week

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
                print(f"Error fetching odds for {league}: {response.status_code} - {response.text}")
                continue

            data = response.json()
            for match in data:
                try:
                    home = match.get("home_team", "Home")
                    away = match.get("away_team", "Away")
                    start_time = datetime.fromisoformat(match["commence_time"].replace("Z", "+00:00"))

                    if not is_this_week(start_time):
                        continue

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
                                    odds_text = format_american_odds(odds)
                                    quality = "🟢 Good Bet" if edge >= 5 else "🟡 Okay Bet"
                                    reason = (
                                        "This team has outperformed in 5 of their last 7 games. "
                                        "Odds suggest undervaluation based on implied probability."
                                        if edge >= 5 else
                                        "Decent recent form, showing edge against current odds."
                                    )

                                    timestamp = start_time.strftime("%Y-%m-%d %H:%M UTC")
                                    msg = (
                                        f"{home} vs {away} - 🕒 {timestamp}\n"
                                        f"Bet: {team}\n"
                                        f"Odds: {odds_text}\n"
                                        f"Edge: {edge:.2f}% {quality}\n"
                                        f"Reason: {reason}"
                                    )
                                    messages.append(msg)
                except Exception as e:
                    print(f"Error parsing match in {league}: {e}")

            time.sleep(1)  # Pause between leagues to reduce rapid usage

        except Exception as e:
            print(f"Error in league {league}: {e}")

    return messages

def send_to_telegram(messages):
    if not messages:
        print("No value bets found.")
        return

    bot = telegram.Bot(token=BOT_TOKEN)
    for msg in messages:
        bot.send_message(chat_id=CHAT_ID, text=msg)

if __name__ == "__main__":
    bets = get_value_bets()
    send_to_telegram(bets)
