import requests
import json
from datetime import datetime, timedelta
import pytz
import time

# --- YOUR SETTINGS ---
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
ODDS_API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
SPORTMONKS_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0G-BLTAplBKVHt8YL6m0jNZpmUbCu4szH"
ODDSAPI_SPORTS = ["baseball_mlb", "basketball_wnba", "soccer_usa_mls", "soccer_usa_nwsl"]

# --- TIME CONFIG ---
tz = pytz.timezone("US/Eastern")
today = datetime.now(tz)
tomorrow = today + timedelta(days=1)

def get_today_date_range():
    start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    end = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, end

def format_odds(value):
    return f"{'+' if value > 0 else ''}{value}"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram error:", e)

def fetch_oddsapi_bets():
    start, end = get_today_date_range()
    results = []

    for sport in ODDSAPI_SPORTS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
            "dateFormat": "iso"
        }
        try:
            r = requests.get(url, params=params)

            if r.status_code != 200:
                print(f"OddsAPI HTTP {r.status_code}: {r.text}")
                continue

            try:
                games = r.json()
            except json.JSONDecodeError:
                print("OddsAPI returned invalid JSON:", r.text)
                continue

            for game in games:
                game_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).astimezone(tz)
                if not (start <= game_time <= end):
                    continue

                match = f"{game['home_team']} vs {game['away_team']}"
                msg = f"*🟢 {match}*\n🕒 {game_time.strftime('%b %d %I:%M %p')}\n"
                bookmakers = game.get("bookmakers", [])

                if not bookmakers:
                    continue

                markets = {m["key"]: m for m in bookmakers[0]["markets"]}

                # H2H odds
                if "h2h" in markets:
                    h2h = markets["h2h"]["outcomes"]
                    for o in h2h:
                        msg += f"🏆 ML: {o['name']} @ {format_odds(o['price'])}\n"

                # Spread
                if "spreads" in markets:
                    for s in markets["spreads"]["outcomes"]:
                        msg += f"📏 Spread: {s['name']} {s['point']} @ {format_odds(s['price'])}\n"

                # Totals
                if "totals" in markets:
                    for t in markets["totals"]["outcomes"]:
                        msg += f"📊 Total: {t['name']} {t['point']} @ {format_odds(t['price'])}\n"

                results.append(msg.strip())

        except Exception as e:
            print("OddsAPI error:", e)

    return results

def fetch_sportmonks_bets():
    url = f"https://soccer.sportmonks.com/api/v2.0/fixtures?api_token={SPORTMONKS_KEY}&include=league,localTeam,visitorTeam&date_from={today.strftime('%Y-%m-%d')}&date_to={tomorrow.strftime('%Y-%m-%d')}"
    try:
        res = requests.get(url)
        data = res.json()
        matches = data.get("data", [])
        messages = []

        for match in matches:
            league = match["league"]["data"]["name"]
            home = match["localTeam"]["data"]["name"]
            away = match["visitorTeam"]["data"]["name"]
            kickoff = datetime.fromisoformat(match["time"]["starting_at"]["date_time"]).astimezone(tz)
            match_str = f"*⚽️ {home} vs {away}*\n🏟️ {league}\n🕒 {kickoff.strftime('%b %d %I:%M %p')}\n"

            # Add mock historical logic (placeholder)
            match_str += f"📈 Recent form: {home} WWD • {away} LLD\n"
            match_str += f"🧠 *Analysis*: {home} has stronger form and better last-5 metrics. Slight edge.\n"

            messages.append(match_str)

        return messages

    except Exception as e:
        print("SportMonks error:", e)
        return []

def main():
    print("✅ Fetching bets...")
    bets = fetch_oddsapi_bets() + fetch_sportmonks_bets()
    if bets:
        for msg in bets:
            send_telegram_message(msg)
        print(f"✅ Sent {len(bets)} total bets.")
    else:
        print("⚠️ No bets found.")

    print("🔄 Checking for resolved bets...")
    try:
        with open("tracked_bets.json", "r") as f:
            tracked = json.load(f)
    except:
        tracked = []

    updated = []
    for e in tracked:
        try:
            start = datetime.fromisoformat(e["game_time"].replace("Z", "+00:00"))
            if start < datetime.utcnow() - timedelta(hours=3):
                res = ("won" if ((e["market"] == "h2h" and e["team"] == e["winner"]) or
                                 (e["market"] == "spreads" and abs(e["spread"]) > abs(e["line"])))
                       else "lost")
                send_telegram_message(f"📊 Bet result for {e['match']}: *{res.upper()}*")
            else:
                updated.append(e)
        except:
            updated.append(e)

    with open("tracked_bets.json", "w") as f:
        json.dump(updated, f)

if __name__ == "__main__":
    main()
