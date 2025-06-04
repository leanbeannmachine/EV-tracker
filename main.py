from soccer_scraper import get_soccer_bets

if __name__ == "__main__":
    bets = get_soccer_bets()
    if bets:
        for bet in bets:
            print(f"{bet['matchup']} | {bet['bookmaker']} | {bet['odds']}")
    else:
        print("⚠️ No bets found.")
