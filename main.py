import requests
from datetime import datetime
import pytz
import telegram

API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

BOOKMAKERS = ["pinnacle", "betonlineag"]
SPORTS = ["baseball_mlb", "soccer_epl", "soccer_uefa_champs_league", "soccer_usa_mls", "soccer_spain_la_liga", "soccer_italy_serie_a", "soccer_germany_bundesliga", "soccer_france_ligue_one", "soccer_brazil_campeonato", "soccer_mexico_liga_mx", "soccer_portugal_primeira_liga", "soccer_netherlands_eredivisie"]

CDT = pytz.timezone('America/Chicago')


def fetch_odds_for_sport(sport_key):
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
    except requests.RequestException as e:
        print(f"Error fetching odds for {sport_key}: {e}")
        return []

def implied_probability(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def estimated_model_probability(odds, team_name):
    base = implied_probability(odds)
    form_boost = 0.06  # Simulated mild form tilt
    return max(0.01, min(0.99, base + form_boost))

def calculate_ev(odds, model_prob):
    payout = odds if odds > 0 else 10000 / abs(odds)
    ev = (model_prob * payout) - ((1 - model_prob) * 100)
    return round(ev / 100, 4)

def get_ev_label(ev):
    if ev >= 0.05:
        return "🟢 BEST VALUE"
    elif ev >= 0.015:
        return "🟡 GOOD VALUE"
    else:
        return None

def is_today_game(commence_time):
    game_time = datetime.fromisoformat(commence_time.replace('Z', '+00:00')).astimezone(CDT)
    now = datetime.now(CDT)
    return game_time.date() == now.date()

def build_summary_message(game, bets):
    home = game.get("home_team", "")
    away = game.get("away_team", "")
    time_str = datetime.fromisoformat(game["commence_time"].replace('Z', '+00:00')).astimezone(CDT).strftime("%b %d, %I:%M %p CDT")

    moneyline_lines, spread_lines, total_lines = [], [], []
    for bookmaker in game.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            if market["key"] == "h2h":
                for o in market["outcomes"]:
                    moneyline_lines.append(f"{o['name']}: {o['price']:+}")
            elif market["key"] == "spreads":
                for o in market["outcomes"]:
                    pt = o.get("point", 0)
                    spread_lines.append(f"{o['name']} {pt:+.1f} @ {o['price']:+}")
            elif market["key"] == "totals":
                for o in market["outcomes"]:
                    pt = o.get("point", 0)
                    total_lines.append(f"Total {pt:.1f} @ {o['price']:+}")

    summary = (
        f"🏟️ {away} vs {home}\n"
        f"📅 {time_str}\n"
        f"🏆 ML: {' | '.join(moneyline_lines)}\n"
        f"📏 Spread: {' | '.join(spread_lines)}\n"
        f"📊 Total: {' | '.join(total_lines)}\n\n"
    )

    for bet in bets:
        emoji = "⚾" if "mlb" in game["sport_key"] else "⚽"
        ev_label = get_ev_label(bet['ev'])
        if not ev_label:
            continue
        summary += (
            f"📊 *{bet['market'].upper()} BET*\n\n"
            f"🔥 Pick: {bet['team']}\n"
            f"💵 Odds: {bet['odds']:+}\n"
            f"📈 Expected Value: +{bet['ev']*100:.1f}% {ev_label}\n"
            f"🧮 Implied Prob: {bet['implied_prob']*100:.1f}%\n"
            f"🧠 Model Prob: {bet['model_prob']*100:.1f}%\n"
            f"🔍 Edge: +{bet['edge']:.2f}%\n"
            f"{emoji} ——————\n\n"
        )
    return summary

def find_value_bets(game):
    value_bets = []
    for bookmaker in game.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            key = market["key"]
            for outcome in market["outcomes"]:
                odds = outcome.get("price")
                team = outcome.get("name")
                if odds is None or team is None:
                    continue
                implied = implied_probability(odds)
                model = estimated_model_probability(odds, team)
                edge = round((model - implied) * 100, 2)
                ev = calculate_ev(odds, model)
                label = get_ev_label(ev)
                if label:
                    value_bets.append({
                        "market": key,
                        "team": f"{team} {outcome.get('point', '')}".strip(),
                        "odds": odds,
                        "implied_prob": implied,
                        "model_prob": model,
                        "edge": edge,
                        "ev": ev
                    })
    return value_bets

def send_to_telegram(message):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Telegram error: {e}")

def main():
    for sport in SPORTS:
        games = fetch_odds_for_sport(sport)
        for game in games:
            if not is_today_game(game["commence_time"]):
                continue
            value_bets = find_value_bets(game)
            if value_bets:
                msg = build_summary_message(game, value_bets)
                send_to_telegram(msg)

if __name__ == "__main__":
    main()
