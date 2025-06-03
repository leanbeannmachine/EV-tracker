import requests

def get_bovada_odds():
    print("Scraping Bovada site for Soccer odds...")

    url = "https://www.bovada.lv/services/sports/event/v2/events/A/description/soccer"
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

    results = []

    for category in data:
        for event in category.get("events", []):
            try:
                teams = event["description"]
                markets = event.get("displayGroups", [])[0].get("markets", [])
                if markets:
                    outcomes = markets[0].get("outcomes", [])
                    if len(outcomes) >= 2:
                        odds = [outcome["price"]["american"] for outcome in outcomes[:2]]
                        results.append({
                            "matchup": teams,
                            "odds": odds
                        })
            except Exception as parse_error:
                print(f"⚠️ Error parsing event: {parse_error}")

    print(f"✅ Scraped {len(results)} soccer games.")
    return results
