 import requests
import pytz
from datetime import datetime
import os
import time

API_KEY = "183b79e95844e2300faa30f9383890b5"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
THRESHOLD_GOOD = 70
THRESHOLD_OKAY = 55

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, json=payload)

def calculate_win_probability(odds):
    if odds > 0:
        return round(100 / (odds / 100 + 1), 2)
    else:
        return round(abs(odds) / (abs(odds) + 100) * 100, 2)

def get_bet_quality(prob):
    if prob >= THRESHOLD_GOOD:
        return "🟢 Good bet"
    elif prob >= THRESHOLD_OKAY:
        return "🟡 Okay bet"
    else:
        return "🔴 Risky bet"

def fetch_active_leagues():
    url = f"https://api.the-odds-api.com/v4/sports/?apiKey={API_KEY}"
    response = requests.get(url)
    return [sport['key'] for sport in response.json() if sport['active']]

def fetch_and_send_bets():
    leagues = fetch_active_leagues()
    for league in leagues:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{league}/odds/?apiKey={API_KEY}&regions=us&markets=h2h&oddsFormat=american"
            response = requests.get(url)
            if response.status_code == 404:
                continue
            games = response.json()

            for game in games:
                teams = game['teams']
                commence_time = datetime.fromisoformat(game['commence_time'].replace("Z", "+00:00"))
                odds_data = game['bookmakers'][0]['markets'][0]['outcomes']

                message = f"📊 *{league.replace('_', ' ').title()}*\n⏰ {commence_time.strftime('%Y-%m-%d %I:%M %p')} UTC\n"

                for outcome in odds_data:
                    name = outcome['name']
                    odds = outcome['price']
                    win_prob = calculate_win_probability(odds)
                    quality = get_bet_quality(win_prob)
                    message += f"\n{name}: {odds} odds\n🧮 Win %: {win_prob}%\n{quality}"

                send_telegram_message(message)
                time.sleep(1)

        except Exception as e:
            print(f"Error fetching odds for {league}: {str(e)}")

fetch_and_send_bets()
