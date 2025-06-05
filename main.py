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
        elif d > 1:
            return round(-100 / (d - 1))
        else:
            return None
    except Exception as e:
        print(f"❌ to_american conversion error: {e}")
        return None

# Filter odds within range (lowered threshold)
def is_in_range(american):
    return american is not None and 100 <= american <= 220

# Pull SportMonks data
from datetime import datetime, timedelta
import requests

def get_sportmonks_matches():
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    url = f"https://api.sportmonks.com/v3/football/fixtures/between/{today}/{tomorrow}"
    params = {
        'api_token': 'pt70HsJAeICOY3nWH8bLDtQFPk4kMDz0PHF9ZvqfFuhseXsk10Xfirbh4pAG',
        'include': 'localTeam,visitorTeam,odds,league'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
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
    print(f"DEBUG: Fetched {len(matches)} matches")

    if not matches:
        msg = "⚠️ No matches found for today or tomorrow. Check back later!"
        print(msg)
        send_telegram_message(msg)
        return

    total_sent = 0

    for match in matches:
        odds_data = match.get('odds', {}).get('data', [])
        print(f"DEBUG: Match {match.get('id')} odds: {[odd.get('value') for odd in odds_data]}")

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
                if am >= 150:
                    highlight = True

        if odds_lines:
            msg_hash = match.get('id')
            if msg_hash in sent_hashes:
                continue
            sent_hashes.add(msg_hash)

            match_str = format_match(match, highlight)
            odds_str = " | ".join(odds_lines)
            flame = "🔥 BEST VALUE PICK!\n" if highlight else "💡 Smart Pick\n"
            full_message = f"{flame}{match_str}\n🎯 {odds_str}"

            print(f"Sending message for match {msg_hash}...")
            try:
                send_telegram_message(full_message)
                print(f"✅ Message sent for match {msg_hash}")
            except Exception as e:
                print(f"❌ Failed to send Telegram message for match {msg_hash}: {e}")

            total_sent += 1
            time.sleep(1)

    if total_sent == 0:
        msg = "😕 No value bets for today or tomorrow. Check back later!"
        print(msg)
        send_telegram_message(msg)
        return
if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
        time.sleep(900)  # wait 15 minutes before next run
