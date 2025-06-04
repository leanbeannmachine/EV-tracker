import requests

def get_soccer_bets():
    api_key = "183b79e95844e2300faa30f9383890b5"

    url = "https://api.the-odds-api.com/v4/sports/soccer/odds"
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return []

    print("\n📊 Logging all received matches:\n")

    for match in data:
        teams = match.get("teams", ["Unknown", "Unknown"])
        commence = match.get("commence_time", "Unknown time")
        league = match.get("league", "Unknown league")
        bookmakers = match.get("bookmakers", [])

        print("––––––––––––––––––––––––")
        print(f"🏟 Match: {teams[0]} vs {teams[1]}")
        print(f"📅 Commence Time: {commence}")
        print(f"📘 League: {league}")
        print(f"📚 Bookmakers Available: {len(bookmakers)}")

    print(f"\n✅ Total Matches Found: {len(data)}")
    return data
