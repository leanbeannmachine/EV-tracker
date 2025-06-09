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

def format_bet_message(game, best_bets):
    message = f"🟢 *{game['home']} vs {game['away']}*\n"
    message += f"📅 {game['date']} {game['time']}\n"
    message += f"🏆 *ML:* {game['away']}: {game['odds']['moneyline'][game['away']]} | {game['home']}: {game['odds']['moneyline'][game['home']]}\n"
    message += f"📏 *Spread:* {game['away']} {game['odds']['spread'][game['away']]['point']} @ {game['odds']['spread'][game['away']]['price']} | {game['home']} {game['odds']['spread'][game['home']]['point']} @ {game['odds']['spread'][game['home']]['price']}\n"
    message += f"📊 *Total:* Over {game['odds']['totals']['point']} @ {game['odds']['totals']['over']} | Under {game['odds']['totals']['point']} @ {game['odds']['totals']['under']}\n"

    for bet_type, bet_info in best_bets.items():
        if bet_type == "moneyline":
            message += f"💰 *Best ML Bet:* {bet_info['team']} @ {bet_info['odds']} (🎯 Win {bet_info['win_prob']}% vs 📉 Imp. {bet_info['imp_prob']}% | 🔥 Diff {bet_info['diff']}%)\n"
        elif bet_type == "spread":
            message += f"📐 *Best Spread:* {bet_info['team']} {bet_info['point']} @ {bet_info['odds']} (🎯 Win {bet_info['win_prob']}% vs 📉 Imp. {bet_info['imp_prob']}% | 🔥 Diff {bet_info['diff']}%)\n"
        elif bet_type == "total":
            message += f"📈 *Best Total:* {bet_info['type']} {bet_info['point']} @ {bet_info['odds']} (🎯 Win {bet_info['win_prob']}% vs 📉 Imp. {bet_info['imp_prob']}% | 🔥 Diff {bet_info['diff']}%)\n"
    return message

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram error:", e)

def build_bet_message(header, time_str, moneylines, spreads, totals, best_bet_line, best_spread_line=None, best_total_line=None):
    message = f"🟢 *{header}*\n📅 {time_str}\n"
    if moneylines:
        message += f"🏆 ML: {moneylines}\n"
    if spreads:
        message += f"📏 Spread: {spreads}\n"
    if totals:
        message += f"📊 Total: {totals}\n"
    
    if best_bet_line:
        message += f"✅ *Best Bet ML*: {best_bet_line}\n"
    if best_spread_line:
        message += f"✅ *Best Bet Spread*: {best_spread_line}\n"
    if best_total_line:
        message += f"✅ *Best Bet Total*: {best_total_line}\n"
    
    return message.strip()

def fetch_oddsapi_bets():
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "regions": "us",
        "oddsFormat": "american",
        "markets": "h2h,spreads,totals",
        "apiKey": ODDS_API_KEY
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        for game in data:
            teams = game["teams"]
            home_team = game["home_team"]
            away_team = [team for team in teams if team != home_team][0]
            commence_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).astimezone(pytz.timezone("America/New_York"))
            time_str = commence_time.strftime("%b %d %I:%M %p")

            bookmakers = game.get("bookmakers", [])
            if not bookmakers:
                continue

            best_bookmaker = bookmakers[0]
            markets = best_bookmaker.get("markets", [])
            header = f"{away_team} vs {home_team}"
            moneylines = spreads = totals = ""
            best_bet_line = ""
            best_spread_line = ""
            best_total_line = ""

            # Moneyline
            for m in markets:
                if m['key'] == 'h2h':
                    lines = []
                    best_ev = -999
                    for o in m['outcomes']:
                        name = o['name']
                        price = o['price']
                        win_prob = 0.56  # placeholder
                        imp = implied_prob(price)
                        diff = round((win_prob - imp) * 100, 2)
                        ev_line = f"{name} @ {format_odds(price)} (Win Prob {round(win_prob * 100, 1)}% vs Implied {round(imp * 100, 2)}% | Diff {diff}%)"
                        lines.append(f"{name}: {format_odds(price)}")
                        if diff > best_ev:
                            best_ev = diff
                            best_bet_line = ev_line
                    moneylines = " | ".join(lines)

            # Spread
            for m in markets:
                if m['key'] == 'spreads':
                    lines = []
                    best_ev = -999
                    for o in m['outcomes']:
                        name = o['name']
                        price = o['price']
                        point = o['point']
                        win_prob = 0.54  # placeholder
                        imp = implied_prob(price)
                        diff = round((win_prob - imp) * 100, 2)
                        ev_line = f"{name} {point} @ {format_odds(price)} (Win Prob {round(win_prob * 100, 1)}% vs Implied {round(imp * 100, 2)}% | Diff {diff}%)"
                        lines.append(f"{name} {point} @ {format_odds(price)}")
                        if diff > best_ev:
                            best_ev = diff
                            best_spread_line = ev_line
                    spreads = " | ".join(lines)

            # Total
            for m in markets:
                if m['key'] == 'totals':
                    lines = []
                    best_ev = -999
                    for o in m['outcomes']:
                        name = o['name']
                        price = o['price']
                        point = o['point']
                        win_prob = 0.53  # placeholder
                        imp = implied_prob(price)
                        diff = round((win_prob - imp) * 100, 2)
                        ev_line = f"{name} {point} @ {format_odds(price)} (Win Prob {round(win_prob * 100, 1)}% vs Implied {round(imp * 100, 2)}% | Diff {diff}%)"
                        lines.append(f"{name} {point} @ {format_odds(price)}")
                        if diff > best_ev:
                            best_ev = diff
                            best_total_line = ev_line
                    totals = " | ".join(lines)

            # Format message
            message = build_bet_message(
                header, time_str,
                moneylines, spreads, totals,
                best_bet_line, best_spread_line, best_total_line
            )

            send_telegram_alert(message)

    except Exception as e:
        print(f"Error fetching OddsAPI data: {e}")

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
    try:
        games_today = fetch_odds_api_bets()

        for game in games_today:
            best_bets = calculate_best_bets(game)
            if best_bets:
                message = format_bet_message(game, best_bets)
                send_telegram_message(message)

    except Exception as e:
        print(f"🚨 Error in main execution: {e}")

if __name__ == "__main__":
    main()
