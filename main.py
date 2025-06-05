import requests
import datetime
import time

# API Keys and Tokens
ODDS_API_KEY = "7b5d540e73c8790a95b84d3713e1a572"
SPORTMONKS_API_KEY = "pt70HsJAeICOY3nWH8bLDtQFPk4kMDz0PHF9ZvqfFuhseXsk10Xfirbh4pAG"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# Helper to convert to American odds
def to_american(decimal_odds):
    try:
        if decimal_odds >= 2.0:
            return int((decimal_odds - 1) * 100)
        else:
            return int(-100 / (decimal_odds - 1))
    except:
        return None

# Check if odds fall within the allowed range
def is_valid_american(odds):
    return -200 <= odds <= 150

# Send message to Telegram
def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload, timeout=10)
        print("✅ Sent to Telegram")
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

# Format the message cleanly
def format_bet_message(match, pick_label, odds_text, start_time, value_indicator):
    home = match.get('home_team')
    away = match.get('away_team')
    message = (
    "🔥 Bet Alert!\n"
    "🟡 Low Value\n"
    "🏟️ Texas Rangers @ Tampa Bay Rays\n"
    "🕒 Start: Thursday, June 05 at 09:43 PM EST\n"
    "💵 Odds:\n"
    "• Tampa Bay Rays: -144\n"
    "• Texas Rangers: +122\n"
    "• Total Over 8.5 @ -110\n"
    "• Total Under 8.5 @ -110\n"
    "✅ Pick: Over 8.5 Runs\n\n"
    "📊 Why?\n"
    "• Odds range shows 🟡 low value\n"
    "• Model favors recent volatility in scoring\n"
    "• Auto-filtered for optimal daily picks"
)
    return message

# Fetch value bets from OddsAPI
def get_oddsapi_bets():
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,totals",
        "oddsFormat": "decimal",
        "dateFormat": "iso"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ OddsAPI Error: {e}")
        return []

    value_bets = []
    for match in data:
        try:
            teams = match.get("teams", [])
            home_team = match.get("home_team", "")
            away_team = teams[0] if teams[1] == home_team else teams[1]
            start_time = match.get("commence_time", "").replace("T", " ").replace("Z", " UTC")

            for bookmaker in match.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    label = market.get("key")
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        name = outcome.get("name")
                        price = outcome.get("price")
                        american_odds = to_american(price)

                        if not is_valid_american(american_odds):
                            continue

                        pick_label = name
                        odds_text = f"• {teams[0]}: {to_american(outcomes[0]['price'])}
• {teams[1]}: {to_american(outcomes[1]['price'])}"
                        if label == "totals":
                            pick_label = f"{name} {market.get('point')}"
                            odds_text = f"• Total Over {market.get('point')} @ {to_american(outcomes[0]['price'])}
• Total Under {market.get('point')} @ {to_american(outcomes[1]['price'])}"

                        value_indicator = "🟢 Best Value" if abs(american_odds) >= 120 else "🟡 Low Value"
                        value_bets.append({
                            "home_team": home_team,
                            "away_team": away_team,
                            "start_time": start_time,
                            "pick_label": pick_label,
                            "odds_text": odds_text,
                            "value_indicator": value_indicator
                        })
                        break
        except Exception as e:
            print(f"❌ Parse Error: {e}")
            continue

    return value_bets

# Main loop
def main():
    bets = get_oddsapi_bets()
    print(f"✅ Loaded {len(bets)} bets")

    if not bets:
        send_telegram_message("⚠️ No value bets found right now. Check back soon!")
        return

    sent = 0
    for bet in bets:
        message = format_bet_message(
            match=bet,
            pick_label=bet["pick_label"],
            odds_text=bet["odds_text"],
            start_time=bet["start_time"],
            value_indicator=bet["value_indicator"]
        )
        send_telegram_message(message)
        time.sleep(1)
        sent += 1

    print(f"✅ Sent {sent} bets to Telegram")

if __name__ == "__main__":
    main()
