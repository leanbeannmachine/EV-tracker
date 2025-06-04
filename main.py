import requests
import datetime
import pytz
import random
import time
from telegram import Bot

# ✅ CONFIG
ODDS_API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
MARKETS = "h2h,spreads,totals"
BOOKMAKERS = "fanduel,draftkings,betus"

bot = Bot(token=TELEGRAM_TOKEN)
sent_games = set()

def get_mlb_odds():
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": MARKETS,
        "bookmakers": BOOKMAKERS,
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"OddsAPI Error: {response.status_code} - {response.text}")
    return response.json()

def is_today(iso_date):
    today = datetime.datetime.now(pytz.timezone("US/Eastern")).date()
    match_time = datetime.datetime.fromisoformat(iso_date.replace("Z", "+00:00")).astimezone(pytz.timezone("US/Eastern")).date()
    return match_time == today

def format_bet(game):
    home_team = game['home_team']
    away_team = game['away_team']
    commence_time_utc = datetime.datetime.fromisoformat(game['commence_time'].replace("Z", "+00:00"))
    eastern_time = commence_time_utc.astimezone(pytz.timezone("US/Eastern"))
    readable_time = eastern_time.strftime("%Y-%m-%d %I:%M %p ET")

    bookmaker_data = game['bookmakers'][0]
    bookmaker = bookmaker_data['title']
    markets = {m['key']: m for m in bookmaker_data['markets']}

    def get_odds(market, team):
        try:
            return next(outcome['price'] for outcome in markets[market]['outcomes'] if outcome['name'] == team)
        except:
            return None

    def get_total_line(market, side):
        try:
            return next(
                (o['point'], o['price']) for o in markets['totals']['outcomes'] if o['name'].lower().startswith(side)
            )
        except:
            return None, None

    # Odds
    home_ml = get_odds("h2h", home_team)
    away_ml = get_odds("h2h", away_team)

    home_spread = get_odds("spreads", home_team)
    away_spread = get_odds("spreads", away_team)
    spread_point = markets.get("spreads", {}).get("outcomes", [{}])[0].get("point", "N/A")

    over_pt, over_odds = get_total_line("totals", "over")
    under_pt, under_odds = get_total_line("tot
