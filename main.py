from bovada_scraper import get_bovada_soccer_odds

def main():
    bets = get_bovada_soccer_odds()
    for bet in bets:
        print(f"{bet['matchup']} | {bet['market']} | Odds: {bet['odds']}")

if __name__ == "__main__":
    main()
