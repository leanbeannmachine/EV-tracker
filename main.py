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

import requests
from datetime import datetime
import pytz

import requests
import json

SCRAPERAPI_KEY = "a4494e58bed5da50547d3abb23cf658b"  # Replace with your real key

def fetch_bovada_mlb_odds():
    print("📡 Fetching MLB odds using ScraperAPI...")

    bovada_url = "https://www.bovada.lv/services/sports/event/v2/en-us/featured/baseball/mlb"
    scraperapi_url = f"http://api.scraperapi.com?api_key={SCRAPERAPI_KEY}&url={bovada_url}"

    try:
        response = requests.get(scraperapi_url, timeout=15)
        response.raise_for_status()
        data = response.json()

        if not data or "events" not in data[0]:
            print("⚠️ Unexpected response structure:", data)
            return []

        print("✅ MLB odds fetched successfully.")
        return data[0]["events"]

    except requests.exceptions.RequestException as e:
        print(f"❌ ScraperAPI error: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        print("⚠️ Raw response:", response.text)
        return []

    games = []
    try:
        events = data[0]["events"]
        for event in events:
            teams = [c["name"] for c in event["competitors"]]
            home = [c["name"] for c in event["competitors"] if c["home"]][0]
            away = [c["name"] for c in event["competitors"] if not c["home"]][0]
            start_time_utc = datetime.fromtimestamp(event["startTime"] / 1000)
            start_time_cdt = start_time_utc.astimezone(pytz.timezone("America/Chicago")).strftime("%I:%M %p %Z")

            markets = event.get("displayGroups", [])[0].get("markets", [])
            moneyline, spread, total = None, None, None

            for market in markets:
                description = market.get("description", "").lower()
                if "moneyline" in description:
                    moneyline = market
                elif "spread" in description:
                    spread = market
                elif "total" in description:
                    total = market

            def extract_odds(market):
                if not market:
                    return {}
                outcomes = {}
                for outcome in market.get("outcomes", []):
                    team = outcome.get("description", "")
                    odds_str = outcome.get("price", {}).get("american", "")
                    if odds_str == "EVEN":
                        odds_str = "+100"
                    try:
                        odds = int(odds_str)
                    except ValueError:
                        odds = None
                    outcomes[team] = {
                        "odds": odds,
                        "raw": outcome.get("price", {})
                    }
                return outcomes

            games.append({
                "home_team": home,
                "away_team": away,
                "start_time_cdt": start_time_cdt,
                "moneyline": extract_odds(moneyline),
                "spread": extract_odds(spread),
                "total": extract_odds(total),
            })

    except Exception as e:
        print(f"❌ Error while parsing event data: {e}")

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
    if not games:
        print("🔕 No MLB odds fetched. Exiting.")
    else:
        for game in games:
            send_alert(game)
