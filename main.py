import requests
import datetime
import time
import telegram

# Your API keys here
SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Emoji dictionaries
TEAM_EMOJIS = {
    "Arsenal": "🛡️",
    "Chelsea": "🔵",
    "Liverpool": "🟥",
    "Manchester United": "🔴",
    "Manchester City": "🔵",
    "Real Madrid": "⚪",
    "Barcelona": "🔵",
    "Bayern Munich": "🔴",
    # Add more teams as needed
}

LEAGUE_EMOJIS = {
    8: "🏆",    # Premier League
    72: "⚽",   # Eredivisie
    82: "🥨",   # Bundesliga
    301: "🥖",  # Ligue 1
    384: "🍕",  # Serie A
    564: "🎉",  # La Liga
}

def get_oddsapi_matches():
    url = f"https://api.the-odds-api.com/v4/sports/soccer_epl/odds?apiKey={ODDS_API_KEY}&regions=us&markets=h2h,spreads,totals&oddsFormat=american"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching OddsAPI data: {e}")
        return []

def get_sportmonks_matches():
    url = f"https://api.sportmonks.com/v3/football/fixtures?api_token={SPORTMONKS_API_KEY}&include=localTeam,visitorTeam,odds"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except Exception as e:
        print(f"Error fetching SportMonks data: {e}")
        return []

def format_match(match):
    home = match['home_team']['name'] if 'home_team' in match else match.get('localTeam', {}).get('data', {}).get('name', 'Unknown')
    away = match['away_team']['name'] if 'away_team' in match else match.get('visitorTeam', {}).get('data', {}).get('name', 'Unknown')

    # Add emojis for teams if found, else default soccer ball
    home_emoji = TEAM_EMOJIS.get(home, "⚽")
    away_emoji = TEAM_EMOJIS.get(away, "⚽")

    # DateTime parsing depending on source
    time_utc = match.get('starting_at', {}).get('date_time_utc') or match.get('time', {}).get('starting_at') or match.get('starting_at')
    if not time_utc:
        time_utc = match.get('time', {}).get('starting_at') or match.get('starting_at')
    if isinstance(time_utc, str):
        try:
            match_time = datetime.datetime.strptime(time_utc, "%Y-%m-%d %H:%M:%S")
        except Exception:
            match_time = datetime.datetime.utcnow()
    else:
        match_time = datetime.datetime.utcnow()
    match_time_str = match_time.strftime("%Y-%m-%d %H:%M UTC")

    # League emoji fallback
    league_id = None
    if 'league' in match and match['league']:
        league_id = match['league'].get('id')
    elif 'league_id' in match:
        league_id = match['league_id']
    league_emoji = LEAGUE_EMOJIS.get(league_id, "⚽")

    return f"{league_emoji} <b>{home_emoji} {home} vs {away_emoji} {away}</b>\n🕒 {match_time_str}"

def format_bet(odds):
    # Example format for American odds and bet types
    if odds is None:
        return ""
    line = ""
    if 'point' in odds:
        line += f"Line: {odds['point']} "
    if 'odds' in odds:
        line += f"Odds: {odds['odds']} "
    return line.strip()

def send_telegram_message(text):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode=telegram.ParseMode.HTML)
        print("Sent message to Telegram")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def main():
    oddsapi_matches = get_oddsapi_matches()
    sportmonks_matches = get_sportmonks_matches()

    messages = []

    # Process OddsAPI matches
    for match in oddsapi_matches:
        msg = format_match(match)
        # Include odds here if you want, simplified example:
        if 'bookmakers' in match and match['bookmakers']:
            best_bookmaker = match['bookmakers'][0]
            markets = best_bookmaker.get('markets', [])
            for market in markets:
                if market['key'] == 'h2h':
                    odds_str = " | ".join([f"{outcome['name']}: {outcome['price']}" for outcome in market['outcomes']])
                    msg += f"\n🎯 {odds_str}"
        messages.append(msg)

    # Process SportMonks matches
    for match in sportmonks_matches:
        msg = format_match(match)
        # Add odds from SportMonks if present
        odds_data = match.get('odds', {}).get('data', [])
        if odds_data:
            odds_str = []
            for odd in odds_data:
                label = odd.get('label', 'Bet')
                value = odd.get('value', '')
                odds_str.append(f"{label}: {value}")
            msg += "\n🎯 " + " | ".join(odds_str)
        messages.append(msg)

    # Send each message to Telegram with a small pause to avoid flooding
    for message in messages:
        send_telegram_message(message)
        time.sleep(1)

if __name__ == "__main__":
    main()
