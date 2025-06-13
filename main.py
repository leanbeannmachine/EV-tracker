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
    url = "https://www.bovada.lv/services/sports/event/v2/en-us/featured/baseball/mlb"
    proxy_list = [
        "http://208.102.24.225:80",
        "http://138.201.125.229:8118",  # Germany
        "http://198.27.74.6:9300",     # USA
        "http://177.53.152.81:8080",   # Brazil
    ]

    for proxy_url in proxy_list:
        proxies = {"http": proxy_url, "https": proxy_url}
        try:
            response = requests.get(url, proxies=proxies, timeout=10)
        except requests.RequestException as e:
            print(f"⚠️ Proxy {proxy_url} connection error: {e}")
            continue

        if response.status_code != 200 or not response.text.strip():
            print(f"⚠️ Proxy {proxy_url} returned status {response.status_code}")
            continue

        try:
            raw = response.json()
            data = raw[0]["events"]
        except Exception as e:
            print(f"⚠️ Proxy {proxy_url} JSON parse error: {e}")
            continue

        # Success! Process data below...
        central = pytz.timezone("America/Chicago")
        games = []
        for g in data:
            try:
                home = next(team["name"] for team in g["competitors"] if team["home"])
                away = next(team["name"] for team in g["competitors"] if not team["home"])
                start_dt = datetime.fromtimestamp(g["startTime"]/1000, tz=central)
                start_cdt = start_dt.strftime("%b %d, %I:%M %p CDT")

                ml, sp, tot = None, None, None
                for grp in g.get("displayGroups", []):
                    for m in grp.get("markets", []):
                        desc = m.get("description", "").lower()
                        if "moneyline" in desc: ml = m.get("outcomes", [])
                        if "spread" in desc: sp = m.get("outcomes", [])
                        if "total" in desc: tot = m.get("outcomes", [])

                def ex(os):
                    out = {}
                    for o in os or []:
                        nm = o.get("description")
                        od = o.get("price", {}).get("american")
                        od = 100 if od == "EVEN" else int(od or 0)
                        out[nm] = {"odds": od, "raw": o}
                    return out

                games.append({
                    "home_team": home,
                    "away_team": away,
                    "start_time_cdt": start_cdt,
                    "moneyline": ex(ml),
                    "spread": ex(sp),
                    "total": ex(tot),
                })
            except Exception as e:
                print(f"⚠️ Event parse error: {e}")
                continue

        return games  # Exit once we get valid data

    # If we tried all proxies and none worked:
    print("❌ All proxies failed. No data fetched.")
    return []
    
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
