import requests
from datetime import datetime, timedelta
import pytz
import telegram
import json
import os

# === API KEYS (paste yours) ===
ODDS_API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0G-BLTAplBKVHt8YL6m0jNZpmUbCu4szH"

# === Telegram Setup ===
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# === Config ===
BOOKMAKERS = ["pinnacle", "betonlineag"]
SPORTS = ["baseball_mlb", "basketball_wnba"]
RESULTS_FILE = "results.json"
TIMEZONE = pytz.timezone('US/Central')

# === UTC/CT Helpers ===
def central_time(iso):
    return datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone(TIMEZONE)

def is_within_next_2_days(iso):
    dt = central_time(iso)
    now = datetime.now(TIMEZONE)
    return 0 <= (dt.date() - now.date()).days <= 1

# === Team ID Mappings ===
# Fetches once at start; maps team names to IDs for validation and future use
def get_active_names(sport_key):
    resp = requests.get(f"https://api.the-odds-api.com/v4/sports/{sport_key}/events",
                        params={"apiKey": ODDS_API_KEY})
    resp.raise_for_status()
    names = set()
    for e in resp.json():
        names.add(e["home_team"])
        names.add(e["away_team"])
    return names

def get_soccer_team_ids():
    ids = {}
    page = 1
    while True:
        r = requests.get(
            "https://api.sportmonks.com/v3/football/teams",
            params={"api_token": SPORTMONKS_API_KEY, "page": page, "per_page": 50}
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        if not data:
            break
        for t in data:
            ids[t["name"]] = t["id"]
        page += 1
    return ids

MLB_TEAMS = get_active_names("baseball_mlb")
WNBA_TEAMS = get_active_names("basketball_wnba")
SOCCER_TEAMS = get_soccer_team_ids()
print(f"Mapped {len(MLB_TEAMS)} MLB teams, {len(WNBA_TEAMS)} WNBA teams, {len(SOCCER_TEAMS)} soccer clubs")

# === EV & Message Formatting Helpers ===
def calculate_ev(odds, win_prob=0.5):
    dec = 1 + (odds/100) if odds > 0 else 1 + (100/abs(odds))
    return (dec * win_prob - 1) * 100

def format_ev_label(ev):
    if ev > 7:
        return "🟢 *BEST VALUE*"
    if ev > 3:
        return "🟡 *GOOD VALUE*"
    if ev > 0:
        return "🟠 *SLIGHT EDGE*"
    return "🔴 *NO EDGE*"

def generate_reasoning(market, team):
    if market == "h2h":
        return f"{team} are riding momentum 🚀 and metrics favor them."
    if market == "spreads":
        return f"{team} covers spreads consistently 🧱 with strong performance."
    if market == "totals":
        return f"Scoring tempo supports this totals play 📈"
    return "Value play based on matchup trends."

def send_telegram_message(text):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode=telegram.ParseMode.MARKDOWN)

def save_result(entry):
    data = json.load(open(RESULTS_FILE)) if os.path.exists(RESULTS_FILE) else []
    data.append(entry)
    json.dump(data, open(RESULTS_FILE, "w"), indent=2)

# === OddsAPI Fetch & Soccer Fetch ===
def fetch_odds(sport_key):
    resp = requests.get(f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds", params={
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "bookmakers": ",".join(BOOKMAKERS)
    })
    resp.raise_for_status()
    return resp.json()

def fetch_soccer_fixtures():
    start = datetime.now(TIMEZONE).strftime("%Y-%m-%d")
    end = (datetime.now(TIMEZONE) + timedelta(days=1)).strftime("%Y-%m-%d")
    resp = requests.get(
        f"https://api.sportmonks.com/v3/football/fixtures/between/{start}/{end}",
        params={"api_token": SPORTMONKS_API_KEY}
    )
    resp.raise_for_status()
    return resp.json().get("data", [])

# === Unified Game Processing ===
def process_game(sport, game, is_soccer=False):
    iso = game.get("commence_time") or game["time"]["starting_at"]["date_time_utc"]
    if not is_within_next_2_days(iso):
        return

    if is_soccer:
        home = game["localteam"]["data"]["name"]
        away = game["visitorteam"]["data"]["name"]
        if home not in SOCCER_TEAMS and away not in SOCCER_TEAMS:
            return
        outcomes = game.get("odds", {}).get("data", [])
        team_header = f"{away} vs {home}"
    else:
        home = game["home_team"]
        away = game["away_team"]
        if sport == "baseball_mlb" and home not in MLB_TEAMS and away not in MLB_TEAMS:
            return
        if sport == "basketball_wnba" and home not in WNBA_TEAMS and away not in WNBA_TEAMS:
            return
        outcome_set = game["bookmakers"][0]["markets"][0]
        outcomes = outcome_set["outcomes"]
        team_header = f"{away} vs {home}"

    market_key = outcome_set["key"] if not is_soccer else "h2h"
    best = max(outcomes, key=lambda o: calculate_ev(o["price"]))
    ev = calculate_ev(best["price"])
    if 3 <= ev <= 15:
        line_info = f" {best.get('point', ''):+.1f}" if market_key in ("spreads", "totals") else ""
        dt = central_time(iso).strftime("%b %d, %I:%M %p CT")
        msg = (
            f"📊 *{team_header}* — *{market_key.upper()} BET*\n"
            f"🔥 *Pick:* **{best['name']}{line_info}** @ {best['price']:+}\n"
            f"📈 EV: **+{ev:.1f}%** {format_ev_label(ev)}\n"
            f"🕒 *Game Time:* {dt}\n"
            f"💡 {generate_reasoning(market_key, best['name'])}\n"
            "——————"
        )
        send_telegram_message(msg)
        save_result({
            "sport": "soccer" if is_soccer else sport,
            "market": market_key,
            "pick": best["name"],
            "home": home,
            "away": away,
            "line": best.get("point", 0),
            "game_time": iso,
            "resolved": False
        })

# === Main & Result Checker ===
def check_results():
    entries = json.load(open(RESULTS_FILE, "r")) if os.path.exists(RESULTS_FILE) else []
    now = datetime.utcnow()
    for e in entries:
        if e.get("resolved"):
            continue
        start = datetime.fromisoformat(e["game_time"])
        if now - start < timedelta(hours=12):
            continue
        try:
            resp = requests.get(
                f"https://api.the-odds-api.com/v4/sports/{e['sport']}/scores",
                params={"apiKey": ODDS_API_KEY, "daysFrom": 2}
            )
            resp.raise_for_status()
            for g in resp.json():
                if g["home_team"] == e["home"] and g["away_team"] == e["away"]:
                    hs = g["scores"]["home_score"]
                    as_ = g["scores"]["away_score"]
                    res = ("won" if ((e["market"]=="h2h" and
                                     ((e["pick"]==e["home"] and hs>as_) or
                                      (e["pick"]==e["away"] and as_>hs))) else "lost")
                    e["result"] = res
                    e["resolved"] = True
                    print(f"✅ Logged {res} for {e['pick']}")
                    break
        except:
            continue
    json.dump(entries, open(RESULTS_FILE, "w"), indent=2)

def main():
    for sp in SPORTS:
        for g in fetch_odds(sp):
            process_game(sp, g)
    for g in fetch_soccer_fixtures():
        process_game("soccer", g, is_soccer=True)
    check_results()
    print("✅ Cycle complete.")

if __name__ == "__main__":
    main()
