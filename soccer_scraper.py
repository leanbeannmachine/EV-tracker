import requests

API_KEY = "183b79e95844e2300faa30f9383890b5"
BASE_URL = "https://api.the-odds-api.com/v4/sports"
SPORT = "soccer"
REGIONS = "us"  # or 'eu'/'uk'/'au' depending on your focus
MARKETS = "h2h,spreads,totals"
LEAGUES = [
    "australia_queensland_premier_league",
    "australia_brisbane_premier_league",
    "usa_usl_league_two",
    "usa_usl_w_league",
    "usa_wpsl",
    "basketball_wnba",
    "soccer_friendly_women"
]

for league in LEAGUES:
    url = f"{BASE_URL}/{league}/odds/?apiKey={API_KEY}&regions={REGIONS}&markets={MARKETS}&oddsFormat=decimal"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch for {league}: {response.status_code} - {response.text}")
        continue

    matches = response.json()
    print(f"\n📘 League: {league} | Matches Found: {len(matches)}")
    for match in matches:
        home = match.get("home_team", "Unknown")
        away = match.get("away_team", "Unknown")
        commence = match.get("commence_time", "N/A")
        print(f"🏟 {home} vs {away} @ {commence}")

        for bookmaker in match.get("bookmakers", []):
            name = bookmaker.get("title", "N/A")
            for market in bookmaker.get("markets", []):
                if market["key"] == "h2h":
                    print(f"📚 Bookmaker: {name}")
                    for outcome in market["outcomes"]:
                        print(f"  - {outcome['name']}: {outcome['price']}")
