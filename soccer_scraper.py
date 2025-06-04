import requests

def get_soccer_bets():
    api_key = "183b79e95844e2300faa30f9383890b5"
    
    url = "https://api.the-odds-api.com/v4/sports/soccer/odds"

    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "decimal",
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return []

    # Log all available leagues and match info
    leagues = set()
    for match in data:
        if "league" in match:
            leagues.add(match["league"])
        print("––––––––––––––––––––––––")
        print("🏟 Match:", match.get("teams"))
        print("📅 Commence Time:", match.get("commence_time"))
        print("📘 League (if available):", match.get("league", "Unknown"))

    print(f"\n📋 Unique Leagues Found ({len(leagues)}):")
    for l in leagues:
        print(f"  - {l}")

    return data  # Return all data for now, without filtering
