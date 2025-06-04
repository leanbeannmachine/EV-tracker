import requests

# Set a hard cap for how many bets you want to process (e.g. 100 max)
MAX_BETS = 50

def get_bovada_odds():
    print("📡 Fetching capped odds from Bovada...")

    url = "https://www.bovada.lv/services/sports/event/v2/en-us/featured"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return []

    events = []
    for category in data:
        for sport in category.get('events', []):
            title = sport.get("description", "Unknown")
            teams = [comp.get("name", "Unknown") for comp in sport.get("competitors", [])]
            markets = sport.get("displayGroups", [])

            for group in markets:
                for market in group.get("markets", []):
                    outcomes = market.get("outcomes", [])
                    if len(outcomes) >= 2:
                        odds_pair = [out.get("price", {}).get("american", "N/A") for out in outcomes]
                        events.append({
                            "matchup": f"{' vs '.join(teams)}",
                            "market": market.get("description", "Unknown Market"),
                            "odds": odds_pair
                        })
                        if len(events) >= MAX_BETS:
                            print(f"🛑 Reached data cap of {MAX_BETS} bets.")
                            return events

    print(f"✅ Scraped {len(events)} bets from Bovada.")
    return events
