import requests
import datetime
import time
import telegram

# API Keys and Bot Config
SPORTMONKS_API_KEY = "pt70HsJAeICOY3nWH8bLDtQFPk4kMDz0PHF9ZvqfFuhseXsk10Xfirbh4pAG"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Emojis
TEAM_EMOJIS = {
    "Arsenal": "🛡️", "Chelsea": "🔵", "Liverpool": "🟥", "Manchester United": "🔴",
    "Manchester City": "🔷", "Real Madrid": "⚪", "Barcelona": "🔵", "Bayern Munich": "🔴",
    "Juventus": "⚫", "PSG": "🔴", "AC Milan": "⚫", "Inter Milan": "🔵", "Tottenham": "⚪",
}
LEAGUE_EMOJIS = {
    8: "🏆", 72: "🇳🇱", 82: "🇩🇪", 301: "🇫🇷", 384: "🇮🇹", 564: "🇪🇸", 501: "🇺🇸"
}

# Convert decimal odds to American odds
def to_american(decimal):
    try:
        d = float(decimal)
        if d >= 2.0:
            return round((d - 1) * 100)
        else:
            return round(-100 / (d - 1))
    except:
        return None

# Filter odds within range
def is_in_range(american):
    return american is not None and 110 <= american <= 190

# Pull SportMonks data
def get_sportmonks_matches():
    today = datetime.datetime.utcnow().date()
    tomorrow = today + datetime.timedelta(days=1)
    url = f"https://api.sportmonks.com/v3/football/fixtures/date/{today},{tomorrow}?api_token={SPORTMONKS_API_KEY}&include=localTeam,visitorTeam,odds,league"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json().get('data', [])
    except Exception as e:
        print(f"❌ Error fetching SportMonks data: {e}")
        return []

# Format individual match
def format_match(match, highlight=False):
    home = match.get('localTeam', {}).get('data', {}).get('name', 'Unknown')
    away = match.get('visitorTeam', {}).get('data', {}).get('name', 'Unknown')
    league = match.get('league', {}).get('data', {}).get('id', None)
    league_emoji = LEAGUE_EMOJIS.get(league, "⚽")
    home_emoji = TEAM_EMOJIS.get(home, "⚽")
    away_emoji = TEAM_EMOJIS.get(away, "⚽")

    time_utc = match.get('starting_at', {}).get('date_time_utc')
    try:
        match_time = datetime.datetime.strptime(time_utc, "%Y-%m-%d %H:%M:%S")
    except:
        match_time = datetime.datetime.utcnow()

    match_time_str = match_time.strftime("%Y-%m-%d %H:%M UTC")
    bold = "<b>" if highlight else ""
    close = "</b>" if highlight else ""

    return f"{league_emoji} {bold}{home_emoji} {home} vs {away_emoji} {away}{close}\n🕒 {match_time_str}"

# Send message to Telegram
def send_telegram_message(text):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode=telegram.ParseMode.HTML)
        print("✅ Sent to Telegram")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

# Main logic
def main():
    sent_hashes = set()
    matches = get_sportmonks_matches()
    total_sent = 0

    for match in matches:
        odds_data = match.get('odds', {}).get('data', [])
        highlight = False
        odds_lines = []

        for odd in odds_data:
            label = odd.get('label', '').lower()
            val = odd.get('value', None)
            if not val or label not in ['1', '2', 'x']:
                continue
            am = to_american(val)
            if is_in_range(am):
                odds_lines.append(f"{label.upper()}: +{am}")
                if am >= 160:
                    highlight = True

        if odds_lines:
            msg_hash = match['id']
            if msg_hash in sent_hashes:
                continue
            sent_hashes.add(msg_hash)

            match_str = format_match(match, highlight)
            odds_str = " | ".join(odds_lines)
            flame = "🔥 BEST VALUE PICK!\n" if highlight else "💡 Smart Pick\n"
            full_message = f"{flame}{match_str}\n🎯 {odds_str}"

            send_telegram_message(full_message)
            total_sent += 1
            time.sleep(1)

    if total_sent == 0:
        send_telegram_message("😕 No value bets for today or tomorrow. Check back later!")

if __name__ == "__main__":
    main()
