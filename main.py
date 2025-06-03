from bovada_scraper import get_bovada_odds
from ev_calculator import find_ev_bets
from telegram_alert_bot import send_telegram_message

def main():
    print("Fetching Bovada odds...")
    odds = get_bovada_odds()

    if not odds:
        print("No odds found or scraping failed.")
        return

    print("Finding EV bets...")
    ev_bets = find_ev_bets(odds)

    if not ev_bets:
        print("No +EV bets found.")
        return

    print(f"✅ Found {len(ev_bets)} +EV bets. Sending to Telegram...")
    for bet in ev_bets:
        send_telegram_message(bet)

if __name__ == "__main__":
    main()
