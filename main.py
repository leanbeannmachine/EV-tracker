from bovada_scraper import get_bovada_odds
from ev_calculator import find_high_probability_bets
from telegram_alert_bot import send_telegram_message

def run():
    print("Fetching Bovada odds...")
    odds = get_bovada_odds()
    bets = find_high_probability_bets(odds)
    if not bets:
        print("⚠️ No high probability bets found.")
    for bet in bets:
        msg = f"🔥 {bet['team']} to win\nMatchup: {bet['matchup']}\nOdds: {bet['odds']}\nImplied Probability: {bet['implied_prob']}%"
        send_telegram_message(msg)

if __name__ == "__main__":
    run()
