import requests
from datetime import datetime, timezone
import pytz
import math
import telegram

CDT = pytz.timezone("America/Chicago")

# Replace with your actual Telegram bot/token/chat_id
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# Model probabilities — placeholder, replace with your actual model logic
def get_model_probabilities(team1, team2):
    return {
        "moneyline": {team1: 0.52, team2: 0.48},
        "spread": {team1: 0.53, team2: 0.47},
        "total": {"Over": 0.58, "Under": 0.42}
    }

def implied_prob(odds):
    return abs(odds) / (abs(odds) + 100) if odds > 0 else 100 / (abs(odds) + 100)

def calc_vig(p1, p2):
    return p1 + p2 - 1

def expected_value(prob, odds):
    return ((prob * (abs(odds) / 100)) - (1 - prob)) * 100 if odds > 0 else ((prob * 100 / abs(odds)) - (1 - prob)) * 100

from datetime import datetime, timezone, timedelta
import pytz
import requests

import requests
from datetime import datetime, timedelta

def fetch_bovada_mlb_odds():
    url = "https://www.bovada.lv/services/sports/event/v2/en-us/featured/baseball/mlb"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"❌ Failed to fetch data from Bovada. Status code: {response.status_code}")
        print("⚠️ Response content:", response.text)
        return []

    try:
        data = response.json()[0]["events"]
    except Exception as e:
        print("❌ Failed to parse Bovada JSON:", e)
        print("⚠️ Raw response:", response.text)
        return []

    games = []
    for event in data:
        try:
            home_team = event["competitors"][0]["name"]
            away_team = event["competitors"][1]["name"]
            start_time_utc = datetime.fromtimestamp(event["startTime"] / 1000.0)
            start_time_cdt = start_time_utc - timedelta(hours=5)  # CDT = UTC-5

            markets = event.get("displayGroups", [])[0].get("markets", [])

            moneyline = next((m for m in markets if m["description"] == "Moneyline"), None)
            spread = next((m for m in markets if "Point Spread" in m["description"]), None)
            total = next((m for m in markets if "Total" in m["description"]), None)

            def extract_odds(market):
                if not market or "outcomes" not in market:
                    return {}
                odds_dict = {}
                for outcome in market["outcomes"]:
                    name = outcome["description"]
                    odds = outcome["price"]["american"]
                    # Handle 'EVEN' string safely
                    if odds == "EVEN":
                        odds = 100
                    odds_dict[name] = {
                        "odds": int(odds),
                        "point": outcome.get("price", {}).get("handicap")
                    }
                return odds_dict

            games.append({
                "home_team": home_team,
                "away_team": away_team,
                "start_time_cdt": start_time_cdt.strftime("%b %d, %I:%M %p CDT"),
                "moneyline": extract_odds(moneyline),
                "spread": extract_odds(spread),
                "total": extract_odds(total),
            })
        except Exception as e:
            print(f"⚠️ Failed to parse an event: {e}")
            continue

    return games
    
def format_bet_section(bet_type, pick, odds, ev, imp, model_prob, edge, vig):
    emoji = "🔥" if ev > 0 else "⚠️"
    return f"""📊 {bet_type.upper()} BET
{emoji} Pick: {pick}
💵 Odds: {odds}
📈 EV: {ev:+.1f}% 💎🟢 BEST VALUE
🧮 Implied Prob: {imp:.1%}
🧠 Model Prob: {model_prob:.1%}
🔍 Edge: {edge:+.1f}%
⚖️ Vig: {vig:.2%}
⚾ ——————"""

def send_alert(game):
    home = game["home_team"]
    away = game["away_team"]
    start_time = game.get("start_time_cdt") or game.get("start_time") or datetime.now()

    ml_data = game.get("moneyline") or {}
    spread_data = game.get("spread") or {}
    total_data = game.get("total") or {}

    msg = f"""🏟️ {home} vs {away}
📅 {start_time.strftime('%b %d, %I:%M %p CDT')}
🏆 ML: {home}: {ml_data.get(home, {}).get('odds', 'N/A')} | {away}: {ml_data.get(away, {}).get('odds', 'N/A')}
📏 Spread: {spread_data.get('label', 'N/A')} @ {spread_data.get('odds', 'N/A')}
📊 Total: {total_data.get('label', 'N/A')} — {total_data.get('side', 'N/A')} @ {total_data.get('odds', 'N/A')}

━━━━━━━━━━━━━━━━━━"""

    if ml_data.get("best_value"):
        msg += format_bet_section("MONEYLINE BET", ml_data["best_value"])
    if spread_data.get("best_value"):
        msg += format_bet_section("SPREAD BET", spread_data["best_value"])
    if total_data.get("best_value"):
        msg += format_bet_section("TOTALS BET", total_data["best_value"])

    send_telegram_message(msg)
    
# MAIN RUN
if __name__ == "__main__":
    games = fetch_bovada_mlb_odds()
    for game in games:
        send_alert(game)
