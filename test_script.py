import requests
from datetime import datetime
import pytz
import logging

logging.basicConfig(level=logging.INFO)

ODDS_API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"

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
            logging.warning(f"Skipping game due to insufficient teams info: {game.get('id', 'unknown')}")
            return None

        home_team = game.get('home_team', teams[0])
        away_team = [team for team in teams if team != home_team][0]

        commence_time = datetime.fromisoformat(game['commence_time'][:-1]).astimezone(pytz.timezone('US/Eastern'))
        time_str = commence_time.strftime("%I:%M %p %Z")

        bookmaker = game.get('bookmakers', [])
        if not bookmaker:
            logging.warning(f"No bookmakers for game {game.get('id', 'unknown')}")
            return None
        bookmaker = bookmaker[0]

        moneyline_odds = {outcome['name']: outcome['price'] for outcome in bookmaker.get('markets', [])[0].get('outcomes', [])}

        msg = (
            f"MLB Game:\n"
            f"{away_team} @ {home_team}\n"
            f"Time: {time_str}\n"
            f"Bookmaker: {bookmaker.get('title', 'Unknown')}\n"
            f"Moneyline Odds: {moneyline_odds}"
        )
        return msg
    except Exception as e:
        logging.error(f"Error formatting bet message: {e}")
        return None

if __name__ == "__main__":
    games = fetch_today_games()
    if games:
        bet_message = format_bet(games[0])
        if bet_message:
            print(bet_message)
        else:
            print("Could not format bet message for the first game.")
    else:
        print("No games found for today.")
