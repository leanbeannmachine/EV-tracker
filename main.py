from soccer_scraper import get_soccer_bets
from telegram_alert_bot import send_telegram_message

def run():
    bets = get_soccer_bets()
    if not bets:
        print("No bets found.")
        return
    for bet in bets[:10]:  # Limit to avoid spam
        send_telegram_message(bet)

if __name__ == "__main__":
    run()
