import requests
import json
from datetime import datetime, timedelta
import pytz

# === CONFIG ===
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
ODDS_API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
SPORTMONKS_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0G-BLTAplBKVHt8YL6m0jNZpmUbCu4szH"
ODDSAPI_SPORTS = ["baseball_mlb", "basketball_wnba", "soccer_usa_mls", "soccer_usa_nwsl"]

# === TIME SETUP ===
tz = pytz.timezone("US/Eastern")
now = datetime.now(tz)
today = now.replace(hour=0, minute=0, second=0, microsecond=0)
tomorrow = today + timedelta(days=1)

def format_odds(value):
    return f"{'+' if value > 0 else ''}{value}"

def implied_prob(odds):
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram error:", e)

def build_bet_message(header, time_str, moneylines, spreads, totals, best_bet_line):
    message = f"🟢 *{header}*\n📅 {time_str}\n"
    if moneylines: message += f"🏆 ML: {moneylines}\n"
    if spreads: message += f"📏 Spread: {spreads}\n"
    if totals: message += f"📊 Total: {totals}\n"
    if best_bet_line: message += f"✅ *Best Bet*: {best_bet_line}\n"
    return message.strip()

def fetch_oddsapi_bets():
    messages = []
    MAX_REALISTIC_DIFF = 15.0  # max % difference allowed for alerts

    for sport in ODDSAPI_SPORTS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american"
        }

        try:
            res = requests.get(url, params=params)
            games = res.json()
            for game in games:
                start_time = datetime.fromisoformat(game['commence_time'].replace("Z", "+00:00")).astimezone(tz)
                if not (today <= start_time < tomorrow):
                    continue

                home = game['home_team']
                away = game['away_team']
                header = f"{home} vs {away}"
                time_str = start_time.strftime("%b %d %I:%M %p")
                moneylines = spreads = totals = ""
                best_ev = -999
                best_bet_line = ""

                markets = game['bookmakers'][0]['markets'] if game.get("bookmakers") else []
                for m in markets:
                    if m['key'] == 'h2h':
                        lines = []
                        for team in m['outcomes']:
                            team_name = team['name']
                            price = team['price']
                            lines.append(f"{team_name}: {format_odds(price)}")

                            # Placeholder: you can plug your own model here for win_prob
                            win_prob = 0.56
                            imp_prob = implied_prob(price)
                            diff = round((win_prob - imp_prob) * 100, 2)

                            # Filter for realistic EV diffs
                            if 0 < diff < MAX_REALISTIC_DIFF and diff > best_ev:
                                best_ev = diff
                                best_bet_line = f"{team_name} @ {format_odds(price)} (Win Prob {round(win_prob*100, 2)}% vs Implied {round(imp_prob*100, 2)}% | Diff {diff}%)"
                        moneylines = " | ".join(lines)

                    if m['key'] == 'spreads':
                        spreads = " | ".join(
                            f"{o['name']} {o['point']} @ {format_odds(o['price'])}" for o in m['outcomes']
                        )

                    if m['key'] == 'totals':
                        totals = " | ".join(
                            f"{o['name']} {o['point']} @ {format_odds(o['price'])}" for o in m['outcomes']
                        )

                if best_ev > 0:  # only send messages with good value bets
                    message = build_bet_message(header, time_str, moneylines, spreads, totals, best_bet_line)
                    messages.append(message)

        except Exception as e:
            print("OddsAPI error:", e)
    return messages

def fetch_sportmonks_bets():
    messages = []
    try:
        url = f"https://soccer.sportmonks.com/api/v2.0/fixtures?api_token={SPORTMONKS_KEY}&include=league,localTeam,visitorTeam&date_from={today.strftime('%Y-%m-%d')}&date_to={tomorrow.strftime('%Y-%m-%d')}"
        res = requests.get(url)
        data = res.json().get("data", [])

        for match in data:
            league = match["league"]["data"]["name"]
            home = match["localTeam"]["data"]["name"]
            away = match["visitorTeam"]["data"]["name"]
            start_time = datetime.fromisoformat(match["time"]["starting_at"]["date_time"]).astimezone(tz)

            if not (today <= start_time < tomorrow):
                continue

            header = f"{home} vs {away}"
            time_str = start_time.strftime("%b %d %I:%M %p")

            # Historical logic (placeholder)
            home_form = "WWD"
            away_form = "LDL"
            win_prob = 0.61
            imp_prob = 0.50
            diff = round((win_prob - imp_prob) * 100, 2)
            best_bet_line = f"{home} ML (Win Prob 61% vs Implied 50% | Diff {diff}%)"

            body = f"🏟️ {league}\n📈 Recent Form: {home} {home_form} • {away} {away_form}\n"
            body += f"✅ *Best Bet*: {best_bet_line}"

            messages.append(f"🟢 *{header}*\n📅 {time_str}\n{body.strip()}")

    except Exception as e:
        print("SportMonks error:", e)
    return messages

def main():
    print("✅ Fetching all bets...")
    all_messages = fetch_oddsapi_bets() + fetch_sportmonks_bets()
    if all_messages:
        for msg in all_messages:
            send_telegram_message(msg)
        print(f"✅ Sent {len(all_messages)} total bets.")
    else:
        print("⚠️ No bets found.")

if __name__ == "__main__":
    main()
