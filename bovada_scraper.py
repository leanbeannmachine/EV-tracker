import requests
from bs4 import BeautifulSoup

def get_bovada_odds():
    print("Scraping Bovada site for MLB odds...")

    url = "https://www.bovada.lv/sports/baseball/mlb"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    games = soup.select('.market-container')

    results = []

    for game in games:
        teams = game.select('.competitor-name')
        odds = game.select('.bet-price')

        if len(teams) == 2 and len(odds) >= 2:
            team1 = teams[0].text.strip()
            team2 = teams[1].text.strip()
            odds1 = odds[0].text.strip()
            odds2 = odds[1].text.strip()

            results.append({
                "matchup": f"{team1} vs {team2}",
                "odds": [odds1, odds2]
            })

    print(f"✅ Scraped {len(results)} MLB games.")
    return results
