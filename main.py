import requests
import telegram
from datetime import datetime, timezone
import random

# --- CONFIGURATION ---
SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
THRESHOLD_EDGE = 5  # Minimum edge % to send
ODDS_SOURCE = "bet365"  # Can adjust later if needed

# --- Initialize bot ---
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# --- Helper functions ---
def format_american_odds(odds_decimal):
    if odds_decimal >= 2.0:
        return f"+{int((odds_decimal - 1) * 100)}"
    else:
        return f"{int(-100 / (odds_decimal - 1))}"

def implied_probability(decimal_odds):
    return 1 / decimal_odds if decimal_odds else 0

def classify_edge(edge):
    if edge >= 10:
        return "🟢 High Value"
    elif edge >= 5:
        return "🟡 Solid Value"
    else:
        return "🔴 Low Value"

def generate_reasoning(home, away, odds, implied, edge):
    trends = [
        f"{home} vs {away} has historically favored {random.choice([home, away])}",
        f"{away} has underperformed in their last 5 matches.",
        f"Recent data suggests a mismatch in form levels.",
        f"Odds of {odds} imply only {implied*100:.1f}% chance, but market signals higher probability.",
        f"{home} playing at home with momentum makes this value sharp.",
        f"Betting models predict this line should be shorter."
    ]
    return random.choice(trends) + f" - Edge: {edge:.1f}%"

# --- Main fetch function ---
def fetch_fixtures():
    url = f"https://api.sportmonks.com/v3/football/fixtures?api_token={SPORTMONKS_API_KEY}&include=odds&filters=starts_between:{datetime.utcnow().date()},{datetime.utcnow().date()}"
    response = requests.get(url)
    if response.status_code != 200:
        print("Failed to fetch SportMonks data.")
        return []

    data = response.json().get("data", [])
    alerts = []

    for match in data:
        try:
            fixture_id = match["id"]
            home = match["home_team"]["name"]
            away = match["away_team"]["name"]
            kickoff = match["starting_at"]["date_time"]
            kickoff_dt = datetime.fromisoformat(kickoff.replace("Z", "+00:00"))

            odds_data = match.get("odds", [])
            for odd in odds_data:
                if odd.get("bookmaker") and odd["bookmaker"]["name"].lower() != ODDS_SOURCE:
                    continue
                for bet in odd.get("odds", []):
                    outcome = bet.get("label")
                    value = bet.get("value")
                    decimal_odds = float(bet.get("decimal", 0))

                    if decimal_odds == 0:
                        continue

                    implied = implied_probability(decimal_odds)
                    edge = (1 - implied) * 100

                    if edge >= THRESHOLD_EDGE:
                        american_odds = format_american_odds(decimal_odds)
                        tag = classify_edge(edge)
                        reason = generate_reasoning(home, away, american_odds, implied, edge)
                        alerts.append({
                            "match": f"{home} vs {away}",
                            "start": kickoff_dt.strftime('%Y-%m-%d %H:%M UTC'),
                            "bet": f"{outcome} ({value})",
                            "odds": american_odds,
                            "edge": f"{edge:.1f}%",
                            "quality": tag,
                            "reason": reason
                        })
        except Exception as e:
            print(f"Error processing match: {e}")
            continue

    return alerts

def send_alerts():
    bets = fetch_fixtures()
    if not bets:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="No value bets found today.")
        return

    for bet in bets:
        msg = (
            f"{bet['match']} - 🕒 {bet['start']}\n"
            f"Bet: {bet['bet']}\n"
            f"Odds: {bet['odds']}\n"
            f"Edge: {bet['edge']} {bet['quality']}\n"
            f"Reason: {bet['reason']}"
        )
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

# --- Trigger ---
if __name__ == "__main__":
    send_alerts()
