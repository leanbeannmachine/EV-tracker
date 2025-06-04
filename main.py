import requests
import datetime
import pytz

# Your tokens
SPORTMONKS_API_TOKEN = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# Get current UTC time and 3 days later
now = datetime.datetime.now(pytz.utc)
in_3_days = now + datetime.timedelta(days=3)
start_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")
end_str = in_3_days.strftime("%Y-%m-%dT%H:%M:%SZ")

# API request to SportMonks for MLB fixtures
url = "https://api.sportmonks.com/v3/baseball/fixtures"
params = {
    "api_token": SPORTMONKS_API_TOKEN,
    "include": "odds.bookmakers.markets",
    "filter[starts_between]": f"{start_str},{end_str}",
    "filter[league_id]": "1",  # Assuming '1' is the MLB league ID
    "sort": "starting_at",
    "per_page": 50
}

try:
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    fixtures = data.get("data", [])
    if not fixtures:
        message = "📭 No MLB bets available in the next 3 days."
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", params={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        })
    else:
        count = 0
        for fixture in fixtures:
            try:
                teams = fixture.get("participants", [])
                if len(teams) < 2:
                    continue

                team1 = teams[0]["name"]
                team2 = teams[1]["name"]
                start_time = fixture.get("starting_at", "Unknown time")

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
                                    if value >= 120:
                                        reason = f"📊 Odds for {label}: {odds} — solid upside for a straight win."
                                        msg = (
                                            f"⚾ *{team1} vs {team2}*\n"
                                            f"🕒 Start: {start_time}\n"
                                            f"💰 Bet: *{label}* to win\n"
                                            f"💸 Odds: `{odds}`\n\n"
                                            f"{reason}"
                                        )
                                        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={
                                            "chat_id": TELEGRAM_CHAT_ID,
                                            "text": msg,
                                            "parse_mode": "Markdown"
                                        })
                                        count += 1
            except Exception as e:
                print(f"Fixture parse error: {e}")

        if count == 0:
            message = "📭 No strong MLB bets found with good odds in the next 3 days."
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", params={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message
            })

except Exception as e:
    error_msg = f"🚨 Bot error:\n{e}"
    requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", params={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": error_msg
    })
