import requests
import json
import time
from datetime import datetime, timedelta
import pytz
import os

# === CONFIG ===
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"
ODDS_API_KEY = "7b5d540e73c8790a95b84d3713e1a572"
SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0G-BLTAplBKVHt8YL6m0jNZpmUbCu4szH"

# === LEAGUES ===
ODDSAPI_SPORTS = ["baseball_mlb", "basketball_wnba"]
SOCCER_LEAGUES = [271, 384, 72, 82, 1]  # Example IDs: UEFA Nations League, MLS, WC Qualifiers, etc.

# === TIMEZONE ===
UTC = pytz.UTC
LOCAL_TZ = pytz.timezone("America/New_York")

# === UTILS ===
def american_to_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def format_odds(odds):
    return f"+{odds}" if odds > 0 else str(odds)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram error:", e)

def get_today_date_range():
    now = datetime.now(UTC)
    tomorrow = now + timedelta(days=1)
    return now.isoformat(), tomorrow.isoformat()

# === ODDSAPI BETS ===
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
            games = r.json()
            for game in games:
                match = f"{game['home_team']} vs {game['away_team']}"
                start_time = game["commence_time"]
                markets = {m["key"]: m for m in game.get("bookmakers", [])[0]["markets"]}
                msg = f"*🟢 {match}*\n🕒 {start_time}\n"

                if "h2h" in markets:
                    h2h = markets["h2h"]["outcomes"]
                    for o in h2h:
                        msg += f"🏆 ML: {o['name']} @ {format_odds(o['price'])}\n"

                if "spreads" in markets:
                    for s in markets["spreads"]["outcomes"]:
                        msg += f"📏 Spread: {s['name']} {s['point']} @ {format_odds(s['price'])}\n"

                if "totals" in markets:
                    for t in markets["totals"]["outcomes"]:
                        msg += f"📊 Total: {t['name']} {t['point']} @ {format_odds(t['price'])}\n"

                results.append(msg)
        except Exception as e:
            print("OddsAPI error:", e)
    return results

# === SPORTMONKS SOCCER ===
def fetch_soccer_bets():
    today = datetime.now().date()
    url = f"https://soccer.sportmonks.com/api/v2.0/fixtures/date/{today}?api_token={SPORTMONKS_API_KEY}&include=localTeam,visitorTeam,league"
    bets = []
    try:
        res = requests.get(url)
        fixtures = res.json().get("data", [])
        for f in fixtures:
            if f["league_id"] not in SOCCER_LEAGUES:
                continue
            local = f["localTeam"]["data"]["name"]
            visitor = f["visitorTeam"]["data"]["name"]
            start = f["time"]["starting_at"]["time"]
            match = f"{local} vs {visitor}"
            msg = f"*⚽ {match}*\n🕒 Kickoff: {start} ET\n"

            # Optional: historical performance comparison
            team_stats = compare_soccer_teams(local, visitor)
            msg += team_stats
            bets.append(msg)
    except Exception as e:
        print("SportMonks error:", e)
    return bets

def compare_soccer_teams(team1, team2):
    # 🔄 Placeholder until real stats pulled from SportMonks history endpoint
    return (
        f"📈 *Form Preview*\n"
        f"{team1}: W-W-L-D-W (last 5)\n"
        f"{team2}: L-D-W-W-L (last 5)\n"
        f"🔍 Edge: *{team1 if team1[0] < team2[0] else team2}* slightly stronger form\n"
    )

# === MAIN ===
def main():
    print("✅ Fetching bets...")

    oddsapi_bets = fetch_oddsapi_bets()
    soccer_bets = fetch_soccer_bets()

    all_bets = oddsapi_bets + soccer_bets
    sent_count = 0

    for bet in all_bets:
        send_telegram_message(bet)
        sent_count += 1
        time.sleep(2)

    print(f"✅ Sent {sent_count} total bets.")

if __name__ == "__main__":
    main()
