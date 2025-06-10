import requests
from datetime import datetime
import pytz
import telegram
import random

# === CONFIG ===
API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
SPORTS = ["baseball_mlb", "soccer_epl", "soccer_uefa_champs_league", "soccer_spain_la_liga", "soccer_italy_serie_a", "soccer_germany_bundesliga", "soccer_france_ligue_one"]
BOOKMAKERS = ["pinnacle", "betonlineag"]

# === UTILITIES ===

def implied_probability(odds):
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

def get_team_form(team_name):
    random.seed(hash(team_name) % 10000)
    return random.uniform(0.45, 0.55)

def estimate_win_prob(odds, team_name):
    base_prob = implied_probability(odds)
    form = get_team_form(team_name)
    adjustment = (form - 0.5) * 0.18
    return max(0.01, min(0.99, base_prob + adjustment))

def calculate_ev(odds, win_prob):
    win_payout = odds if odds > 0 else 10000 / abs(odds)
    lose_payout = 100
    ev = (win_prob * win_payout) - ((1 - win_prob) * lose_payout)
    return round(ev / 100, 4)

def get_ev_label(ev):
    if ev >= 0.05:
        return "🟢 BEST VALUE"
    elif ev >= 0.015:
        return "🟡 GOOD VALUE"
    elif ev > 0:
        return "🟠 SLIGHT EDGE"
    else:
        return "🔴 NO EDGE"

def format_time(iso_time_str):
    cdt = pytz.timezone("America/Chicago")
    local_time = datetime.fromisoformat(iso_time_str.replace("Z", "+00:00")).astimezone(cdt)
    return local_time.strftime('%b %d, %I:%M %p CDT')

def fetch_odds(sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "bookmakers": ",".join(BOOKMAKERS)
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Failed to fetch odds for {sport_key}: {e}")
        return []

def is_today_game(iso_time_str):
    game_time = datetime.fromisoformat(iso_time_str.replace("Z", "+00:00")).astimezone(pytz.timezone("America/Chicago"))
    now = datetime.now(pytz.timezone("America/Chicago"))
    return game_time.date() == now.date()

def send_telegram_message(message):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
    except telegram.error.TelegramError as e:
        print(f"Telegram error: {e}")

# === FORMATTERS ===

def format_header(game, moneyline, spreads, totals):
    away, home = game["away_team"], game["home_team"]
    game_time = format_time(game["commence_time"])
    return (
        f"🏟️ {away} vs {home}\n"
        f"📅 {game_time}\n"
        f"🏆 ML: {' | '.join(moneyline) if moneyline else 'N/A'}\n"
        f"📏 Spread: {' | '.join(spreads) if spreads else 'N/A'}\n"
        f"📊 Total: {' | '.join(totals) if totals else 'N/A'}\n\n"
    )

def format_bet_message(market, team, odds, ev, point=None):
    emoji = get_ev_label(ev)
    ev_str = f"{ev*100:+.1f}%"
    line = f"{team} {point:+.1f}" if point is not None else team
    return (
        f"📊 *{market.upper()} BET*\n\n"
        f"🔥 *Pick:* **{line}**\n"
        f"💵 *Odds:* {odds:+}\n"
        f"📈 *Expected Value:* **{ev_str}**\n"
        f"🏷️ {emoji}\n"
        f"——————"
    )

# === MAIN LOGIC ===

def find_best_bets(game):
    best = {"h2h": None, "spreads": None, "totals": None}
    moneylines, spreads, totals = [], [], []

    for book in game.get("bookmakers", []):
        for market in book.get("markets", []):
            for outcome in market.get("outcomes", []):
                name, odds = outcome.get("name"), outcome.get("price")
                point = outcome.get("point", None)
                if name is None or odds is None:
                    continue

                win_prob = estimate_win_prob(odds, name)
                ev = calculate_ev(odds, win_prob)
                key = market["key"]

                # Format line info
                if key == "h2h":
                    moneylines.append(f"{name}: {odds:+}")
                elif key == "spreads":
                    spreads.append(f"{name} {point:+.1f} @ {odds:+}")
                elif key == "totals":
                    totals.append(f"Total {point:.1f} @ {odds:+}")

                # Replace if better EV
                if not best[key] or ev > best[key]['ev']:
                    best[key] = {"team": name, "odds": odds, "ev": ev, "point": point}

    return best, moneylines, spreads, totals

def main():
    all_games = []
    for sport in SPORTS:
        games = fetch_odds(sport)
        all_games.extend([g for g in games if is_today_game(g["commence_time"])])

    for game in all_games:
        best_bets, ml_lines, sp_lines, tot_lines = find_best_bets(game)
        header = format_header(game, ml_lines, sp_lines, tot_lines)

        for market in ["h2h", "spreads", "totals"]:
            bet = best_bets[market]
            if bet:
                msg = format_bet_message(market, bet["team"], bet["odds"], bet["ev"], bet["point"])
                send_telegram_message(header + msg)

if __name__ == "__main__":
    main()
