import requests
import time
import logging
from datetime import datetime
import pytz

# Config - Insert your keys here
ODDS_API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

logging.basicConfig(level=logging.INFO)

sent_bets = set()

def fetch_today_games():
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "dateFormat": "iso",
        "oddsFormat": "american"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    games = response.json()

    today = datetime.now(pytz.UTC).date()
    todays_games = [game for game in games if datetime.fromisoformat(game['commence_time'][:-1]).date() == today]
    return todays_games

def format_bet(game):
    try:
        teams = game.get('teams', [])
        if len(teams) < 2:
            raise ValueError("Not enough teams info")

        home_team = game.get('home_team', teams[0])
        away_team = [team for team in teams if team != home_team][0]

        commence_time = datetime.fromisoformat(game['commence_time'][:-1]).astimezone(pytz.timezone('US/Eastern'))
        time_str = commence_time.strftime("%I:%M %p %Z")

        bookmakers = game.get('bookmakers', [])
        if not bookmakers:
            return None

        bookmaker = bookmakers[0]
        markets = bookmaker.get('markets', [])
        if not markets:
            return None

        moneyline_odds = {}
        spread_odds = {}
        total_odds = {}

        for market in markets:
            if market['key'] == 'h2h':
                for outcome in market['outcomes']:
                    moneyline_odds[outcome['name']] = outcome['price']
            elif market['key'] == 'spreads':
                for outcome in market['outcomes']:
                    spread_odds[outcome['name']] = outcome.get('point', "N/A")
            elif market['key'] == 'totals':
                for outcome in market['outcomes']:
                    total_odds[outcome['name']] = outcome['price']

        msg = (
            f"📊 *MLB Bet Preview*\n"
            f"🕒 {time_str}\n"
            f"⚔️ {away_team} @ {home_team}\n"
            f"🏦 {bookmaker['title']}\n\n"
            f"💰 *Moneyline:*\n"
            f"- {away_team}: {moneyline_odds.get(away_team, 'N/A')}\n"
            f"- {home_team}: {moneyline_odds.get(home_team, 'N/A')}\n\n"
            f"🟩 *Spread:*\n"
            f"- {away_team}: {spread_odds.get(away_team, 'N/A')}\n"
            f"- {home_team}: {spread_odds.get(home_team, 'N/A')}\n\n"
            f"📈 *Total:*\n"
            f"- Over: {total_odds.get('Over', 'N/A')}\n"
            f"- Under: {total_odds.get('Under', 'N/A')}\n"
        )
        return msg
    except Exception as e:
        logging.error(f"Error formatting bet message: {e}")
        return None

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        logging.info("Message sent successfully")
    except Exception as e:
        logging.error(f"Failed to send message: {e}")

def send_bets():
    games = fetch_today_games()
    count = 0
    max_bets = 10

    for game in games:
        bet_msg = format_bet(game)
        if bet_msg and bet_msg not in sent_bets:
            send_telegram_message(bet_msg)
            sent_bets.add(bet_msg)
            count += 1
            if count >= max_bets:
                break

    logging.info(f"Cycle complete: sent {count} bets.")

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
