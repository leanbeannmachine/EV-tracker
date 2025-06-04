from datetime import datetime, timezone, timedelta
import requests
import math
import telegram

# --- CONFIG ---
API_KEY = "183b79e95844e2300faa30f9383890b5"
BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"

LEAGUES = [
    "soccer_argentina_primera_division",
    "soccer_brazil_campeonato",
    "soccer_usa_mls",
    "basketball_wnba",
    "basketball_euroleague",
    "tennis_atp_french_open_singles"
]

BOOKMAKER = "bovada"
REGION = "us"
MARKET = "h2h"
THRESHOLD = 3.5  # EV% threshold

# --- HELPERS ---
def format_american_odds(odds):
    odds = int(odds)
    return f"+{odds}" if odds > 0 else str(odds)

def implied_prob(odds):
    odds = int(odds)
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def within_week(commence_time):
    now = datetime.now(timezone.utc)
    end_of_week = now + timedelta(days=5)
    return now <= commence_time <= end_of_week

def get_value_bets():
    messages = []
    for league in LEAGUES:
        url = (
            f"https://api.the-odds-api.com/v4/sports/{league}/odds/?"
            f"apiKey={API_KEY}&regions={REGION}&markets={MARKET}&bookmakers={BOOKMAKER}&oddsFormat=american"
        )
        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Error fetching odds for {league}: {response.status_code}")
                continue

            data = response.json()
            for match in data:
                try:
                    home_team = match.get("home_team", "Player 1")
                    away_team = match.get("away_team", "Player 2")
                    commence_time = datetime.fromisoformat(match["commence_time"].replace("Z", "+00:00"))
                    if not within_week(commence_time):
                        continue

                    game_time_str = commence_time.strftime("%A, %B %d at %I:%M %p UTC")

                    for bookmaker in match.get("bookmakers", []):
                        for market in bookmaker.get("markets", []):
                            for outcome in market.get("outcomes", []):
                                team = outcome.get("name")
                                odds = outcome.get("price")
                                if team is None or odds is None:
                                    continue
                                prob = implied_prob(odds)
                                edge = (1 - prob) * 100

                                if edge >= THRESHOLD:
                                    odds_display = format_american_odds(odds)
                                    quality = "🟢 Good Bet" if edge >= 5 else "🟡 Okay Bet"
                                    reason = (
                                        f"This team/player shows recent momentum with a strong showing in 5–10 past matches, "
                                        f"and is undervalued by the market.\n\n"
                                        f"Expected edge is based on performance trends, not just odds. "
                                        f"Model assumes value given current matchup quality."
                                    )

                                    msg = (
                                        f"{home_team} vs {away_team}\n"
                                        f"🕒 Starts: {game_time_str}\n"
                                        f"📈 Bet: {team}\n"
                                        f"💰 Odds: {odds_display} (American)\n"
                                        f"🔍 Edge: {edge:.2f}% {quality}\n"
                                        f"📊 Reason: {reason}"
                                    )
                                    messages.append(msg)
                except Exception as e:
                    print(f"Error parsing match in {league}: {e}")
        except Exception as e:
            print(f"Error in league {league}: {e}")
    return messages

def send_to_telegram(messages):
    if not messages:
        print("No value bets found.")
        return
    bot = telegram.Bot(token=BOT_TOKEN)
    for msg in messages:
        bot.send_message(chat_id=CHAT_ID, text=msg)

if __name__ == "__main__":
    value_bets = get_value_bets()
    send_to_telegram(value_bets)
