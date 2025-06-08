import requests
from datetime import datetime, timedelta
import pytz
import telegram

import random

def generate_reasoning(market_key, team_name):
    team = team_name.split()[-1] if team_name else "this team"

    if market_key == "spreads":
        reasons = [
            f"{team} has consistently covered recent spreads due to strong defense.",
            f"{team}'s margin of victory trends well against this line.",
            f"{team} matches up well and tends to outperform expectations.",
            f"Based on recent form, {team} has value on this spread.",
        ]
    elif market_key == "totals":
        if "Over" in team_name:
            reasons = [
                "Both teams play at a fast pace, suggesting a high-scoring affair.",
                "Recent matchups show consistent totals going over this line.",
                "Offensive efficiency is expected to push the game over.",
                "Scoring trends favor the over in this matchup.",
            ]
        else:
            reasons = [
                "Defensive intensity and slower tempo point to a low-scoring game.",
                "Recent totals between these teams tend to fall short of this line.",
                "Offensive struggles make the under appealing here.",
                "Pace and recent form favor the under hitting.",
            ]
    elif market_key == "h2h":
        reasons = [
            f"{team} has the edge based on recent form and matchups.",
            f"Momentum and team stats favor {team} to win outright.",
            f"{team} has outperformed opponents in similar spots.",
            f"Confidence in {team} stems from both recent wins and depth.",
        ]
    else:
        reasons = [
            f"{team} is in a strong position based on matchup metrics.",
            "Value play based on line movement and implied probabilities.",
        ]

    return random.choice(reasons)

API_KEY = "b478dbe3f62f1f249a7c319cb2248bc5"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

BOOKMAKERS = ["pinnacle", "betonlineag"]

SPORTS = [
    "baseball_mlb",
    "basketball_wnba",
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
        return "🟢 BEST VALUE"
    elif ev > 3:
        return "🟡 GOOD VALUE"
    elif ev > 0:
        return "🟠 SLIGHT EDGE"
    else:
        return "🔴 NO EDGE"

def generate_reasoning(market, team):
    if market == "h2h":
        return f"{team} has a favorable head-to-head matchup based on recent results."
    elif market == "spreads":
        return f"{team} tends to cover the spread due to consistent scoring or defensive strength."
    elif market == "totals":
        return "Expected game tempo and efficiency favor this total line."
    return "No specific reasoning available."


def format_message(game, market, outcome, odds, ev, start_time):
    market_key = market.lower()
    team = outcome.get('name', '')
    line_info = ""

    # Add line for spreads and totals
    if market_key == "spreads" and 'point' in outcome:
        line_info = f" {outcome['point']:+.1f}"
    elif market_key == "totals" and 'point' in outcome:
        line_info = f" {outcome['point']:.1f}"

    # If outcome name is missing (like totals), build team label
    if not team:
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        team = f"{away} vs {home}"

    team_line = f"{team}{line_info}"
    label = format_ev_label(ev)
    readable_time = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(pytz.timezone('US/Eastern')).strftime('%b %d, %I:%M %p ET')
    odds_str = f"{odds:+}" if isinstance(odds, int) else odds
    reasoning = generate_reasoning(market, team)

    return (
        f"📊 *{market.upper()}*\n"
        f"*Pick:* {team_line}\n"
        f"*Odds:* {odds_str}\n"
        f"*Expected Value:* {ev:.1f}%\n"
        f"{label}\n"
        f"🕒 *Game Time:* {readable_time}\n"
        f"💡 *Reasoning:* {reasoning}\n"
        f"——————"
    )
    
def send_telegram_message(message):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
    except telegram.error.TelegramError as e:
        print(f"Telegram error: {e}")

def is_today_game(game_time_str):
    game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00')).astimezone(pytz.timezone('US/Eastern'))
    now = datetime.now(pytz.timezone('US/Eastern'))
    return game_time.date() == now.date()

def main():
    for sport in SPORTS:
        games = fetch_odds_for_sport(sport)
        for game in games:
            commence_time = game.get('commence_time')
            if not is_today_game(commence_time):
                continue

            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    market_type = market.get('key')
                    best_outcome = None
best_ev = -999  # or some very low number

for outcome in market.get('outcomes', []):
    odds = outcome.get('price')
    if odds is None:
        continue
    ev = calculate_ev(odds, game)  # Use your existing EV calculation function
    if ev > best_ev:
        best_ev = ev
        best_outcome = outcome

if best_outcome and best_ev >= YOUR_MIN_EV_THRESHOLD:  # e.g., 3.0% or whatever you want
    message = format_message(game, market_key, best_outcome, best_outcome['price'], best_ev, game['commence_time'])
    send_telegram_alert(message)

if __name__ == "__main__":
    main()
