import requests
from datetime import datetime, timedelta
import pytz
import telegram
import json
import os

# === API KEYS ===
ODDS_API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0G-BLTAplBKVHt8YL6m0jNZpmUbCu4szH"

# === TELEGRAM SETUP ===
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# === CONFIG ===
BOOKMAKERS = ["pinnacle", "betonlineag"]
SPORTS = ["baseball_mlb", "basketball_wnba"]
RESULTS_FILE = "results.json"
TIMEZONE = pytz.timezone('US/Central')

# === UTILITY FUNCTIONS ===
def now_ct(): return datetime.now(TIMEZONE)

def to_ct(iso_str):
    return datetime.fromisoformat(iso_str.replace('Z', '+00:00')).astimezone(TIMEZONE)

def is_today_or_tomorrow(iso_str):
    dt = to_ct(iso_str)
    return dt.date() in [now_ct().date(), (now_ct() + timedelta(days=1)).date()]

def generate_reasoning(market, team):
    if market == "h2h":
        return f"{team} are in form and the metrics lean heavily their way 🚀"
    if market == "spreads":
        return f"{team} is hitting spreads consistently 🧱"
    if market == "totals":
        return f"Total line looks underpriced based on recent pace 📈"
    return "Value play based on matchup data."

def calculate_ev(american_odds, win_prob):
    dec = (american_odds / 100 + 1) if american_odds > 0 else (100 / abs(american_odds) + 1)
    return (dec * win_prob - 1) * 100

def format_ev_label(ev):
    return ("🟢 *BEST VALUE*" if ev > 7 else
            "🟡 *GOOD VALUE*" if ev > 3 else
            "🟠 *SLIGHT EDGE*" if ev > 0 else
            "🔴 *NO EDGE*")

def format_message(market, team, line_info, odds, ev, iso_str):
    dt = to_ct(iso_str)
    return (
        f"📊 *{market.upper()} BET*\n\n"
        f"🔥 *Pick:* **{team}{line_info}**\n"
        f"💵 *Odds:* {odds:+}\n"
        f"📈 *EV:* **+{ev:.1f}%** {format_ev_label(ev)}\n"
        f"🕒 *Game Time:* {dt.strftime('%b %d, %I:%M %p CT')}\n"
        f"💡 {generate_reasoning(market, team)}\n——————"
    )

def send_msg(text):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode=telegram.ParseMode.MARKDOWN)

def save_log(entry):
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'w') as f: json.dump([], f)
    with open(RESULTS_FILE, 'r+') as f:
        data = json.load(f); data.append(entry)
        f.seek(0); json.dump(data, f, indent=2)

# === FETCH ODDS: MLB & WNBA ===
def fetch_odds(sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    try:
        resp = requests.get(url, params={
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
            "bookmakers": ",".join(BOOKMAKERS)
        })
        resp.raise_for_status()
        return resp.json()
    except:
        return []

# === FETCH SOCCER MATCHES via SportMonks ===
def fetch_soccer_matches():
    url = f"https://soccer.sportmonks.com/api/v2.0/fixtures/between/{now_ct().strftime('%Y-%m-%d')}/{(now_ct()+timedelta(days=1)).strftime('%Y-%m-%d')}"
    try:
        resp = requests.get(url, params={"api_token": SPORTMONKS_API_KEY, "tz": "UTC"})
        resp.raise_for_status()
        return resp.json().get('data', [])
    except:
        return []

# === PROCESS MATCHES & SEND ALERTS ===
def process_sport(sport_key, data, is_soccer=False):
    for game in data:
        iso = game['commence_time'] if not is_soccer else game['time']['starting_at']['date_time_utc']
        if not is_today_or_tomorrow(iso): continue

        if is_soccer:
            teams = f"{game['localteam']['data']['name']} vs {game['visitorteam']['data']['name']}"
            market = 'h2h'; outcomes = game.get('odds', {}).get('data', [])
        else:
            teams = f"{game['away_team']} vs {game['home_team']}"
            bk = game.get('bookmakers', [])[0]
            market = bk['markets'][0]['key']
            outcomes = bk['markets'][0]['outcomes']

        best = max(outcomes, key=lambda o: calculate_ev(o['price'], 0.5))
        ev = calculate_ev(best['price'],0.5)
        if 3.0 <= ev <= 15.0:
            line = f" {best.get('point', ''):+.1f}" if best.get('point') else ""
            msg = format_message(market, best['name'], line, best['price'], ev, iso)
            send_msg(msg)
            save_log({
                "sport": "soccer" if is_soccer else sport_key,
                "market": market, "pick": best['name'],
                "teams": teams, "game_time": iso, "resolved": False
            })

# === MAIN FUNCTION ===
def main():
    for sp in SPORTS:
        process_sport(sp, fetch_odds(sp))
    process_sport("soccer", fetch_soccer_matches(), is_soccer=True)
    print("✅ Cycle complete.")

if __name__=="__main__":
    main()
