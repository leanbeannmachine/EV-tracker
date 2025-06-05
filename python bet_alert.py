import requests
import pytz
from datetime import datetime, timedelta
import time

# Your API keys here
SPORTMONKS_API_KEY = "pt70HsJAeICOY3nWH8bLDtQFPk4kMDz0PHF9ZvqfFuhseXsk10Xfirbh4pAG"
ODDSAPI_KEY = "7b5d540e73c8790a95b84d3713e1a572"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

LOCAL_TZ = pytz.timezone("US/Eastern")

def to_american(decimal_odds):
    decimal_odds = float(decimal_odds)
    if decimal_odds >= 2.0:
        return f"+{int((decimal_odds - 1) * 100)}"
    else:
        return f"{int(-100 / (decimal_odds - 1))}"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Telegram send error: {e}")

def get_sportmonks_bets(api_key, date_str=None):
    if not date_str:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
    url = f"https://api.sportmonks.com/v3/football/fixtures/date/{date_str}"
    params = {
        "api_token": api_key,
        "include": "localTeam,visitorTeam,odds,league"
    }
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        fixtures = data.get("data", [])
    except Exception as e:
        print(f"❌ Error fetching SportMonks data: {e}")
        return []

    bets = []
    for fixture in fixtures:
        odds = fixture.get("odds", {}).get("data", [])
        local_team = fixture.get("localTeam", {}).get("data", {}).get("name", "Unknown")
        visitor_team = fixture.get("visitorTeam", {}).get("data", {}).get("name", "Unknown")
        start_time = fixture.get("starting_at")
        if not odds or not start_time:
            continue
        for odd in odds:
            if odd.get("type") != "h2h":
                continue
            outcomes = odd.get("outcomes", [])
            for outcome in outcomes:
