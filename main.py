import requests
from datetime import datetime, timedelta
import pytz
import telegram

API_KEY = "b478dbe3f62f1f249a7c319cb2248bc5"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# ✅ TEMP FIX — Use books with fewer restrictions to avoid 401s
BOOKMAKERS = ["pinnacle", "betonlineag"]

SPORTS = [
    "baseball_mlb",
    "basketball_wnba",
    "soccer_usa_mls",
    "soccer_usa_nwsl",  # Fixed key
    "mma_mixed_martial_arts"
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

def format_message(game, market, outcome, odds, ev, start_time):
    team = outcome.get('name')
    label = format_ev_label(ev)
    readable_time = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(pytz.timezone('US/Eastern')).strftime('%b %d, %I:%M %p ET')
    odds_str = f"{odds:+}" if isinstance(odds, int) else odds

    return (
        f"📊 *{market.upper()}*\n"
        f"*Pick:* {team}\n"
        f"*Odds:* {odds_str}\n"
        f"*Expected Value:* {ev:.1f}%\n"
        f"{label}\n"
        f"🕒 *Game Time:* {readable_time}\n"
        f"Good luck! 🍀\n"
        f"——————"
    )

def send_telegram_message(message):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
    except telegram.error.TelegramError as e:
        print(f"Telegram error: {e}")

def main():
    for sport in SPORTS:
        games = fetch_odds_for_sport(sport)
        for game in games:
            home_team = game.get('home_team')
            commence_time = game.get('commence_time')

            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    market_type = market.get('key')
                    for outcome in market.get('outcomes', []):
                        odds = outcome.get('price')
                        if odds is None:
                            continue

                        # Placeholder win prob: you can customize this!
                        implied_prob = 0.55 if odds < 0 else 0.48
                        ev = calculate_ev(odds, implied_prob)

                        if ev > 3:  # Filter for solid value
                            msg = format_message(game, market_type, outcome, odds, ev, commence_time)
                            send_telegram_message(msg)

if __name__ == "__main__":
    main()
