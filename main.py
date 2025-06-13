import requests
from datetime import datetime
import pytz
import telegram
import math

# 📍 Config
CDT = pytz.timezone("America/Chicago")
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
ODDS_API_KEY = "25af17e62a8d221b05b9b5c5a4911cdb"
SPORT = "baseball_mlb"
REGIONS = "us"
MARKETS = "h2h,spreads,totals"
BOOKMAKER = "mybookie"

bot = telegram.Bot(token=TELEGRAM_TOKEN)

# 🎯 Math Functions
def implied_prob(odds):
    return abs(odds) / (abs(odds) + 100) if odds > 0 else 100 / (abs(odds) + 100)

def calc_vig(p1, p2):
    return p1 + p2 - 1

def expected_value(prob, odds):
    return ((prob * (abs(odds) / 100)) - (1 - prob)) * 100 if odds > 0 else ((prob * 100 / abs(odds)) - (1 - prob)) * 100

def get_model_probabilities(team1, team2):
    return {
        "moneyline": {team1: 0.52, team2: 0.48},
        "spread": {team1: 0.53, team2: 0.47},
        "total": {"Over": 0.58, "Under": 0.42}
    }

# 🧽 Format Alert Section
def format_bet_section(bet_type, pick, odds, ev, imp, model_prob, edge, vig):
    emoji = "🔥" if ev > 0 else "⚠️"
    return f"""\n📊 {bet_type.upper()} BET
{emoji} Pick: {pick}
💵 Odds: {odds}
📈 EV: {ev:+.1f}% 💎🟢 BEST VALUE
🧮 Implied Prob: {imp:.1%}
🧠 Model Prob: {model_prob:.1%}
🔍 Edge: {edge:+.1f}%
⚖️ Vig: {vig:.2%}
⚾ ——————"""

# 🚀 Pull odds from OddsAPI
def fetch_oddsapi_mlb_odds():
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey={API_KEY}&regions=us&markets=h2h,spreads,totals&bookmakers=mybookieag"
    print("Status:", resp.status_code, "Remaining:", resp.headers.get('x-requests-remaining'))
    print("Sample data:", resp.text[:500])
    data = resp.json()
    print("Game count:", len(data))
    for g in data:
        print(g['home_team'], "vs", g['away_team'], ":", [b['key'] for b in g['bookmakers']])
    return data

# 🧠 Parse and send alerts
from datetime import datetime, timezone
import pytz

# Set your timezone for CDT
CDT = pytz.timezone("America/Chicago")

def process_and_alert(games):
    for game in games:
        try:
            # Fix ISO string with Z timezone by replacing with +00:00 for fromisoformat
            start = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).astimezone(CDT)
            home = game["home_team"]
            away = game["away_team"]

            # Find MyBookie bookmaker odds only
            mybookie = next((b for b in game["bookmakers"] if b["key"] == "mybookieag"), None)
            if not mybookie:
                print(f"❌ MyBookie odds not available for {away} vs {home}")
                continue

            # Create dictionary of markets for easy access
            markets = {m["key"]: m for m in mybookie["markets"]}

            h2h = markets.get("h2h", {}).get("outcomes", [])
            spreads = markets.get("spreads", {}).get("outcomes", [])
            totals = markets.get("totals", {}).get("outcomes", [])

            if not (h2h and spreads and totals):
                print(f"⚠️ Incomplete odds for {away} vs {home}")
                continue

            # Extract odds
            ml_odds = {o["name"]: o["price"] for o in h2h}
            spread_odds = spreads
            total_odds = totals

            # Call your alert logic here with those odds
            send_alert(
                home_team=home,
                away_team=away,
                start_time=start,
                moneyline_odds=ml_odds,
                spread_odds=spread_odds,
                total_odds=total_odds,
            )

        except Exception as e:
            print(f"Error processing game {away} vs {home}: {e}")
            
# 🔁 Run
if __name__ == "__main__":
    games = fetch_oddsapi_mlb_odds()
    if not games:
        print("🔕 No MLB games found.")
    else:
        process_and_alert(games)
