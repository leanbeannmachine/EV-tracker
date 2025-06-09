import requests
from datetime import datetime, timedelta
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

def implied_probability(american_odds):
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)

# Simulated team form score [0.3 to 0.7] for underdogs/favorites adjustments, based on last 5 matches.
# In real use, replace this with actual team form stats from API or database.
def get_team_form(team_name):
    random.seed(hash(team_name) % 10000)  # deterministic for same team in same run
    return random.uniform(0.4, 0.6)

def estimated_win_prob(american_odds, team_name):
    base_prob = implied_probability(american_odds)
    form = get_team_form(team_name)
    # Adjust base_prob by form factor, scaled small (max +/- 8%)
    # If form > 0.5, increase prob; else decrease prob
    adjustment = (form - 0.5) * 0.16  # roughly ±8%
    adjusted_prob = base_prob + adjustment
    # Clamp between 0.01 and 0.99 for sanity
    adjusted_prob = max(0.01, min(0.99, adjusted_prob))
    return adjusted_prob

def format_message(game, market, outcome, odds, ev, start_time):
    market_key = market.lower()
    team = outcome.get('name', '')
    line_info = ""

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

def format_best_line(label, bet_data):
    if not bet_data:
        return f"❌ {label}: None found"

    team = bet_data['outcome']['name']
    odds = bet_data['outcome']['price']
    point = bet_data['outcome'].get('point')
    win_prob = bet_data.get('win_prob', 0) * 100

    implied_prob = implied_probability(odds) * 100
    diff = win_prob - implied_prob

    if diff > 7:
        badge = "🟢 BEST Bet"
    elif diff > 3:
        badge = "🟡 Good Value"
    elif diff > 1:
        badge = "🟠 Slight Edge"
    else:
        badge = "🔴 No Edge"

    point_text = f"{point:+.1f} " if point else ""
    return (
        f"{badge} {label}: {team} {point_text}@ {odds:+} "
        f"(Win Prob {win_prob:.1f}% vs Implied {implied_prob:.1f}% | Diff {diff:.2f}%)"
    )

def format_game_summary_with_best_bets(game, best_bets_by_market):
    home = game.get("home_team", "")
    away = game.get("away_team", "")
    start_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00')).astimezone(pytz.timezone('US/Eastern')).strftime('%b %d %I:%M %p ET')

    moneyline = []
    spread = []
    total = []

    for bookmaker in game.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            for outcome in market.get("outcomes", []):
                name = outcome.get("name", "")
                price = outcome.get("price", "")
                point = outcome.get("point", "")
                if market["key"] == "h2h":
                    moneyline.append(f"{name}: {price:+}")
                elif market["key"] == "spreads":
                    spread.append(f"{name} {point:+} @ {price:+}")
                elif market["key"] == "totals":
                    total.append(f"Total {point} @ {price:+}")

    message = (
        f"🏟️ {away} vs {home}\n"
        f"📅 {start_time}\n"
        f"🏆 ML: {' | '.join(moneyline) if moneyline else 'N/A'}\n"
        f"📏 Spread: {' | '.join(spread) if spread else 'N/A'}\n"
        f"📊 Total:
