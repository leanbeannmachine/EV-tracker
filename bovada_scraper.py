import requests

def get_bovada_odds():
    print("🟡 Connecting to Bovada API...")
    url = "https://www.bovada.lv/services/sports/event/v2/us/en"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; EVTracker/1.0)"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()

        mlb_games = []

        # Loop through each category (sport)
        for category in data:
            events = category.get("events", [])
            for event in events:
                sport_desc = event.get("sport", {}).get("description", "").lower()
                league_desc = event.get("league", {}).get("description", "").lower()

                # Check if MLB or Major League Baseball in league description
                if "mlb" in league_desc or "major league baseball" in league_desc:
                    mlb_games.append(event)

        print(f"✅ Successfully scraped {len(mlb_games)} MLB games.")
        return mlb_games

    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP request failed: {e}")
    except ValueError as e:
        print(f"❌ JSON decoding failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    return []
