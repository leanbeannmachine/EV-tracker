import requests
from datetime import datetime, timedelta
import pytz
import telegram

def is_game_today(commence_time):
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern).date()
    game_time = datetime.fromisoformat(commence_time.replace('Z', '+00:00')).astimezone(eastern).date()
    return game_time == now

API_KEY = "b478dbe3f62f1f249a7c319cb2248bc5"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

BOOKMAKERS = ["pinnacle", "betonlineag"]

SPORTS = [
    "baseball_mlb",
    "basketball_wnba",
    "soccer_usa_mls",
    "soccer_usa_nwsl",
]

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

def generate_reasoning(market, pick, game, line=None):
    home = game.get('home_team')
    away = game.get('away_team')

    if market == "h2h":
        if pick.lower() == "draw":
            return f"Draw expected as both {home} and {away} show balanced recent form."
        elif pick.lower() == home.lower():
            return f"{home} favored due to strong home performance and recent win streak."
        elif pick.lower() == away.lower():
            return f"{away} looks strong on the road with solid offensive stats."
    elif market == "spreads":
        return f"{pick} covers the spread with strong defense and recent margins."
    elif market == "totals":
        if "over" in pick.lower():
            return f"Expecting a high scoring game over the total line."
        elif "under" in pick.lower():
            return f"Defenses likely to dominate, keeping score under the total."
    return "This bet shows promising value based on recent trends."

def format_message(game, market, outcome, odds, ev, start_time):
    team = outcome.get('name')
    line = outcome.get('point')  # spread/run line or total line number
    label = format_ev_label(ev)
    readable_time = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(pytz.timezone('US/Eastern')).strftime('%b %d, %I:%M %p ET')
    odds_str = f"{odds:+}" if isinstance(odds, int) else str(odds)
    market_display = market.upper()

    # Build pick string with line for spreads and totals
    if market in ["spreads", "totals"] and line is not None:
        # For totals, line is usually float like 2.5, and pick is "Over" or "Under"
        if market == "totals":
            pick_str = f"{team} {line}"
        else:
            # For spreads, line is run/goal/point spread, combine with pick (team)
            pick_str = f"{team} {line:+}"  # adds + or - sign
    else:
        pick_str = team

    reasoning = generate_reasoning(market, team, game, line)

    message = (
        f"📊 *{market_display}*\n"
        f"*Pick:* {pick_str}\n"
        f"*Odds:* {odds_str}\n"
        f"*Expected Value:* {ev:.1f}%\n"
        f"{label}\n"
        f"🕒 *Game Time:* {readable_time}\n"
        f"💡 *Reasoning:* {reasoning}\n"
        f"——————"
    )
    return message

def send_telegram_message(message):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
    except telegram.error.TelegramError as e:
        print(f"Telegram error: {e}")

def send_results_alerts():
    # Placeholder: you would fetch or keep track of finished matches and outcomes,
    # then send messages summarizing which bets won or lost.
    #
    # Example message:
    # "🏆 Results Update:\n
    #  H2H: New York Yankees WON ✅\n
    #  Spread: D.C. United LOST ❌\n
    #  Totals: Over 2.5 WON ✅"
    #
    # This requires a separate data source or caching mechanism for match results.
    pass

def main():
    for sport in SPORTS:
        games = fetch_odds_for_sport(sport)
        for game in games:
    commence_time = game.get('commence_time')
    if not commence_time or not is_game_today(commence_time):
        continue  # skip games not starting today

            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    market_type = market.get('key')
                    for outcome in market.get('outcomes', []):
                        odds = outcome.get('price')
                        if odds is None:
                            continue

                        # Example win probability — you can improve this!
                        implied_prob = 0.55 if odds < 0 else 0.48
                        ev = calculate_ev(odds, implied_prob)

                        if ev > 3:  # Filter for decent value bets
                            msg = format_message(game, market_type, outcome, odds, ev, commence_time)
                            send_telegram_message(msg)

    # You can call send_results_alerts() here or schedule it to run separately
    # send_results_alerts()

if __name__ == "__main__":
    main()
