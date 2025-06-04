import requests
import time
import os
from datetime import datetime
import pytz

# --- CONFIG ---
ODDS_API_KEY = "183b79e95844e2300faa30f9383890b5"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

LEAGUES = "australia_brisbane_premier_league,australia_queensland_premier_league,usa_usl_league_two,usa_usl_w_league,usa_wpsl,soccer_friendly_women,basketball_wnba"
REGION = "us"
ODDS_FORMAT = "american"

def implied_prob(odds):
    return abs(odds) / (abs(odds) + 100) if odds < 0 else 100 / (odds + 100)

def expected_value(prob, odds):
    win = prob * (odds if odds > 0 else 100)
    loss = (1 - prob) * (100 if odds > 0 else abs(odds))
    return win - loss

def classify_bet(ev, prob):
    if ev > 10 and prob >= 0.60:
        return "🟢 Good", "Strong value + high win chance"
    elif ev > 0 and prob >= 0.52:
        return "🟡 Okay", "Moderate edge, lower confidence"
    else:
        return "🔴 Bad", "Low value or poor win rate"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, data=data)

def fetch_and_send_bets():
    url = f"https://api.the-odds-api.com/v4/sports/?apiKey={API_KEY}"
    sports = requests.get(url).json()

    odds_url = f"https://api.the-odds-api.com/v4/sports/soccer/odds/?regions={REGION}&markets=h2h&oddsFormat={ODDS_FORMAT}&apiKey={API_KEY}"

    response = requests.get(odds_url)
    if response.status_code != 200:
        print("Failed to fetch odds:", response.text)
        return

    data = response.json()

    for match in data:
        home = match['home_team']
        away = match['away_team']
        league = match['sport_title']
        commence_time = datetime.strptime(match['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
        local_time = commence_time.replace(tzinfo=pytz.utc).astimezone(pytz.timezone("US/Eastern"))
        formatted_time = local_time.strftime("%Y-%m-%d %I:%M %p %Z")

        for bookmaker in match['bookmakers']:
            for market in bookmaker['markets']:
                for outcome in market['outcomes']:
                    team = outcome['name']
                    odds = int(outcome['price'])

                    # Estimated win probability (temporary default until model is ready)
                    model_prob = 0.57  # Default safe starter guess
                    implied = implied_prob(odds)
                    ev = expected_value(model_prob, odds)
                    label, reason = classify_bet(ev, model_prob)

                    # Filter only safe, decent value bets
                    if label == "🟢 Good" or label == "🟡 Okay":
                        message = f"""
*⚽ {home} vs {away}*
🏆 League: {league}
🕒 Time: {formatted_time}

📍 Pick: *{team}*
💰 Odds: `{odds}`
📊 Win Chance: `{model_prob*100:.1f}%`
📈 EV: `{ev:.2f}`
🔎 Rating: {label} – _{reason}_
"""
                        send_telegram_message(message)
                        time.sleep(1)

# Run the scraper
fetch_and_send_bets()
