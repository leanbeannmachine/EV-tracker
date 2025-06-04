import requests
import os

API_KEY = "183b79e95844e2300faa30f9383890b5"

def fetch_odds():
    url = "https://api.the-odds-api.com/v4/sports/soccer/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "eu",       # Use 'us' for American books or 'uk', 'au', etc.
        "markets": "h2h",      # Moneyline bets (head-to-head)
        "oddsFormat": "decimal"
    }

    try:
        print("🔎 Fetching odds...")
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"❌ Failed to fetch odds: {e}")
        return []

def display_bets(bets):
    if not bets:
        print("⚠️ No bets found.")
        return

    print(f"✅ Found {len(bets)} matches.\n")

    for event in bets:
        try:
            teams = event['teams']
            site = event['bookmakers'][0]  # Use first available sportsbook
            odds = site['markets'][0]['outcomes']
            print(f"{teams[0]} vs {teams[1]}")
            for outcome in odds:
                print(f"  {outcome['name']}: {outcome['price']}")
            print("-" * 40)
        except (IndexError, KeyError):
            continue

def main():
    odds_data = fetch_odds()
    display_bets(odds_data)

if __name__ == "__main__":
    main()
