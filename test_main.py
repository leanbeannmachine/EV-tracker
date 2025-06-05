import requests
from datetime import datetime, timedelta
from bet_formatter import format_bet_message

# Telegram setup
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("❌ Telegram error:", e)

# Dummy match data to simulate a real bet
dummy_match = {
    "home_team": "Tampa Bay Rays",
    "away_team": "Texas Rangers",
    "commence_time": (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "bookmakers": [
        {
            "markets": [
                {
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Tampa Bay Rays", "price": -144},
                        {"name": "Texas Rangers", "price": 122}
                    ]
                },
                {
                    "key": "totals",
                    "outcomes": [
                        {"name": "Over", "point": 8.5, "price": -110},
                        {"name": "Under", "point": 8.5, "price": -110}
                    ]
                }
            ]
        }
    ],
    "team_form": "Model favors recent volatility in scoring"
}

# Send formatted test alert
msg = format_bet_message(dummy_match)
print(msg)
send_to_telegram(msg)
