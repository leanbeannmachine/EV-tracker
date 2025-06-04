import requests
import os

# Put your OddsAPI key here or set as env var
API_KEY = "183b79e95844e2300faa30f9383890b5"

# Your Telegram bot token and chat ID here
BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"
# List of soccer leagues to fetch — change or add more IDs from OddsAPI docs
LEAGUES = [
    "soccer-australia-brisbane-premier-league",
    "soccer-australia-queensland-premier-league",
    "soccer-usa-usl-league-two",
    "soccer-usa-usl-w-league",
    "soccer-usa-wpsl",
    "soccer-international-friendlies-women",
    "basketball-wnba"
]

def fetch_odds(league_key):
    url = f"https://api.the-odds-api.com/v4/sports/{league_key}/odds/?apiKey={API_KEY}&regions=us&markets=h2h&oddsFormat=american"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Failed to fetch odds for {league_key}: {e}")
        return []

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=data, timeout=5)
        if response.status_code != 200:
            print(f"Failed to send message: {response.text}")
    except Exception as e:
        print(f"Error sending telegram message: {e}")

def find_value_bets(games, min_odds=150):  # American odds > +150 means ~2.5 decimal odds
    value_bets = []
    for game in games:
        home = game.get("home_team")
        away = game.get("away_team")
        for bookmaker in game.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] == "h2h":
                    for outcome in market["outcomes"]:
                        price = outcome.get("price")
                        if price is None:
                            continue
                        # American odds to check if greater than min_odds (e.g. +150)
                        if price > min_odds:
                            bet = {
                                "matchup": f"{home} vs {away}",
                                "team": outcome["name"],
                                "odds": price,
                                "bookmaker": bookmaker.get("title", "Unknown")
                            }
                            value_bets.append(bet)
    return value_bets

def main():
    all_value_bets = []
    for league in SOCCER_LEAGUES:
        print(f"Fetching odds for {league}...")
        games = fetch_odds(league)
        if not games:
            print(f"No data for {league}.")
            continue
        value_bets = find_value_bets(games)
        all_value_bets.extend(value_bets)

    if not all_value_bets:
        print("No value bets found.")
        return

    for bet in all_value_bets:
        message = (f"*Match:* {bet['matchup']}\n"
                   f"*Team:* {bet['team']}\n"
                   f"*Odds:* {bet['odds']}\n"
                   f"*Bookmaker:* {bet['bookmaker']}")
        print(message)
        send_telegram_message(message)

if __name__ == "__main__":
    main()
