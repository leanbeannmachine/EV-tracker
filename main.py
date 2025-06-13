import requests
from datetime import datetime
import pytz
import telegram
import math
import json

# 📍 Configuration
CDT = pytz.timezone("America/Chicago")
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
SCRAPERAPI_KEY = "a4494e58bed5da50547d3abb23cf658b"  # Replace with yours if needed

bot = telegram.Bot(token=TELEGRAM_TOKEN)

# 📈 Probability logic (placeholder model)
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

def fetch_bovada_mlb_odds():
    print("📡 Fetching MLB odds using ScraperAPI...")

    bovada_url = "https://www.bovada.lv/services/sports/event/v2/en-us/league/baseball/mlb"
    scraperapi_url = (
        f"http://api.scraperapi.com/?api_key={SCRAPERAPI_KEY}"
        f"&url={bovada_url}"
        f"&render=true&premium=true"
    )

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

def extract_game_data(event):
    try:
        home_team = event["competitions"][0]["competitors"][0]["name"]
        away_team = event["competitions"][0]["competitors"][1]["name"]
        start_time = datetime.fromisoformat(event["startTime"].replace("Z", "+00:00")).astimezone(CDT)

        display_groups = event["displayGroups"]
        ml_data, spread_data, total_data = {}, {}, {}

        for group in display_groups:
            for market in group.get("markets", []):
                desc = market.get("description", "").lower()
                outcomes = market.get("outcomes", [])
                if desc == "moneyline" and len(outcomes) == 2:
                    odds1 = int(outcomes[0]["price"]["american"])
                    odds2 = int(outcomes[1]["price"]["american"])
                    team1 = outcomes[0]["description"]
                    team2 = outcomes[1]["description"]
                    p1 = implied_prob(odds1)
                    p2 = implied_prob(odds2)
                    vig = calc_vig(p1, p2)
                    model_probs = get_model_probabilities(team1, team2)["moneyline"]
                    ev1 = expected_value(model_probs[team1], odds1)
                    ev2 = expected_value(model_probs[team2], odds2)
                    best = (team1, odds1, model_probs[team1], p1, ev1) if ev1 > ev2 else (team2, odds2, model_probs[team2], p2, ev2)
                    ml_data = {
                        team1: {"odds": odds1},
                        team2: {"odds": odds2},
                        "best_value": (best[0], best[1], best[4], best[3], best[2], best[2] - best[3], vig)
                    }

                if "spread" in desc and len(outcomes) == 2:
                    for out in outcomes:
                        team = out["description"]
                        odds = int(out["price"]["american"])
                        spread = out.get("price", {}).get("handicap", 0)
                        p = implied_prob(odds)
                        model = get_model_probabilities(home_team, away_team)["spread"][team]
                        ev = expected_value(model, odds)
                        edge = model - p
                        spread_data.setdefault("candidates", []).append((team, spread, odds, ev, p, model, edge))

                if "total" in desc and len(outcomes) == 2:
                    for out in outcomes:
                        side = out["description"]
                        odds = int(out["price"]["american"])
                        label = out.get("price", {}).get("handicap", 0)
                        p = implied_prob(odds)
                        model = get_model_probabilities(home_team, away_team)["total"][side]
                        ev = expected_value(model, odds)
                        edge = model - p
                        total_data.setdefault("candidates", []).append((side, label, odds, ev, p, model, edge))

        # Pick best values
        if "candidates" in spread_data:
            best_spread = max(spread_data["candidates"], key=lambda x: x[3])
            spread_data = {
                "label": best_spread[1],
                "odds": best_spread[2],
                "best_value": (best_spread[0], best_spread[2], best_spread[3], best_spread[4], best_spread[5], best_spread[6], calc_vig(*[implied_prob(best_spread[2]), 1 - implied_prob(best_spread[2])]))
            }

        if "candidates" in total_data:
            best_total = max(total_data["candidates"], key=lambda x: x[3])
            total_data = {
                "label": best_total[1],
                "side": best_total[0],
                "odds": best_total[2],
                "best_value": (best_total[0], best_total[2], best_total[3], best_total[4], best_total[5], best_total[6], calc_vig(*[implied_prob(best_total[2]), 1 - implied_prob(best_total[2])]))
            }

        return {
            "home_team": home_team,
            "away_team": away_team,
            "start_time": start_time,
            "moneyline": ml_data,
            "spread": spread_data,
            "total": total_data
        }
    except Exception as e:
        print(f"⚠️ Error parsing event: {e}")
        return None

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

def send_alert(game):
    home = game["home_team"]
    away = game["away_team"]
    start_time = game["start_time"]

    ml_data = game.get("moneyline", {})
    spread_data = game.get("spread", {})
    total_data = game.get("total", {})

    msg = f"""🏟️ {home} vs {away}
📅 {start_time.strftime('%b %d, %I:%M %p CDT')}
━━━━━━━━━━━━━━━━━━"""

    if "best_value" in ml_data:
        msg += format_bet_section("moneyline", *ml_data["best_value"])
    if "best_value" in spread_data:
        msg += format_bet_section("spread", *spread_data["best_value"])
    if "best_value" in total_data:
        msg += format_bet_section("total", *total_data["best_value"])

    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

# 🚀 MAIN
if __name__ == "__main__":
    events = fetch_bovada_mlb_odds()
    if not events:
        print("🔕 No MLB odds fetched. Exiting.")
    else:
        for event in events:
            game = extract_game_data(event)
            if game:
                send_alert(game)
