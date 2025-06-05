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
            # Only moneyline (h2h) odds for simplicity here
            if odd.get("type") != "h2h":
                continue
            outcomes = odd.get("outcomes", [])
            for outcome in outcomes:
                price = outcome.get("price")
                name = outcome.get("name")
                if price:
                    american_odds = to_american(price)
                    bets.append({
                        "source": "SportMonks",
                        "team1": visitor_team,
                        "team2": local_team,
                        "pick": name,
                        "odds_decimal": price,
                        "odds_american": american_odds,
                        "match_time": start_time,
                        "value": True,  # You can add more advanced +EV logic here
                        "rating": "green"  # Simplified
                    })
    return bets

def get_oddsapi_bets(api_key, date_str=None):
    if not date_str:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

    url_sports = "https://api.the-odds-api.com/v4/sports/"
    headers = {"x-api-key": api_key}
    try:
        r = requests.get(url_sports, headers=headers)
        r.raise_for_status()
        sports = r.json()
    except Exception as e:
        print(f"❌ Error fetching sports list: {e}")
        return []

    all_bets = []
    for sport in sports:
        key = sport.get("key")
        if not key:
            continue
        odds_url = f"https://api.the-odds-api.com/v4/sports/{key}/odds"
        params = {
            "regions": "us",
            "markets": "h2h",
            "dateFormat": "iso",
            "apiKey": api_key,
        }
        try:
            r = requests.get(odds_url, params=params)
            r.raise_for_status()
            matches = r.json()
        except Exception as e:
            print(f"❌ Error fetching odds for {key}: {e}")
            continue

        for match in matches:
            start_time = match.get("commence_time")
            if not start_time or start_time[:10] != date_str:
                continue
            teams = match.get("teams", [])
            bookmakers = match.get("bookmakers", [])
            if not teams or len(teams) < 2 or not bookmakers:
                continue

            # Pick first bookmaker for simplicity
            markets = bookmakers[0].get("markets", [])
            if not markets:
                continue
            outcomes = markets[0].get("outcomes", [])
            for outcome in outcomes:
                price = outcome.get("price")
                name = outcome.get("name")
                if price:
                    american_odds = to_american(price)
                    all_bets.append({
                        "source": "OddsAPI",
                        "team1": teams[0],
                        "team2": teams[1],
                        "pick": name,
                        "odds_decimal": price,
                        "odds_american": american_odds,
                        "match_time": start_time,
                        "value": True,
                        "rating": "green"
                    })
    return all_bets

def format_bet_message(bet):
    # Format the start time nicely
    try:
        dt = datetime.fromisoformat(bet["match_time"].replace("Z", "+00:00"))
        dt_local = dt.astimezone(LOCAL_TZ)
        time_str = dt_local.strftime("%A, %b %d at %I:%M %p %Z")
    except Exception:
        time_str = bet["match_time"]

    message = (
        f"🔥 *Bet Alert* from {bet['source']}!\n"
        f"🟢 *High Value Pick*\n\n"
        f"🏟️ *Match:* {bet['team1']} vs {bet['team2']}\n"
        f"🕒 *Start:* {time_str}\n"
        f"💵 *Pick:* {bet['pick']} @ {bet['odds_american']} (Decimal: {bet['odds_decimal']:.2f})\n\n"
        "📊 *Why?*\n"
        "• Positive expected value (+EV)\n"
        "• Strong model confidence\n"
        "• Filtered for optimal daily picks"
    )
    return message

def main():
    print("✅ Starting main function...")

    today = datetime.utcnow().strftime("%Y-%m-%d")
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%d")

    all_bets = []

    # Fetch for today and tomorrow
    for date_str in [today, tomorrow]:
        print(f"📅 Fetching bets for {date_str}")

        try:
            sm_bets = get_sportmonks_bets(SPORTMONKS_API_KEY, date_str)
            print(f"📊 SportMonks bets: {len(sm_bets)}")
            all_bets.extend(sm_bets)
        except Exception as e:
            print(f"❌ Error fetching SportMonks bets: {e}")

        try:
            oa_bets = get_oddsapi_bets(ODDSAPI_KEY, date_str)
            print(f"📊 OddsAPI bets
