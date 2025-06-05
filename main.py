import requests
import datetime
import time
import telegram

# Your API keys here
SPORTMONKS_API_KEY = "UGsOsScp6nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
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

def adjust_american_odds(odds_str):
    """
    Adjust American odds down by about 5 points:
    - For positive odds: subtract 5 (min +100)
    - For negative odds: add 5 (max -100)
    """
    try:
        odds = int(odds_str)
        if odds > 0:
            adjusted = odds - 5
            if adjusted < 100:
                adjusted = 100
        else:
            adjusted = odds + 5
            if adjusted > -100:
                adjusted = -100
        if adjusted > 0:
            return f"+{adjusted}"
        else:
            return str(adjusted)
    except Exception:
        return odds_str

def format_odds(odds_data):
    odds_str = []
    for odd in odds_data:
        label = odd.get('label', 'Bet')
        value = odd.get('value', '')
        adjusted_value = adjust_american_odds(value)
        odds_str.append(f"{label}: {adjusted_value}")
    return " | ".join(odds_str)

def format_match(match):
    home = match.get('localTeam', {}).get('data', {}).get('name', 'Unknown')
    away = match.get('visitorTeam', {}).get('data', {}).get('name', 'Unknown')

    home_emoji = TEAM_EMOJIS.get(home, "⚽")
    away_emoji = TEAM_EMOJIS.get(away, "⚽")

    time_utc = match.get('starting_at', {}).get('date_time_utc') or match.get('starting_at')
    if isinstance(time_utc, str):
        try:
            match_time = datetime.datetime.strptime(time_utc, "%Y-%m-%d %H:%M:%S")
        except Exception:
            match_time = datetime.datetime.utcnow()
    else:
        match_time = datetime.datetime.utcnow()
    match_time_str = match_time.strftime("%Y-%m-%d %H:%M UTC")

    league_id = None
    if 'league' in match and match['league']:
        league_id = match['league'].get('id')
    elif 'league_id' in match:
        league_id = match['league_id']
    league_emoji = LEAGUE_EMOJIS.get(league_id, "⚽")

    return f"{league_emoji} <b>{home_emoji} {home} vs {away_emoji} {away}</b>\n🕒 {match_time_str}"

def send_telegram_message(text):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode=telegram.ParseMode.HTML)
        print("Sent message to Telegram")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def main():
    sportmonks_matches = get_sportmonks_matches()
    messages = []

    for match in sportmonks_matches:
        msg = format_match(match)
        odds_data = match.get('odds', {}).get('data', [])
        if odds_data:
            odds_str = format_odds(odds_data)
            msg += "\n🎯 " + odds_str
        messages.append(msg)

    if not messages:
        send_telegram_message("No value bets for today or next two days, check back soon!")
    else:
        for message in messages:
            send_telegram_message(message)
            time.sleep(1)

if __name__ == "__main__":
    main()
