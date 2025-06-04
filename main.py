import requests
import logging
import time
from datetime import datetime
import pytz
import telegram

# --- Configuration ---
ODDS_API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = 964091254
SLEEP_MINUTES = 15
TIMEZONE = "US/Eastern"

# Initialize Telegram bot
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

# Track sent games to avoid duplicates during runtime
sent_bets = set()

def fetch_today_games():
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals,player_props",
        "dateFormat": "iso",
        "oddsFormat": "american"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        games = response.json()
        today = datetime.now(pytz.UTC).date()
        todays_games = []
        for game in games:
            try:
                game_time = datetime.fromisoformat(game['commence_time'].rstrip('Z')).date()
                if game_time == today:
                    todays_games.append(game)
            except Exception as e:
                logging.warning(f"Skipping game due to invalid time format: {e}")
        return todays_games
    except Exception as e:
        logging.error(f"Failed to fetch games: {e}")
        return []

def american_to_decimal(american_odds):
    if american_odds > 0:
        return 1 + (american_odds / 100)
    else:
        return 1 + (100 / abs(american_odds))

def calculate_ev(odds, win_prob):
    decimal_odds = american_to_decimal(odds)
    return (decimal_odds * win_prob) - 1

def parse_odds_and_reasoning(game):
    bookmakers = game.get('bookmakers', [])
    if not bookmakers:
        return None, "No bookmaker data."

    bookmaker = bookmakers[0]
    markets = bookmaker.get('markets', [])
    if not markets:
        return None, "No markets data."

    h2h = None
    spreads = None
    totals = None
    player_props = None

    for market in markets:
        key = market.get('key')
        if key == 'h2h':
            h2h = market.get('outcomes', [])
        elif key == 'spreads':
            spreads = market.get('outcomes', [])
        elif key == 'totals':
            totals = market.get('outcomes', [])
        elif key == 'player_props':
            player_props = market.get('outcomes', [])

    return {
        "h2h": h2h,
        "spreads": spreads,
        "totals": totals,
        "player_props": player_props,
    }, None

def estimate_win_probability(american_odds):
    # Simple conversion to implied probability
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)

def filter_good_bets(h2h_outcomes):
    # Filter for bets with implied win probability over 50% (safe bets)
    filtered = []
    for outcome in h2h_outcomes:
        price = outcome.get('price')
        if price is None:
            continue
        prob = estimate_win_probability(price)
        ev = calculate_ev(price, prob)
        # Criteria: EV positive and probability at least 0.5 (>=50%)
        if ev > 0 and prob >= 0.5:
            filtered.append({
                "name": outcome.get('name'),
                "price": price,
                "probability": prob,
                "ev": ev
            })
    return filtered

def format_bet_message(game):
    teams = game.get('teams')
    if not teams or len(teams) < 2:
        logging.error("Not enough teams info")
        return None

    home_team = game.get('home_team', teams[0])
    away_team = [t for t in teams if t != home_team]
    if not away_team:
        logging.error("Could not identify away team")
        return None
    away_team = away_team[0]

    try:
        commence_time_utc = datetime.fromisoformat(game['commence_time'].rstrip('Z')).replace(tzinfo=pytz.UTC)
        commence_time_local = commence_time_utc.astimezone(pytz.timezone(TIMEZONE))
        time_str = commence_time_local.strftime("%I:%M %p %Z")
        date_str = commence_time_local.strftime("%b %d, %Y")
    except Exception as e:
        logging.warning(f"Failed to parse time: {e}")
        time_str = "Unknown Time"
        date_str = "Unknown Date"

    odds_data, error = parse_odds_and_reasoning(game)
    if error:
        logging.error(error)
        return None

    h2h = odds_data.get("h2h")
    spreads = odds_data.get("spreads")
    totals = odds_data.get("totals")
    player_props = odds_data.get("player_props")

    msg = []
    msg.append("⚾️ *MLB Bet Alert* ⚾️")
    msg.append(f"📅 {date_str}  🕒 {time_str}")
    msg.append(f"🏟 {away_team} @ {home_team}")
    msg.append("")

    # Moneyline bets - filter and rank
    if h2h:
        good_bets = filter_good_bets(h2h)
        if good_bets:
            msg.append("💰 *Moneyline Value Bets*")
            for bet in good_bets:
                name = bet["name"]
                price = bet["price"]
                prob = bet["probability"]
                ev = bet["ev"]
                # Emoji and risk label
                if ev > 0.15 and prob > 0.6:
                    label = "✅ Strong Value"
                    emoji = "🔥"
                elif ev > 0.05:
                    label = "👍 Good Value"
                    emoji = "✅"
                else:
                    label = "⚠️ Moderate Value"
                    emoji = "⚠️"

                msg.append(f"  {emoji} {name}: {price} (EV: {ev:.2%}, Win Prob: {prob:.2%}) — {label}")
        else:
            msg.append("💰 Moneyline: No strong value bets today.")

    # Spreads
    if spreads:
        msg.append("")
        msg.append("📊 *Spread Lines*")
        for spread in spreads:
            name = spread.get("name")
            point = spread.get("point")
            price = spread.get("price")
            if name is None or point is None or price is None:
                continue
            sign = "+" if point > 0 else ""
            msg.append(f"  🏈 {name} {sign}{point}: {price}")

    # Totals
    if totals:
        msg.append("")
        msg.append("🎯 *Totals (Over/Under)*")
        for total in totals:
            name = total.get("name")
            point = total.get("point")
            price = total.get("price")
            if name is None or point is None or price is None:
                continue
            sign = "+" if point > 0 else ""
            msg.append(f"  🎲 {name} {sign}{point}: {price}")

    # Player Props (simple example, improve with more logic)
    if player_props:
        msg.append("")
        msg.append("⭐️ *Player Props Highlights*")
        count = 0
        for prop in player_props:
            name = prop.get("name")
            price = prop.get("price")
            if name and price and count < 3:  # max 3 props per game to avoid spam
                msg.append(f"  🎯 {name}: {price}")
                count += 1

    msg.append("")
    msg.append("🔔 *Bet safely, manage your bankroll!*")
    return "\n".join(msg)

def send_telegram_message(text):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text,
