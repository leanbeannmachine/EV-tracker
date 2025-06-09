import requests
from datetime import datetime, timedelta
import pytz
import telegram
import json
import os

# 🔑 API KEYS
ODDS_API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0G-BLTAplBKVHt8YL6m0jNZpmUbCu4szH"  # 👈 Plug in your valid key

# 📲 TELEGRAM
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

BOOKMAKERS = ["pinnacle", "betonlineag"]
SPORTS = ["baseball_mlb", "basketball_wnba"]
RESULTS_FILE = "results.json"

# 📌 DATE FILTERS
def is_valid_day(game_time_str):
    game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00')).astimezone(pytz.timezone('US/Central'))
    today = datetime.now(pytz.timezone('US/Central')).date()
    return game_time.date() in [today, today + timedelta(days=1)]

# 🧠 EV CALCULATION
def calculate_ev(american_odds, win_prob):
    decimal_odds = 1 + (american_odds / 100) if american_odds > 0 else 1 + (100 / abs(american_odds))
    return ((decimal_odds * win_prob) - 1) * 100

def format_ev_label(ev):
    if ev > 7:
        return "🟢 *BEST VALUE*"
    elif ev > 3:
        return "🟡 *GOOD VALUE*"
    elif ev > 0:
        return "🟠 *SLIGHT EDGE*"
    return "🔴 *NO EDGE*"

# 📣 MESSAGE GEN
def generate_reasoning(market, team):
    if market == "h2h":
        return f"The {team} come in hot 🚀 and the metrics favor them 📊. Great value for a team in form!"
    elif market == "spreads":
        return f"{team} has covered spreads reliably 🧱 with solid defense. A strong value spot!"
    elif market == "totals":
        return f"Tempo and trends support this line 📈. The matchup data aligns with value on this total."
    return "Data and trends suggest this is a smart value play."

def format_message(game, market, outcome, odds, ev, start_time):
    market_key = market.lower()
    team = outcome.get('name', '')
    line_info = ""

    if market_key == "spreads" and 'point' in outcome:
        line_info = f" {outcome['point']:+.1f}"
    elif market_key == "totals" and 'point' in outcome:
        line_info = f" {outcome['point']:.1f}"

    matchup = f"{game.get('away_team', '')} @ {game.get('home_team', '')}"
    team_line = f"{team}{line_info}"
    readable_time = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(pytz.timezone('US/Central')).strftime('%b %d, %I:%M %p CT')
    odds_str = f"{odds:+}" if isinstance(odds, int) else odds
    label = format_ev_label(ev)
    reasoning = generate_reasoning(market, team)

    return (
        f"📢 *{matchup}*\n"
        f"📊 *{market.upper()} BET*\n\n"
        f"🔥 *Pick:* **{team_line}**\n"
        f"💵 *Odds:* {odds_str}\n"
        f"📈 *Expected Value:* **+{ev:.1f}%**\n"
        f"{label}\n\n"
        f"🕒 *Game Time:* {readable_time}\n"
        f"💡 *Why We Like It:*\n{reasoning}\n"
        f"——————"
    )

def send_telegram_message(message):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
    except telegram.error.TelegramError as e:
        print(f"Telegram error: {e}")

# 📡 ODDS FETCHER
def fetch_odds_for_sport(sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "bookmakers": ",".join(BOOKMAKERS)
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching odds for {sport_key}: {e}")
        return []

# 📁 LOG RESULTS
def save_result_log(entry):
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'w') as f:
            json.dump([], f)

    with open(RESULTS_FILE, 'r+') as f:
        data = json.load(f)
        data.append(entry)
        f.seek(0)
        json.dump(data, f, indent=2)

# ✅ RESULTS CHECKER (optional completion)
def check_and_update_results():
    print("🔄 Checking for resolved bets...")
    now = datetime.utcnow()

    if not os.path.exists(RESULTS_FILE):
        return

    with open(RESULTS_FILE, "r+") as f:
        results = json.load(f)

    for e in results:
        if e.get("resolved"):
            continue
        start = datetime.fromisoformat(e["game_time"])
        if now - start >= timedelta(hours=12):
            try:
                url = f"https://api.the-odds-api.com/v4/sports/{e['sport']}/scores"
                params = {"apiKey": ODDS_API_KEY, "daysFrom": 2}
                r = requests.get(url, params=params)
                r.raise_for_status()
                for g in r.json():
                    if g.get("home_team") == e["home"] and g.get("away_team") == e["away"]:
                        hs = g.get("scores", {}).get("home_score", 0)
                        as_ = g.get("scores", {}).get("away_score", 0)
                        res = (
                            "won" if (
                                (e["market"] == "h2h" and ((e["pick"] == e["home"] and hs > as_) or (e["pick"] == e["away"] and as_ > hs)))
                            ) else "lost"
                        )
                        e["result"] = res
                        e["resolved"] = True
                        print(f"📌 Logged result for {e['pick']}: {res}")
                        break
            except Exception as err:
                print(f"❌ Score fetch failed: {err}")

    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

# 🚀 MAIN
def main():
    sent_any = False
    for sport in SPORTS:
        games = fetch_odds_for_sport(sport)
        for game in games:
            if not is_valid_day(game['commence_time']):
                continue
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    best_outcome = None
                    best_ev = -999
                    for outcome in market.get('outcomes', []):
                        odds = outcome.get('price')
                        if odds is None:
                            continue
                        ev = calculate_ev(odds, 0.5)  # ← use your model here
                        if ev > best_ev:
                            best_ev = ev
                            best_outcome = outcome
                    if best_outcome and 3 <= best_ev <= 15:
                        msg = format_message(game, market['key'], best_outcome, best_outcome['price'], best_ev, game['commence_time'])
                        send_telegram_message(msg)
                        sent_any = True
                        save_result_log({
                            "sport": sport,
                            "market": market['key'],
                            "pick": best_outcome.get("name", ""),
                            "home": game.get("home_team"),
                            "away": game.get("away_team"),
                            "line": best_outcome.get("point", 0),
                            "type": "over" if "over" in best_outcome.get("name", "").lower() else "under" if "under" in best_outcome.get("name", "").lower() else None,
                            "game_time": game['commence_time'],
                            "resolved": False
                        })
    if not sent_any:
        print("✅ Script ran but no EV bets found.")
    else:
        print("✅ Bets sent.")
    check_and_update_results()

if __name__ == "__main__":
    main()
