import requests
from datetime import datetime
import pytz

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
    teams = game.get('teams', [])
    home_team = game.get('home_team', teams[0])
    away_team = [team for team in teams if team != home_team][0]
    commence_time = datetime.fromisoformat(game['commence_time'][:-1]).astimezone(pytz.timezone('US/Eastern'))
    time_str = commence_time.strftime("%I:%M %p %Z")
    bookmaker = game.get('bookmakers', [])[0]
    moneyline_odds = {outcome['name']: outcome['price'] for outcome in bookmaker['markets'][0]['outcomes']}
    msg = f"MLB Game:\n{away_team} @ {home_team}\nTime: {time_str}\nMoneyline Odds: {moneyline_odds}"
    return msg

if __name__ == "__main__":
    games = fetch_today_games()
    if games:
        print(format_bet(games[0]))
    else:
        print("No games found for today.")
