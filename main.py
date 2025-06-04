import requests
import pytz
from datetime import datetime
import os

# --- Configuration ---
ODDS_API_KEY = "183b79e95844e2300faa30f9383890b5"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

LEAGUES = [
    "soccer_argentina_primera_division",
    "soccer_brazil_campeonato",
    "soccer_usa_mls",
    "basketball_wnba"
]

THRESHOLD_GREEN = 60  # % win probability = Green (safe)
THRESHOLD_YELLOW = 50  # % = Yellow (okay)
# Anything below = Red

# --- Helpers ---
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=data)

def calculate_implied_probability(odds):
    if odds > 0:
        return 100 / (odds + 100) * 100
    else:
        return abs(odds) / (abs(odds) + 100) * 100

def odds_to_american(decimal_odds):
    if decimal_odds >= 2:
        return f"+{round((decimal_odds - 1) * 100)}"
    else:
        return f"-{round(100 / (decimal_odds - 1))}"

def evaluate_bet(prob):
    if prob >= THRESHOLD_GREEN:
        return "🟢 Good", "High implied value."
    elif prob >= THRESHOLD_YELLOW:
        return "🟡 Okay", "Moderate risk."
    else:
        return "🔴 Risky", "Too low probability."

# --- Main Logic ---
def fetch_and_send_bets():
    for league in LEAGUES:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={API_KEY}&regions=us&markets=h2h&oddsFormat=american"
            res = requests.get(url)

            if res.status_code != 200:
                print(f"Error fetching odds for {league}: {res.status_code}")
                continue

            matches = res.json()
            for match in matches:
                teams = match.get("teams")
                if not teams or len(teams) != 2:
                    print(f"Error parsing match in {league}: teams missing")
                    continue

                home, away = teams
                commence_time = datetime.fromisoformat(match["commence_time"].replace("Z", "+00:00"))
                commence_str = commence_time.strftime("%Y-%m-%d %H:%M UTC")

                bookmakers = match.get("bookmakers", [])
                if not bookmakers:
                    continue

                for book in bookmakers:
                    markets = book.get("markets", [])
                    for market in markets:
                        if market["key"] != "h2h":
                            continue
                        outcomes = market.get("outcomes", [])
                        for outcome in outcomes:
                            team = outcome["name"]
                            price = outcome.get("price")
                            if price is None:
                                continue

                            probability = round(calculate_implied_probability(price), 2)
                            rating, reasoning = evaluate_bet(probability)
                            american_odds = f"{price:+}"

                            message = (
                                f"{rating} {reasoning}\n"
                                f"📅 {commence_str}\n"
                                f"🏆 {league.replace('_', ' ').title()}\n"
                                f"🔢 Bet: {team} at {american_odds}\n"
                                f"📊 Win Probability: {probability}%"
                            )

                            if rating == "🟢 Good":
                                send_telegram_message(message)
        except Exception as e:
            print(f"Error in league {league}: {e}")

# --- Run It ---
fetch_and_send_bets()
