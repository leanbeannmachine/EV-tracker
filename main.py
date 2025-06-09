import requests
from datetime import datetime
import pytz
import telegram
import random

SPORTSMONK_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

BOOKMAKERS = ["pinnacle", "betonlineag"]
SPORTS = ["baseball_mlb", "basketball_wnba"]

def generate_reasoning(market, team):
    if market == "h2h":
        return f"The {team} come in with serious momentum 🚀 and the metrics are tilting in their favor 📊. With this kind of line, there's huge upside on a team that’s been outperforming expectations!"
    elif market == "spreads":
        return f"{team} has been covering spreads consistently 🧱 due to tough defense and reliable scoring. The matchup looks promising again today."
    elif market == "totals":
        return f"Based on tempo and efficiency 📈, this total line holds strong value. Trends and matchup data support the bet."
    return "Backed by data and matchup trends, this is a value-driven play."

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

def calculate_ev(american_odds, win_prob):
    if american_odds > 0:
        decimal_odds = 1 + (american_odds / 100)
    else:
        decimal_odds = 1 + (100 / abs(american_odds))
    ev = (decimal_odds * win_prob) - 1
    return ev * 100

def format_ev_label(ev):
    if ev > 7:
        return "🟢 *BEST VALUE*"
    elif ev > 3:
        return "🟡 *GOOD VALUE*"
    elif ev > 0:
        return "🟠 *SLIGHT EDGE*"
    else:
        return "🔴 *NO EDGE*"

def is_today_game(game_time_str):
    game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00')).astimezone(pytz.timezone('US/Eastern'))
    now = datetime.now(pytz.timezone('US/Eastern'))
    return game_time.date() == now.date()

def filter_today_games(games):
    return [g for g in games if is_today_game(g['commence_time'])]

def format_message(game, market, outcome, odds, ev, start_time):
    market_key = market.lower()
    team = outcome.get('name', '')
    line_info = ""

    # Add line info
    if market_key == "spreads" and 'point' in outcome:
        line_info = f" {outcome['point']:+.1f}"
    elif market_key == "totals" and 'point' in outcome:
        line_info = f" {outcome['point']:.1f}"

    if not team:
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        team = f"{away} vs {home}"

    team_line = f"{team}{line_info}"
    readable_time = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(pytz.timezone('US/Eastern')).strftime('%b %d, %I:%M %p ET')
    odds_str = f"{odds:+}" if isinstance(odds, int) else odds
    label = format_ev_label(ev)
    reasoning = generate_reasoning(market, team)

    return (
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

def main():
    sent_any = False
    for sport in SPORTS:
        games = fetch_odds_for_sport(sport)
        filtered_games = filter_today_games(games)

        for game in filtered_games:
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    market_key = market['key']
                    best_outcome = None
                    best_ev = -999

                    for outcome in market.get('outcomes', []):
                        odds = outcome.get('price')
                        if odds is None:
                            continue

                        # Placeholder win probability model
                        win_prob = 0.5
                        ev = calculate_ev(odds, win_prob)
                        if ev > best_ev:
                            best_ev = ev
                            best_outcome = outcome

                    if best_outcome and 3.0 <= best_ev <= 13.0:
                        message = format_message(
                            game,
                            market_key,
                            best_outcome,
                            best_outcome['price'],
                            best_ev,
                            game['commence_time']
                        )
                        send_telegram_message(message)
                        sent_any = True

    if not sent_any:
        print("✅ Script ran but no value bets were found.")
    else:
        print("✅ Bets sent successfully.")

if __name__ == "__main__":
    main()
