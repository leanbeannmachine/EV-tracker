from bovada_scraper import get_bovada_odds
from ev_calculator import find_ev_bets
from telegram_alert_bot import send_telegram_message

def main():
    print("Fetching Bovada odds...")
    odds = get_bovada_odds()
    bets = find_ev_bets(odds)
    for bet in bets:
        send_telegram_message(bet)
        print(f"Sent alert for: {bet['match']} — {bet['bet']}")

if __name__ == "__main__":
    main()
