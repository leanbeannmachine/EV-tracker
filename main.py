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
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds" \
          f"?regions=us&markets=h2h,spreads,totals&oddsFormat=american&apiKey={ODDS_API_KEY}"
    resp = requests.get(url, timeout=15)
    print("Status:", resp.status_code, "Remaining:", resp.headers.get('x-requests-remaining'))
    print("Sample data:", resp.text[:500])
    data = resp.json()
    print("Game count:", len(data))
    for g in data:
        print(g['home_team'], "vs", g['away_team'], ":", [b['key'] for b in g['bookmakers']])
    return data

# 🧠 Parse and send alerts
def process_and_alert(games):
    for game in games:
        home = game["home_team"]
        away = game["away_team"]
        start = datetime.fromisoformat(game["commence_time"]).astimezone(CDT)

        model_probs = get_model_probabilities(home, away)

        ml_data, spread_data, total_data = {}, {}, {}

        # Get only MyBookie data
        book = next((b for b in game['bookmakers'] if b['key'] == BOOKMAKER), None)
        if not book:
            continue

        for market in book["markets"]:
            if market["key"] == "h2h":
                if len(market["outcomes"]) == 2:
                    o1, o2 = market["outcomes"]
                    odds1, odds2 = int(o1["price"]), int(o2["price"])
                    p1, p2 = implied_prob(odds1), implied_prob(odds2)
                    vig = calc_vig(p1, p2)
                    ev1 = expected_value(model_probs["moneyline"].get(o1["name"], 0), odds1)
                    ev2 = expected_value(model_probs["moneyline"].get(o2["name"], 0), odds2)
                    best = (o1["name"], odds1, ev1, p1, model_probs["moneyline"].get(o1["name"], 0)) if ev1 > ev2 else (o2["name"], odds2, ev2, p2, model_probs["moneyline"].get(o2["name"], 0))
                    ml_data = {
                        "best_value": (*best, best[4] - best[3], vig)
                    }

            if market["key"] == "spreads":
                best_spread = None
                for o in market["outcomes"]:
                    odds = int(o["price"])
                    p = implied_prob(odds)
                    model = model_probs["spread"].get(o["name"], 0)
                    ev = expected_value(model, odds)
                    edge = model - p
                    vig = calc_vig(p, 1 - p)
                    if not best_spread or ev > best_spread[2]:
                        best_spread = (o["name"], o["point"], odds, ev, p, model, edge, vig)
                if best_spread:
                    spread_data["best_value"] = (f"{best_spread[0]} {best_spread[1]}", best_spread[2], best_spread[3], best_spread[4], best_spread[5], best_spread[6], best_spread[7])

            if market["key"] == "totals":
                best_total = None
                for o in market["outcomes"]:
                    odds = int(o["price"])
                    p = implied_prob(odds)
                    model = model_probs["total"].get(o["name"], 0)
                    ev = expected_value(model, odds)
                    edge = model - p
                    vig = calc_vig(p, 1 - p)
                    if not best_total or ev > best_total[2]:
                        best_total = (o["name"], o["point"], odds, ev, p, model, edge, vig)
                if best_total:
                    total_data["best_value"] = (f"{best_total[0]} {best_total[1]}", best_total[2], best_total[3], best_total[4], best_total[5], best_total[6], best_total[7])

        msg = f"""🏟️ {away} vs {home}
📅 {start.strftime('%b %d, %I:%M %p CDT')}
━━━━━━━━━━━━━━━━━━"""
        if "best_value" in ml_data:
            msg += format_bet_section("moneyline", *ml_data["best_value"])
        if "best_value" in spread_data:
            msg += format_bet_section("spread", *spread_data["best_value"])
        if "best_value" in total_data:
            msg += format_bet_section("total", *total_data["best_value"])

        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

# 🔁 Run
if __name__ == "__main__":
    games = fetch_oddsapi_mlb_odds()
    if not games:
        print("🔕 No MLB games found.")
    else:
        process_and_alert(games)
