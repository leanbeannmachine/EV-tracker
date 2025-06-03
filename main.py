from bovada_scraper import get_odds
from ev_calculator import find_ev_bets
from telegram_alert_bot import send_telegram_message

def run():
    odds = get_odds()
    bets = find_ev_bets(odds)
    for bet in bets:
        send_telegram_message(bet)

if __name__ == "__main__":
    run()