from datetime import datetime, timezone, timedelta
import requests
import telegram

# --- USER CONFIG ---
API_KEY = "183b79e95844e2300faa30f9383890b5"
BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"

# ✅ VALIDATED ACTIVE LEAGUES
LEAGUES = [
    "soccer_brazil_campeonato",
    "soccer_argentina_primera_division",
    "basketball_wnba",
    "basketball_euroleague",
    "tennis_atp"  # Use broader ATP tennis endpoint
]

BOOKMAKER = "bovada"
REGION = "us"
MARKET = "h2h"
THRESHOLD = 3.5  # Minimum value % to send alert

# --- HELPERS ---
def format_american_odds(odds):
    try:
        odds = int(odds)
        return f"+{odds}" if odds > 0 else str(odds)
    except:
        return str(odds)

def implied_prob(odds):
    odds = int(odds)
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def within_target_week(commence_time):
    start = datetime(2025, 6, 4, tzinfo=timezone.utc)
    end = start + timedelta(days=5)
    return start <= commence_time <= end

# --- MAIN LOGIC ---
def get_value_bets():
    messages = []
    for league in LEAGUES:
        url = (
            f"https://api.the-odds-api.com/v4/sports/{league}/odds"
            f"?apiKey={API_KEY}&regions={REGION}&markets={MARKET}&bookmakers={BOOKMAKER}&oddsFormat=american"
        )
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Error fetching odds for {league}: {response.status_code} - {response.text}")
                continue

            data = response.json()
            for match in data:
                home_team = match.get("home_team", "Player 1")
                away_team = match.get("away_team", "Player 2")
                commence_time = datetime.fromisoformat(match["commence
