import requests
import time
from datetime import datetime
import pytz

# ========== 🔑 CONFIG ==========
API_KEY = "183b79e95844e2300faa30f9383890b5"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
LEAGUES = [
    "soccer_usa_usl_league_two", "soccer_usa_wpsl", "soccer_usa_uslw_league",
    "soccer_australia_queensland_premier_league", "soccer_australia_brisbane_premier_league",
    "soccer_friendly_women", "basketball_wnba"
]

# ========== 🧠 HELPERS ==========

def american_odds(decimal_odds):
    if decimal_odds >= 2.0:
        return f"+{int((decimal_odds - 1) * 100)}"
    else:
        return f"-{int(100 / (decimal_odds - 1))}"

def rating_color(probability):
    if probability >= 0.7:
        return "🟢 GOOD"
    elif probability >= 0.55:
        return "🟡 OKAY"
    else:
        return "🔴 RISKY"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, json=payload)

# ========== 🔍 MAIN FUNCTION ==========

def fetch_and_send_bets():
    for league in LEAGUES:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?regions=us&oddsFormat=decimal&apiKey={API_KEY}"
            res = requests.get(url)
            if res.status_code != 200:
                print(f"Error fetching odds for {league}: {res.status_code}")
                continue

            data = res.json()
            for match in data:
                try:
                    home, away = match['teams']
                    commence_time = match['commence_time']
                    utc_dt = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
                    est_dt = utc_dt.astimezone(pytz.timezone("US/Eastern"))
                    time_str = est_dt.strftime("%Y-%m-%d %I:%M %p")

                    for bookmaker in match.get('bookmakers', []):
                        for market in bookmaker.get('markets', []):
                            if market['key'] != "h2h":
                                continue
                            outcomes = market['outcomes']
                            for outcome in outcomes:
                                name = outcome['name']
                                odds_decimal = outcome['price']
                                odds_american = american_odds(odds_decimal)
                                implied_prob = round(1 / odds_decimal, 2)

                                if implied_prob < 0.55:
                                    continue  # Skip risky

                                rating = rating_color(implied_prob)
                                msg = (
                                    f"{rating} VALUE BET 💰\n\n"
                                    f"{league.replace('soccer_', '').upper()}\n"
                                    f"{home} vs {away} @ {time_str}\n\n"
                                    f"🔹 Pick: {name}\n"
                                    f"🔹 Odds: {odds_american}\n"
                                    f"🔹 Win Chance: {int(implied_prob * 100)}%\n"
                                )
                                send_telegram_message(msg)
                except Exception as e:
                    print(f"Error parsing match in {league}: {e}")
        except Exception as err:
            print(f"Failed to fetch for {league}: {err}")

# ========== ▶️ RUN ==========
if __name__ == "__main__":
    fetch_and_send_bets()
