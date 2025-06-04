import requests
import time
import logging
from datetime import datetime
import pytz
import telegram

# --- CONFIG ---
ODDS_API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"  # Your OddsAPI key here
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = 964091254

# How many bets to send per cycle
MAX_BETS_PER_CYCLE = 8

# Pause time between cycles (in seconds)
PAUSE_BETWEEN_CYCLES = 17 * 60  # 17 minutes

# Timezone to display (e.g., US/Eastern)
LOCAL_TIMEZONE = pytz.timezone("US/Eastern")

# Initialize Telegram Bot
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Track already sent bets to avoid duplicates
sent_bets = set()

logging.basicConfig(level=logging.INFO)

def fetch_today_games():
    url = f'https://api.the-odds-api.com/v4/sports/baseball_mlb/odds'
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'h2h,spreads,totals',
        'dateFormat': 'iso',
        'oddsFormat': 'american'
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        games = response.json()
        # Filter only games scheduled for today local time
        today = datetime.now(LOCAL_TIMEZONE).date()
        filtered_games = []
        for game in games:
            game_time_utc = datetime.fromisoformat(game['commence_time'].replace('Z','+00:00'))
            game_time_local = game_time_utc.astimezone(LOCAL_TIMEZONE)
            if game_time_local.date() == today:
                filtered_games.append(game)
        return filtered_games
    except Exception as e:
        logging.error(f"Error fetching games: {e}")
        return []

def format_american_odds(odds):
    if odds > 0:
        return f"+{odds}"
    else:
        return str(odds)

def format_bet(game):
    try:
        home = game.get('home_team', 'Unknown Home')
        away = game.get('away_team', 'Unknown Away')
        commence_utc = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
        commence_local = commence_utc.astimezone(LOCAL_TIMEZONE)
        start_time_str = commence_local.strftime('%Y-%m-%d %I:%M %p %Z')

        bookmakers = game.get('bookmakers', [])
        if not bookmakers:
            return None  # no bookmaker odds, skip

        # Use first bookmaker for simplicity
        bookmaker = bookmakers[0]
        book_name = bookmaker.get('title', 'Unknown Bookmaker')

        markets = {m['key']: m for m in bookmaker.get('markets', [])}

        # Moneyline
        moneyline_str = "💰 Moneyline:"
        if 'h2h' in markets:
            h2h = markets['h2h']['outcomes']
            ml_away = next((o for o in h2h if o['name'] == away), None)
            ml_home = next((o for o in h2h if o['name'] == home), None)
            if ml_away and ml_home:
                moneyline_str += f"\n- {away}: {format_american_odds(ml_away['price'])} ⚠️"
                moneyline_str += f"\n- {home}: {format_american_odds(ml_home['price'])} ⚠️"
            else:
                moneyline_str += "\n- Odds not available"
        else:
            moneyline_str += "\n- Odds not available"

        # Spread
        spread_str = "🟩 Spread:"
        if 'spreads' in markets:
            spreads = markets['spreads']['outcomes']
            spread_away = next((s for s in spreads if s['name'] == away), None)
            spread_home = next((s for s in spreads if s['name'] == home), None)
            if spread_away and spread_home:
                spread_away_line = markets['spreads']['point']
                spread_home_line = -spread_away_line
                spread_str += f"\n- {away} {spread_away_line:+.1f}: {format_american_odds(spread_away['price'])} ⚠️"
                spread_str += f"\n- {home} {spread_home_line:+.1f}: {format_american_odds(spread_home['price'])} ⚠️"
            else:
                spread_str += "\n- Odds not available"
        else:
            spread_str += "\n- Odds not available"

        # Totals (Over/Under)
        total_str = "📈 Total:"
        if 'totals' in markets:
            totals = markets['totals']['outcomes']
            total_point = markets['totals']['point']
            over = next((t for t in totals if t['name'].lower() == 'over'), None)
            under = next((t for t in totals if t['name'].lower() == 'under'), None)
            if over and under:
                total_str += f"\n- Over {total_point}: {format_american_odds(over['price'])} ⚠️"
                total_str += f"\n- Under {total_point}: {format_american_odds(under['price'])} ⚠️"
            else:
                total_str += "\n- Odds not available"
        else:
            total_str += "\n- Odds not available"

        # Dummy trends and lean (for demo, you must replace with real trend logic)
        trends_str = f"📊 Trends:\n- {away}: 🔥 3-2 ATS in last 5\n- {home}: ❄️ 2-3 ATS in last 5"
        lean_str = f"🔎 Lean: {home} moneyline ⚠️"
        advice = "📌 Bet smart. Look for 🔒 low-risk run lines."

        msg = (
            f"📊 MLB Bet Preview\n"
            f"🕒 {start_time_str}\n"
            f"⚔️ {away} @ {home}\n"
            f"🏦 {book_name}\n\n"
            f"{moneyline_str}\n\n"
            f"{spread_str}\n\n"
            f"{total_str}\n\n"
            f"{trends_str}\n\n"
            f"{lean_str}\n"
            f"{advice}"
        )
        return msg
    except Exception as e:
        logging.error(f"Error formatting bet message: {e}")
        return None

def main_loop():
    while True:
        try:
            send_bets()
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        logging.info("Sleeping for 15 minutes...")
        time.sleep(15 * 60)

if __name__ == "__main__":
    main_loop()
