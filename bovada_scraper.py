import requests
from bs4 import BeautifulSoup

# 🎯 Define the soccer leagues you want to include
TARGET_LEAGUES = [
    "UEFA U21",
    "International - U21",
    "UEFA Nations League",
    "Copa America",
    "CONCACAF Nations League",
    "Major League Soccer",
    "Brazil - Serie A",
    "Argentina - Liga Profesional",
    "Sweden - Allsvenskan",
    "Norway - Eliteserien",
    "Japan - J1 League",
    "South Korea - K League 1"
]

def get_bovada_odds():
    print("Scraping Bovada for filtered soccer leagues...")

    url = "https://www.bovada.lv/sports/soccer"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
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
        league_tag = game.find_previous("h4")
        league_name = league_tag.text.strip() if league_tag else "Unknown League"

        if not any(target.lower() in league_name.lower() for target in TARGET_LEAGUES):
            continue  # Skip leagues not in your list

        teams = game.select('.competitor-name')
        odds = game.select('.bet-price')

        if len(teams) == 2 and len(odds) >= 2:
            try:
                team1 = teams[0].text.strip()
                team2 = teams[1].text.strip()
                odds1 = odds[0].text.strip()
                odds2 = odds[1].text.strip()

                results.append({
                    "league": league_name,
                    "matchup": f"{team1} vs {team2}",
                    "odds": [odds1, odds2]
                })
            except IndexError:
                continue  # Skip broken entries

    print(f"✅ Scraped {len(results)} games from target leagues.")
    return results
