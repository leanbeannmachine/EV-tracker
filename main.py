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

def fetch_bovada_mlb_odds():
    import time  # Make sure this is imported at the top

    url = "https://www.bovada.lv/services/sports/event/v2/events/A/description/baseball/mlb"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
    }

    for _ in range(3):  # retry up to 3 times
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.ok and res.text.strip():
                data = res.json()[0]["events"]
                break
        except Exception as e:
            print(f"Retrying... Error: {e}")
            time.sleep(1)
    else:
        print("Failed to fetch odds after 3 attempts.")
        return []

    games = []

    for game in data:
        teams = game["competitors"]
        home = next(t for t in teams if t["home"])
        away = next(t for t in teams if not t["home"])
        start_time_utc = datetime.fromtimestamp(game["startTime"] / 1000, tz=timezone.utc)
        start_time_cdt = start_time_utc.astimezone(CDT)

        display_groups = game.get("displayGroups", [])
        moneyline = spread = total = None

        for group in display_groups:
            for market in group.get("markets", []):
                desc = market.get("description", "").lower()
                if "moneyline" in desc:
                    moneyline = market.get("outcomes", [])
                elif "run line" in desc:
                    spread = market.get("outcomes", [])
                elif "total" in desc:
                    total = market.get("outcomes", [])

        def extract_odds(outcomes):
            if not outcomes:
                return None
            result = {}
            for outcome in outcomes:
                desc = outcome.get("description")
                odds = outcome.get("price", {}).get("american")
                line = outcome.get("price", {}).get("handicap")
                if desc and odds is not None:
                    result[desc] = {
                        "odds": 100 if odds == "EVEN" else int(odds),
                        "line": float(line) if line is not None else None
                    }
            return result

        games.append({
            "home_team": home["name"],
            "away_team": away["name"],
            "start_time": start_time_cdt.strftime("%b %d, %I:%M %p CDT"),
            "moneyline": extract_odds(moneyline),
            "spread": extract_odds(spread),
            "total": extract_odds(total),
        })

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
    start_time = game["start_time_cdt"]

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
