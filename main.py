import requests
import datetime
import pytz

# Your tokens
SPORTMONKS_API_TOKEN = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# Get UTC ISO 8601 timestamps for "now" and "3 days from now"
now = datetime.datetime.now(pytz.utc)
in_3_days = now + datetime.timedelta(days=3)
start_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
end_str = in_3_days.strftime("%Y-%m-%dT%H:%M:%SZ")

# API request to SportMonks
url = "https://api.sportmonks.com/v3/football/fixtures"
params = {
    "api_token": SPORTMONKS_API_TOKEN,
    "include": "odds.bookmakers.markets",
    "filter[starts_between]": f"{start_str},{end_str}",
    "sort": "starting_at",
    "per_page": 50
}

try:
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    fixtures = data.get("data", [])
    if not fixtures:
        message = "📭 No good value bets available in the next 3 days."
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", params={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        })
    else:
        count = 0
        for fixture in fixtures:
            try:
                teams = fixture["participants"]
                team1 = teams[0]["name"]
                team2 = teams[1]["name"]
                start_time = fixture["starting_at"]

                odds_data = fixture.get("odds", {}).get("data", [])
                for bookmaker in odds_data:
                    markets = bookmaker.get("markets", {}).get("data", [])
                    for market in markets:
                        if market["name"] == "Match Winner":
                            outcomes = market.get("outcomes", {}).get("data", [])
                            for outcome in outcomes:
                                if outcome.get("odds", {}).get("american"):
                                    odds = outcome["odds"]["american"]
                                    label = outcome["label"]
                                    value = int(odds.replace("+", "")) if "+" in odds else -int(odds)
                                    if value >= 120:  # VALUE FILTER
                                        reason = f"📊 Odds for {label}: {odds
