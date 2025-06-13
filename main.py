import requests
from datetime import datetime
import pytz
import telegram
import math
import os

# 📍 Config
CDT = pytz.timezone("America/Chicago")
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
API_KEY = "25af17e62a8d221b05b9b5c5a4911cdb"
SPORT = "baseball_mlb"
REGIONS = "us"
MARKETS = "h2h,spreads,totals"
BOOKMAKER = "draftkings"

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
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey={API_KEY}&regions=us&markets=h2h,spreads,totals&bookmakers=draftkings"

    response = requests.get(url)
    print("Status:", response.status_code, "Remaining:", response.headers.get('x-requests-remaining'))

    if response.status_code != 200:
        raise Exception("Failed to fetch odds: " + response.text)

    games = response.json()
    print("Game count:", len(games))

    if games:
        print("Sample data:", games[0])

    return games

def send_alert(home_team, away_team, start_time, moneyline_odds, spread_odds, total_odds):
    model_probs = get_model_probabilities(home_team, away_team)

    # 💰 MONEYLINE
    best_ml = max(moneyline_odds.items(), key=lambda x: expected_value(model_probs["moneyline"].get(x[0], 0), x[1]))
    ml_team, ml_odds_val = best_ml
    ml_prob = implied_prob(ml_odds_val)
    ml_ev = expected_value(model_probs["moneyline"].get(ml_team, 0), ml_odds_val)
    ml_edge = (model_probs["moneyline"].get(ml_team, 0) - ml_prob) * 100
    ml_vig = calc_vig(implied_prob(moneyline_odds[home_team]), implied_prob(moneyline_odds[away_team]))

    # 🧱 SPREAD
    best_spread = max(spread_odds, key=lambda o: expected_value(model_probs["spread"].get(o["name"], 0), o["price"]))
    sp_team = best_spread["name"]
    sp_odds = best_spread["price"]
    sp_prob = implied_prob(sp_odds)
    sp_ev = expected_value(model_probs["spread"].get(sp_team, 0), sp_odds)
    sp_edge = (model_probs["spread"].get(sp_team, 0) - sp_prob) * 100
    sp_vig = calc_vig(*[implied_prob(o["price"]) for o in spread_odds[:2]])

    # 🔥 TOTAL
    best_total = max(total_odds, key=lambda o: expected_value(model_probs["total"].get(o["name"], 0), o["price"]))
    to_side = best_total["name"]
    to_odds = best_total["price"]
    to_prob = implied_prob(to_odds)
    to_ev = expected_value(model_probs["total"].get(to_side, 0), to_odds)
    to_edge = (model_probs["total"].get(to_side, 0) - to_prob) * 100
    to_vig = calc_vig(*[implied_prob(o["price"]) for o in total_odds[:2]])

    # 🕒 Game time
    time_str = start_time.strftime("%I:%M %p %Z")

    # 📝 Build message
    msg = f"""⚾ {away_team} @ {home_team}
🕒 {time_str} CDT

{format_bet_section("Moneyline", ml_team, ml_odds_val, ml_ev, ml_prob, model_probs["moneyline"].get(ml_team, 0), ml_edge, ml_vig)}
{format_bet_section("Spread", f"{best_spread['name']} {best_spread['point']:+}", sp_odds, sp_ev, sp_prob, model_probs["spread"].get(sp_team, 0), sp_edge, sp_vig)}
{format_bet_section("Total", f"{to_side} {best_total['point']}", to_odds, to_ev, to_prob, model_probs["total"].get(to_side, 0), to_edge, to_vig)}
"""
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
    print(f"✅ Alert sent for {away_team} @ {home_team}")

# 🧠 Parse and send alerts
def process_and_alert(games):
    for game in games:
        try:
            start = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).astimezone(CDT)
            home = game["home_team"]
            away = game["away_team"]

            draftkings = next((b for b in game["bookmakers"] if b["key"] == "draftkings"), None)
            if not draftkings:
                print(f"❌ DraftKings odds not available for {away} vs {home}")
                continue

            markets = {m["key"]: m for m in draftkings["markets"]}
            h2h = markets.get("h2h", {}).get("outcomes", [])
            spreads = markets.get("spreads", {}).get("outcomes", [])
            totals = markets.get("totals", {}).get("outcomes", [])

            if not (h2h and spreads and totals):
                print(f"⚠️ Incomplete odds for {away} vs {home}")
                continue

            ml_odds = {o["name"]: o["price"] for o in h2h}
            spread_odds = spreads
            total_odds = totals

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
