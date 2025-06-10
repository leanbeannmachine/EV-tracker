import os
import time
import requests
import pytz
from datetime import datetime
import telegram

# ── CONFIG ──
API_KEY           = "ff76b566ed33aae7bb6e5e98b58d5405"      # OddsAPI key
TELEGRAM_TOKEN    = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"  # Telegram bot token
TELEGRAM_CHAT_ID  = "964091254"    # Telegram chat ID
SPORT_KEY         = "baseball_mlb"                   # MLB only
BOOKMAKERS        = "fanduel,bovada"
MARKETS           = "h2h,spreads,totals"
REGION            = "us"
ODDS_FORMAT       = "american"
EV_THRESHOLD_GOOD = 5.0   # minimum EV% for GOOD VALUE
EV_THRESHOLD_BEST = 7.0   # minimum EV% for BEST VALUE
TIMEZONE          = pytz.timezone("America/New_York")

# ── HELPERS ──
def implied_prob(odds):
    odds = int(odds)
    if odds > 0:
        return 100 / (odds + 100)
    return -odds / (-odds + 100)

# ── MLB TEAM ID HELPER ──
def get_mlb_team_ids():
    import requests
    try:
        r = requests.get("https://statsapi.mlb.com/api/v1/teams?sportId=1")
        r.raise_for_status()
        data = r.json()
        return {team["name"]: team["id"] for team in data["teams"]}
    except Exception as e:
        print("MLB Team ID fetch error:", e)
        return {}

def ev_and_edge(model_prob, odds):
    imp = implied_prob(odds)
    edge = model_prob - imp
    ev = edge * 100
    return round(ev, 1), round(imp * 100, 1), round(edge * 100, 1)

def ev_label(ev):
    if ev >= EV_THRESHOLD_BEST:
        return "💎🟢 BEST VALUE"
    if ev >= EV_THRESHOLD_GOOD:
        return "🔝🟡 GOOD VALUE"
    return None

def fmt_time(iso):
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TIMEZONE)
    return dt.strftime("%b %d, %I:%M %p CDT")

def format_american(odds):
    odds = int(odds)
    return f"+{odds}" if odds > 0 else str(odds)

# ── FETCH ODDS ──
def fetch_odds():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": REGION,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
        "bookmakers": BOOKMAKERS
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()

# ── BUILD & SEND ALERT ──
def send_alert(game):
    home = game["home_team"]
    away = game["away_team"]
    when = fmt_time(game["commence_time"])

    # store odds for comparison
    ml_odds = {}
    spread_odds = {}
    total_odds = {}

    # collect best value per market
    best = {"h2h": None, "spreads": None, "totals": None}
    for bm in game["bookmakers"]:
        for m in bm["markets"]:
            key = m["key"]
            for out in m["outcomes"]:
                team = out["name"]
                odds = out["price"]
                point = out.get("point", "")

                # capture individual odds for home/away comparisons
                if key == "h2h":
                    ml_odds[team] = odds
                elif key == "spreads":
                    spread_odds[f"{team} {point}"] = odds
                elif key == "totals":
                    total_odds[f"{team} {point}"] = odds

                # placeholder model_prob
                model_prob = {"h2h":0.55, "spreads":0.53, "totals":0.58}[key]
                ev, imp, edge = ev_and_edge(model_prob, odds)
                label = ev_label(ev)
                if label and (best[key] is None or ev > best[key]["ev"]):
                    best[key] = {
                        "team": team,
                        "point": point,
                        "odds": odds,
                        "ev": ev,
                        "imp": imp,
                        "mod": round(model_prob*100,1),
                        "edge": edge,
                        "label": label
                    }

    # 💣 BLOCK: if moneyline odds for both teams are equal → skip!
    if "h2h" in best and len(set(ml_odds.values())) == 1:
        print(f"⚠️ Skipping {away} vs {home} — identical moneyline odds for both teams: {list(ml_odds.values())[0]}")
        return
    if "spreads" in best and len(set(spread_odds.values())) == 1:
        print(f"⚠️ Skipping {away} vs {home} — identical spread odds: {list(spread_odds.values())[0]}")
        return
    if "totals" in best and len(set(total_odds.values())) == 1:
        print(f"⚠️ Skipping {away} vs {home} — identical total odds: {list(total_odds.values())[0]}")
        return

    # if none qualifies, skip
    if not any(best.values()):
        return

    # ✅ Display actual ML odds for both teams
    away_ml_odds = format_american(ml_odds.get(away, "N/A"))
    home_ml_odds = format_american(ml_odds.get(home, "N/A"))

    # header
    header = (
        f"🏟️ {away} vs {home}\n"
        f"📅 {when}\n"
        f"🏆 ML: {away}: {away_ml_odds} | {home}: {home_ml_odds}\n"
        f"📏 Spread: {best['spreads']['team']} {best['spreads']['point']} @ {format_american(best['spreads']['odds'])}\n"
        f"📊 Total: {best['totals']['point']} — Over @ {format_american(best['totals']['odds'])}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
    )

    # individual sections
    sections = []
    for mk, data in [("MONEYLINE", best["h2h"]), ("SPREAD", best["spreads"]), ("TOTALS", best["totals"])]:
        if data:
            pick = data["team"] + (f" {data['point']:+}" if data["point"]!="" else "")
            sections.append(
                f"📊 {mk} BET\n"
                f"🔥 Pick: {pick}\n"
                f"💵 Odds: {format_american(data['odds'])}\n"
                f"📈 EV: +{data['ev']}% {data['label']}\n"
                f"🧮 Implied Prob: {data['imp']}%\n"
                f"🧠 Model Prob: {data['mod']}%\n"
                f"🔍 Edge: +{data['edge']}%\n"
                "⚾ ——————"
            )

    msg = header + "\n".join(sections)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)
    
# ── MAIN ──
def main():
    try:
        games = fetch_odds()
    except Exception as e:
        print("Fetch error:", e)
        return

    team_ids = get_mlb_team_ids()  # ✅ Fetch MLB team IDs once

    today = datetime.now(TIMEZONE).date()  # ✅ Get today's date in Eastern Time

    for g in games:
        home = g["home_team"]
        away = g["away_team"]

        # ✅ Filter: only valid MLB teams
        if home not in team_ids or away not in team_ids:
            continue

        # ✅ Filter: only games scheduled for today (Eastern Time)
        try:
            game_time = datetime.fromisoformat(g["commence_time"].replace("Z", "+00:00")).astimezone(TIMEZONE)
        except Exception as e:
            print(f"Time parse error for {away} vs {home}:", e)
            continue

        if game_time.date() != today:
            continue

        send_alert(g)
        time.sleep(2)

if __name__ == "__main__":
    main()
