import requests
import time
from datetime import datetime
import pytz

# ✅ Your API keys
ODDS_API_KEY = "183b79e95844e2300faa30f9383890b5"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# ✅ Set target leagues
LEAGUES = [
    "soccer_australia_queensland_premier_league",
    "soccer_australia_brisbane_premier_league",
    "soccer_usa_usl_league_two",
    "soccer_usa_usl_w_league",
    "soccer_usa_wpsl",
    "soccer_friendly_women",
    "basketball_wnba"
]

# ✅ Bet quality threshold
GOOD_THRESHOLD = 70  # green
OKAY_THRESHOLD = 60  # yellow

# ✅ Send message to Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, json=payload)

# ✅ Determine bet quality
def classify_bet(probability):
    if probability >= GOOD_THRESHOLD:
        return "✅ GOOD (Green)", "High win probability — smart value"
    elif probability >= OKAY_THRESHOLD:
        return "⚠️ OKAY (Yellow)", "Moderate win chance — evaluate carefully"
    else:
        return "❌ BAD (Red)", "Low win chance — avoid for bankroll safety"

# ✅ Convert decimal to American odds
def decimal_to_american(decimal_odds):
    if decimal_odds >= 2.0:
        return f"+{int((decimal_odds - 1) * 100)}"
    else:
        return f"-{int(100 / (decimal_odds - 1))}"

# ✅ Fetch and send bets
def fetch_and_send_bets():
    for league in LEAGUES:
        url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={ODDS_API_KEY}&regions=us&markets=h2h&oddsFormat=decimal"
        response = requests.get(url)

        if response.status_code != 200:
            send_telegram_message(f"Error fetching odds for {league}: {response.status_code}")
            continue

        data = response.json()
        for game in data:
            teams = game['teams']
            commence_time = datetime.fromisoformat(game['commence_time']).astimezone(pytz.timezone("US/Eastern"))
            time_str = commence_time.strftime('%Y-%m-%d %I:%M %p ET')

            for bookmaker in game['bookmakers']:
                for market in bookmaker['markets']:
                    if market['key'] == "h2h":
                        outcomes = market['outcomes']
                        for outcome in outcomes:
                            team = outcome['name']
                            decimal_odds = outcome['price']
                            american_odds = decimal_to_american(decimal_odds)
                            implied_prob = round(100 / decimal_odds, 2)
                            quality, reasoning = classify_bet(implied_prob)

                            if quality == "✅ GOOD (Green)" or quality == "⚠️ OKAY (Yellow)":
                                message = (
                                    f"📊 *{quality}*\n"
                                    f"🏟️ League: {league.replace('soccer_', '').replace('_', ' ').title()}\n"
                                    f"🆚 {teams[0]} vs {teams[1]}\n"
                                    f"🕒 {time_str}\n"
                                    f"🔮 Bet: {team}\n"
                                    f"💰 Odds: {american_odds}\n"
                                    f"📈 Win %: {implied_prob}%\n"
                                    f"💡 Reason: {reasoning}"
                                )
                                send_telegram_message(message)
        time.sleep(1)  # Pause to avoid hitting API rate limits

# ✅ Start the bot
if __name__ == "__main__":
    fetch_and_send_bets()
