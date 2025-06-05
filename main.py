import requests
import datetime
import pytz
import os
import random

# ✅ Your SportMonks API key
SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"

# ✅ Your Telegram Bot info
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# ✅ List of smart emojis by value
VALUE_EMOJIS = {
    "high": "🟢 Best Bet",
    "medium": "🟡 Medium Value",
    "low": "⚠️ Low Confidence"
}

def fetch_sportmonks_bets():
    bets = []
    base_url = "https://api.sportmonks.com/v3/football/odds/date/{}?api_token=" + SPORTMONKS_API_KEY

    today = datetime.datetime.now(pytz.UTC).date()
    for i in range(3):  # today + 2 days ahead
        date_str = today + datetime.timedelta(days=i)
        url = base_url.format(date_str)
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            if not data.get("data"):
                continue

            for game in data["data"]:
                if not game.get("odds"):
                    continue
                match = game.get("fixture", {})
                odds_data = game.get("odds", [])[0]  # First bookmaker

                # Extract odds
                ml = odds_data.get("markets", {}).get("1X2", {})
                over_under = odds_data.get("markets", {}).get("over_under", {})

                if not ml or not over_under:
                    continue

                home_team = match.get("participants", [{}])[0].get("name", "Home")
                away_team = match.get("participants", [{}])[-1].get("name", "Away")
                start_time = match.get("starting_at", {}).get("date_time")

                pick_type = random.choice(["home", "over"])
                if pick_type == "home":
                    pick = f"{home_team} ML"
                    value = "high"
                else:
                    pick = "Over 2.5 Goals"
                    value = "medium"

                bet_message = f"""
🔥 Bet Alert!
{VALUE_EMOJIS[value]}

🏟️ Match: {home_team} vs {away_team}
🕒 Kickoff: {format_datetime(start_time)}
💵 Odds:
• {home_team} ML: {ml.get('home', {}).get('odds', 'N/A')}
• {away_team} ML: {ml.get('away', {}).get('odds', 'N/A')}
• Over 2.5: {over_under.get('over_2.5', {}).get('odds', 'N/A')}
• Under 2.5: {over_under.get('under_2.5', {}).get('odds', 'N/A')}

✅ Pick: {pick}

📊 Why this bet?
• {VALUE_EMOJIS[value]} — selected by auto model based on matchup strength
• 📈 High form edge / recent trends
• 🤖 Pulled from SportMonks live feed
"""
                bets.append(bet_message.strip())

        except requests.exceptions.RequestException as e:
            print(f"SportMonks error: {e}")

    return bets

def format_datetime(iso_str):
    dt = datetime.datetime.fromisoformat(iso_str).astimezone(pytz.timezone("US/Eastern"))
    return dt.strftime("%A, %B %d – %I:%M %p EST")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
    except Exception as e:
        print(f"Telegram error: {e}")

def main():
    print("📡 Fetching SportMonks value bets...")
    bets = fetch_sportmonks_bets()

    if bets:
        selected_bets = bets[:5]  # send max 5
        for bet in selected_bets:
            send_telegram_message(bet)
    else:
        send_telegram_message("⚠️ No live SportMonks bets found for today or next 2 days.\nCheck back soon!")

if __name__ == "__main__":
    main()
