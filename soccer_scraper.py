import requests
import time

def get_soccer_bets():
    print("🔍 Fetching all soccer categories...")

    index_url = "https://www.bovada.lv/services/sports/menu/events/A/description"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(index_url, headers=headers, timeout=15)
        print("🟢 Response Status:", response.status_code)
        print("🟢 Response Sample:", response.text[:300])  # Preview the first 300 characters
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Failed to load categories: {e}")
        return []

    bets = []

    for sport in data:
        if sport["description"].lower() == "soccer":
            for group in sport.get("children", []):
                for league in group.get("children", []):
                    link = league.get("link")
                    if link:
                        league_url = f"https://www.bovada.lv/services/sports/event/v2/events/A{link}"
                        print(f"📡 Scraping: {league_url}")
                        try:
                            league_resp = requests.get(league_url, headers=headers, timeout=10)
                            league_resp.raise_for_status()
                            events_data = league_resp.json()
                        except Exception as e:
                            print(f"⚠️ Failed to scrape {league_url}: {e}")
                            continue

                        for ev_group in events_data:
                            for event in ev_group.get("events", []):
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

    print(f"✅ Total soccer bets scraped: {len(bets)}")
    return bets
