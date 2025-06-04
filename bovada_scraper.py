import requests

def get_bovada_odds():
    print("⚽ Fetching Bovada odds (all soccer leagues)...")

    url = "https://www.bovada.lv/services/sports/event/v2/en-us/soccer"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return []

    print(f"✅ Response received. Previewing first item...")
    if not data or not data[0].get("events"):
        print("⚠️ No events found in Bovada data.")
        return []

    results = []
    for group in data:
        for event in group.get("events", []):
            matchup = event["description"]
            display_groups = event.get("displayGroups", [])

            if not display_groups:
                continue

            markets = display_groups[0].get("markets", [])
            if not markets or len(markets[0].get("outcomes", [])) < 2:
                continue

            try:
                team1 = markets[0]["outcomes"][0]
                team2 = markets[0]["outcomes"][1]

                results.append({
                    "matchup": matchup,
                    "odds": [team1["price"]["american"], team2["price"]["american"]]
                })
            except Exception as inner_e:
                print(f"⚠️ Skipped malformed event: {inner_e}")

    print(f"✅ Scraped {len(results)} soccer games.")
    return results
