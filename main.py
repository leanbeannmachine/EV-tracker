import requests
from datetime import datetime
import pytz
import os
import telegram

API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

MLB_URL = "https://api.the-odds-api.com/v4/sports/baseball_ml/mlb/odds"

HEADERS = {"accept": "application/json"}
MARKETS = ['h2h', 'spreads', 'totals']
BOOKMAKERS = ['pinnacle', 'betonlineag']
MIN_EV = 5.0

def calc_implied_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)

def calc_ev(implied_prob, model_prob, odds):
    edge = model_prob - implied_prob
    return round(edge * 100, 1), round(model_prob * 100, 1), round(implied_prob * 100, 1)

def get_color_tag(ev):
    if ev >= 7.0:
        return '💎🟢 BEST VALUE'
    elif ev >= 5.0:
        return '🟡 GOOD VALUE'
    return None

def get_data():
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": ",".join(MARKETS),
        "oddsFormat": "american",
        "bookmakers": ",".join(BOOKMAKERS)
    }
    response = requests.get(MLB_URL, headers=HEADERS, params=params)
    return response.json()

def convert_time(utc_time):
    dt = datetime.fromisoformat(utc_time.replace("Z", "+00:00"))
    cdt = dt.astimezone(pytz.timezone("America/Chicago"))
    return cdt.strftime("%b %d, %I:%M %p CDT")

def get_best_bets(game):
    game_time = convert_time(game["commence_time"])
    teams = f'{game["home_team"]} vs {game["away_team"]}'

    h2h = {}
    spread = {}
    total = {}

    for bookmaker in game["bookmakers"]:
        for market in bookmaker["markets"]:
            if market["key"] == "h2h":
                for outcome in market["outcomes"]:
                    prob = calc_implied_prob(outcome["price"])
                    model_prob = 0.55  # TEMP STATIC, replace w/ model later
                    ev, model, implied = calc_ev(prob, model_prob, outcome["price"])
                    tag = get_color_tag(ev)
                    if tag and (not h2h or ev > h2h["ev"]):
                        h2h = {
                            "team": outcome["name"],
                            "odds": outcome["price"],
                            "ev": ev,
                            "model": model,
                            "implied": implied,
                            "tag": tag
                        }

            if market["key"] == "spreads":
                for outcome in market["outcomes"]:
                    prob = calc_implied_prob(outcome["price"])
                    model_prob = 0.54  # TEMP STATIC
                    ev, model, implied = calc_ev(prob, model_prob, outcome["price"])
                    tag = get_color_tag(ev)
                    if tag and (not spread or ev > spread["ev"]):
                        spread = {
                            "pick": f"{outcome['name']} {outcome['point']:+}",
                            "odds": outcome["price"],
                            "ev": ev,
                            "model": model,
                            "implied": implied,
                            "tag": tag
                        }

            if market["key"] == "totals":
                for outcome in market["outcomes"]:
                    prob = calc_implied_prob(outcome["price"])
                    model_prob = 0.575  # TEMP STATIC
                    ev, model, implied = calc_ev(prob, model_prob, outcome["price"])
                    tag = get_color_tag(ev)
                    if tag and (not total or ev > total["ev"]):
                        total = {
                            "pick": f"{outcome['name'].title()} {market['outcomes'][0]['point']}",
                            "odds": outcome["price"],
                            "ev": ev,
                            "model": model,
                            "implied": implied,
                            "tag": tag
                        }

    if not (h2h or spread or total):
        return None

    msg = f"""🏟️ {teams}
📅 {game_time}"""

    if h2h:
        msg += f"""

━━━━━━━━━━━━━━━━━━
📊 MONEYLINE BET
🔥 Pick: {h2h['team']}
💵 Odds: {h2h['odds']}
📈 Expected Value: +{h2h['ev']}% {h2h['tag']}
🧮 Implied Prob: {h2h['implied']}%
🧠 Model Prob: {h2h['model']}%
🔍 Edge: +{h2h['ev']}%
⚾ ——————"""

    if spread:
        msg += f"""

📊 SPREAD BET
🔥 Pick: {spread['pick']}
💵 Odds: {spread['odds']}
📈 Expected Value: +{spread['ev']}% {spread['tag']}
🧮 Implied Prob: {spread['implied']}%
🧠 Model Prob: {spread['model']}%
🔍 Edge: +{spread['ev']}%
⚾ ——————"""

    if total:
        msg += f"""

📊 TOTALS BET
🔥 Pick: {total['pick']}
💵 Odds: {total['odds']}
📈 Expected Value: +{total['ev']}% {total['tag']}
🧮 Implied Prob: {total['implied']}%
🧠 Model Prob: {total['model']}%
🔍 Edge: +{total['ev']}%
⚾ ——————"""

    return msg

def send_alerts():
    games = get_data()
    bot = telegram.Bot(token=BOT_TOKEN)
    for game in games:
        msg = get_best_bets(game)
        if msg:
            bot.send_message(chat_id=CHAT_ID, text=msg)

if __name__ == "__main__":
    send_alerts()
