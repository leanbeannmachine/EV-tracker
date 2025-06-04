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

    # ✅ Leagues to include
    desired_leagues = [
        "Brisbane Premier League",
        "Queensland Premier League",
        "USL League Two",
        "USL W League",
        "WPSL",
        "Friendlies Women",
        "WNBA"
    ]

    filtered_bets = []
    for match in data:
        league = match.get("league", "")
        if any(l.lower() in league.lower() for l in desired_leagues):
            filtered_bets.append(match)

    return filtered_bets
