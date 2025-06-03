import requests

def get_bovada_odds():
    print("Fetching Bovada odds...")

    url = "https://www.bovada.lv/services/sports/event/v2/events"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return []

    try:
        sports_data = resp.json()
    except Exception as e:
        print(f"Bovada response preview (first 300 chars):\n{resp.text[:300]}")
        print(f"Failed to parse Bovada data: {e}")
        return []

    odds_list = []
    for sport in sports_data:
        sport_name = sport.get("displayGroup", "Unknown Sport")
        events = sport.get("events", [])

        for event in events:
            league = event.get("group", "Unknown League")

            teams = event.get("competitors", [])
            if len(teams) != 2:
                continue

            team1 = teams[0]["name"]
            team2 = teams[1]["name"]
            markets = event.get("displayGroups", [])

            for market in markets:
                if market["description"] != "Game Lines":
                    continue
                for outcome in market["markets"][0]["outcomes"]:
                    odds_entry = {
                        "sport": sport_name,
                        "league": league,
                        "team1": team1,
                        "team2": team2,
                        "description": outcome["description"],
                        "price": outcome["price"]["decimal"]
                    }
                    odds_list.append(odds_entry)

    print(f"✅ Found {len(odds_list)} bets across all sports.")
    return odds_list
