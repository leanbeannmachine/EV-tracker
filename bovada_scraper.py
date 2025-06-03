import requests

def get_bovada_odds():
    print("⚽ Fetching Bovada Soccer odds via JSON...")

    url = "https://www.bovada.lv/services/sports/event/v2/events/A/description/soccer"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return []

    try:
        data = response.json()
    except Exception as e:
        print(f"❌ Failed to parse Bovada JSON: {e}")
        return []

    events = data[0].get("events", [])
    results = []

    for event in events:
        try:
            teams = event["competitors"]
            team1 = teams[0]["name"]
            team2 = teams[1]["name"]

            outcomes = event["displayGroups"][0]["markets"][0]["outcomes"]
            odds = [o["price"]["american"] for o in outcomes]

            results.append({
                "matchup": f"{team1} vs {team2}",
                "odds": odds
            })
        except Exception as e:
            print(f"⚠️ Error parsing event: {e}")
            continue

    print(f"✅ Scraped {len(results)} soccer games.")
    return results
