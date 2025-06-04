import requests

def get_soccer_bets():
    print("Fetching soccer bets...")

    url = "https://www.bovada.lv/services/sports/event/v2/events/A/description/soccer"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return []

    bets = []
    for group in data:
        for event in group.get("events", []):
            teams = [comp["name"] for comp in event.get("competitors", [])]
            markets = event.get("displayGroups", [])[0].get("markets", []) if event.get("displayGroups") else []

            for market in markets:
                if market["description"] == "Moneyline":
                    outcomes = market.get("outcomes", [])
                    if len(outcomes) >= 2:
                        odds = [(o["description"], o["price"]["american"]) for o in outcomes]
                        bet_info = f"{' vs '.join(teams)}\n" + '\n'.join([f"{desc}: {price}" for desc, price in odds])
                        bets.append(bet_info)
                    break

    print(f"✅ Scraped {len(bets)} soccer games.")
    return bets
