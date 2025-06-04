import requests

SOCCER_MARKET_IDS = [
    "soccer/uefa-champions-league",
    "soccer/england/premier-league",
    "soccer/usa/mls",
    "soccer/international/copa-america",
    "soccer/international/uefa-euro"
]

def get_bovada_odds():
    print("⚽ Fetching Bovada odds for major soccer leagues...")
    base_url = "https://www.bovada.lv/services/sports/event/v2/en-us/markets/"
    results = []

    for market in SOCCER_MARKET_IDS:
        try:
            url = base_url + market
            resp = requests.get(url, timeout=10)
            data = resp.json()

            for group in data:
                for event in group.get("events", []):
                    teams = event["description"]
                    markets = event.get("displayGroups", [])[0].get("markets", [])
                    if markets and len(markets[0].get("outcomes", [])) >= 2:
                        outcome1 = markets[0]["outcomes"][0]
                        outcome2 = markets[0]["outcomes"][1]
                        results.append({
                            "matchup": teams,
                            "odds": [outcome1["price"]["american"], outcome2["price"]["american"]]
                        })

        except Exception as e:
            print(f"❌ Failed to fetch {market}: {e}")

    print(f"✅ Scraped {len(results)} total soccer bets.")
    return results
