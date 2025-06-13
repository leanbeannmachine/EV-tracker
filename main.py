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

import requests
from datetime import datetime
import pytz

def fetch_bovada_mlb_odds():
    url = "https://www.bovada.lv/services/sports/event/v2/us/en/baseball/mlb"
    
    # 🛡️ Free Proxy Config
    proxies = {
        "http": "http://208.102.24.225:80",
        "https": "http://208.102.24.225:80"
    }

    try:
        response = requests.get(url, proxies=proxies, timeout=10)
    except requests.RequestException as e:
        print(f"❌ Proxy connection error: {e}")
        return []

    if response.status_code != 200 or not response.text.strip():
        print(f"❌ Failed to fetch odds — status {response.status_code}")
        print("⚠️ Response:", response.text[:200])
        return []

    games = []

    for game in data:
        teams = game["competitors"]
        home = next(t["name"] for t in teams if t["home"])
        away = next(t["name"] for t in teams if not t["home"])

        try:
            start_time_utc = datetime.fromisoformat(game["startTime"].replace("Z", "+00:00"))
        except:
            start_time_utc = datetime.utcfromtimestamp(int(game["startTime"]) / 1000)

        cdt = pytz.timezone("America/Chicago")
        start_time_cdt = start_time_utc.astimezone(cdt).strftime("%I:%M %p %Z")

        markets = game["displayGroups"]
        moneyline, spread, total = None, None, None

        for market in markets:
            for market_item in market.get("markets", []):
                desc = market_item.get("description", "").lower()

                if "moneyline" in desc:
                    moneyline = market_item.get("outcomes", [])
                elif "spread" in desc:
                    spread = market_item.get("outcomes", [])
                elif "total" in desc:
                    total = market_item.get("outcomes", [])

        def extract_odds(outcomes):
            odds_dict = {}
            for o in outcomes:
                team = o.get("description")
                odds = o.get("price", {}).get("american")
                try:
                    odds = 100 if odds == "EVEN" else int(odds)
                except:
                    odds = None
                odds_dict[team] = {
                    "odds": odds,
                    "raw": o
                }
            return odds_dict

        game_data = {
            "home": home,
            "away": away,
            "start_time_cdt": start_time_cdt,
            "moneyline": extract_odds(moneyline or []),
            "spread": extract_odds(spread or []),
            "total": extract_odds(total or [])
        }

        games.append(game_data)

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
