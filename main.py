from soccer_scraper import get_soccer_bets
import requests

# Your Telegram Bot Config
BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"

def send_to_telegram(message: str):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {'chat_id': CHAT_ID, 'text': message}
    requests.post(url, data=data)

print("🔎 Fetching odds...")
bets = get_soccer_bets()

if not bets:
    print("⚠️ No bets found.")
    send_to_telegram("⚠️ No value bets found right now.")
else:
    print(f"✅ Total Matches Found: {len(bets)}\n")
    for bet in bets:
        league = bet.get("league", "Unknown League")
        team1 = bet.get("team1", "TBD")
        team2 = bet.get("team2", "TBD")
        bookmaker = bet.get("bookmaker", "N/A")
        odds = bet.get("odds", "N/A")
        start = bet.get("commence_time", "TBD")

        message = (
            f"⚽ *{team1} vs {team2}*\n"
            f"📅 Start: {start}\n"
            f"🏟 League: {league}\n"
            f"📚 Bookmaker: {bookmaker}\n"
            f"💰 Odds: {odds}"
        )
        print(message)
        send_to_telegram(message)
