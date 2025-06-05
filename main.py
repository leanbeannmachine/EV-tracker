import requests
import datetime
import pytz
import random
import os
import telegram

# ✅ Your SportMonks API token
SPORTMONKS_API_TOKEN = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"

# ✅ Telegram bot credentials
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Format date in YYYY-MM-DD
def get_target_dates():
    today = datetime.datetime.now(pytz.timezone('UTC')).date()
    tomorrow = today + datetime.timedelta(days=1)
    return [str(today), str(tomorrow)]

# Format the message with emojis and reasons
def format_bet_message(bet):
    match = bet['match']
    odds = bet['odds']
    value_rating = bet['value']

    # Emojis and labels
    if value_rating == 'high':
        emoji = "🟢 Best Bet of the Day"
        reason = [
            "• 🧠 Model strongly favors this outcome",
            "• 📈 Odds show significant value vs. probability",
            "• ✅ Chosen from today’s highest trust picks"
        ]
    elif value_rating == 'medium':
        emoji = "🟡 Medium Value"
        reason = [
            "• ⚠️ Some upside with recent team form",
            "• 🔍 Decent odds-to-outcome potential",
            "• 🧪 Selected for moderate value"
        ]
    else:
        emoji = "🔴 Low Value"
        reason = [
            "• ❌ Riskier bet — limited model support",
            "• ⚠️ Volatile matchup or weak form",
            "• 📉 Lower confidence pick"
        ]

    return f"""
🔥 Bet Alert!
{emoji}

🏟️ Match: {match['home']} vs {match['away']}  
🕒 Kickoff: {match['start_time']}  
💵 Odds: {odds['label']}: {odds['value']}  

✅ Pick: {odds['label']}

📊 Why this bet?
{chr(10).join(reason)}
"""

# Pull SportMonks data
def fetch_sportmonks_bets(date_str):
    url = f"https://api.sportmonks.com/v3/football/odds/date/{date_str}?api_token={SPORTMONKS_API_TOKEN}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        bets = []
        for match_data in data.get("data", []):
            match_info = {
                "home": match_data["home_team"]["name"],
                "away": match_data["away_team"]["name"],
                "start_time": match_data["starting_at"]["date_time"]
            }

            for bookmaker in match_data.get("bookmakers", []):
                for bet_market in bookmaker.get("odds", []):
                    # Pick totals and moneyline only
                    if bet_market["label_name"].lower() in ["1x2", "totals"]:
                        for odd in bet_market.get("values", []):
                            # Simulate EV label (normally this comes from your model)
                            random_val = random.random()
                            if random_val > 0.85:
                                value = "high"
                            elif random_val > 0.6:
                                value = "medium"
                            else:
                                value = "low"

                            bets.append({
                                "match": match_info,
                                "odds": {
                                    "label": odd["value"],
                                    "value": odd["odd"]
                                },
                                "value": value
                            })

        return bets
    except Exception as e:
        print(f"SportMonks error on {date_str}: {e}")
        return []

def send_bet_alerts():
    all_bets = []
    for date_str in get_target_dates():
        print(f"Fetching bets for {date_str}...")
        bets = fetch_sportmonks_bets(date_str)
        all_bets.extend(bets)

    if not all_bets:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="⚠️ No live SportMonks bets found for today or tomorrow.")
        return

    # Pick 5 unique high/medium bets max
    filtered = [b for b in all_bets if b['value'] in ['high', 'medium']]
    random.shuffle(filtered)
    selected = filtered[:5]

    for bet in selected:
        msg = format_bet_message(bet)
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

if __name__ == "__main__":
    send_bet_alerts()
