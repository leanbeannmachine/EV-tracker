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

def fetch_bovada_mlb_odds():
    url = "https://www.bovada.lv/services/sports/event/v2/en-us/featured/baseball/mlb"
    response = requests.get(url)
    data = response.json()[0]["events"]

    central = pytz.timezone("America/Chicago")
    games = []

    for game in data:
        try:
            home = game["competitors"][0] if game["competitors"][0]["home"] else game["competitors"][1]
            away = game["competitors"][1] if game["competitors"][0]["home"] else game["competitors"][0]
            home_team = home["name"]
            away_team = away["name"]

            start_time_utc = datetime.fromtimestamp(game["startTime"] / 1000, tz=timezone.utc)
            start_time_cdt = start_time_utc.astimezone(central)

            display_markets = game.get("displayGroups", [])[0].get("markets", [])
            moneyline, spread, total = None, None, None

            for market in display_markets:
                desc = market.get("description", "").lower()
                if "moneyline" in desc:
                    moneyline = market
                elif "spread" in desc:
                    spread = market
                elif "total" in desc:
                    total = market

            def extract_odds(market):
                if not market:
                    return None

                odds_data = {}
                for outcome in market["outcomes"]:
                    team = outcome["description"]
                    odds = outcome["price"].get("american")

                    # Handle "EVEN" odds
                    if odds == "EVEN":
                        odds = +100

                    try:
                        odds = int(odds)
                    except:
                        continue

                    odds_data[team] = {
                        "odds": odds,
                        "implied_prob": round(100 / (abs(odds) + 100) * (100 if odds > 0 else abs(odds)), 1),
                        # Placeholder values below for now — your model will update them
                        "model_prob": 55.0,
                        "ev_percent": 10.0,
                        "edge_percent": 5.0,
                        "vig_percent": 5.0,
                        "pick": team,
                        "is_best": False
                    }

                return odds_data

            def extract_spread_or_total(market, type_):
                if not market:
                    return None
                outcome = market["outcomes"][0]
                odds = outcome["price"].get("american")
                if odds == "EVEN":
                    odds = +100
                try:
                    odds = int(odds)
                except:
                    odds = None
                return {
                    "label": outcome.get("handicap") if type_ == "spread" else market["outcomes"][0].get("description"),
                    "side": outcome.get("description"),
                    "odds": odds,
                    "implied_prob": round(100 / (abs(odds) + 100) * (100 if odds > 0 else abs(odds)), 1) if odds else None,
                    "model_prob": 58.0,
                    "ev_percent": 10.0,
                    "edge_percent": 7.0,
                    "vig_percent": 6.0,
                    "pick": outcome.get("description"),
                    "is_best": False
                }

            moneyline_data = extract_odds(moneyline)
            spread_data = extract_spread_or_total(spread, "spread")
            total_data = extract_spread_or_total(total, "total")

            # Pick best value bet per category
            best_ml = None
            if moneyline_data:
                best_ml = max(moneyline_data.values(), key=lambda x: x["ev_percent"], default=None)
                best_ml["is_best"] = True

            best_spread = spread_data
            best_total = total_data

            games.append({
                "home_team": home_team,
                "away_team": away_team,
                "start_time": start_time_utc,
                "start_time_cdt": start_time_cdt,
                "moneyline": {
                    **moneyline_data,
                    "best_value": best_ml
                } if moneyline_data else None,
                "spread": {
                    **spread_data,
                    "best_value": best_spread
                } if spread_data else None,
                "total": {
                    **total_data,
                    "best_value": best_total
                } if total_data else None,
            })
        except Exception as e:
            print(f"Failed to parse game: {e}")
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
