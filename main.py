import requests
import time
import pytz
from datetime import datetime

# === CONFIGURE YOUR KEYS ===
API_KEY = "183b79e95844e2300faa30f9383890b5"  # OddsAPI key
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# === LEAGUES TO TRACK ===
LEAGUES = [
    "soccer_argentina_primera_division",
    "soccer_brazil_campeonato",
    "soccer_usa_mls",
    "basketball_wnba",
]

# === FILTER SETTINGS ===
MIN_EDGE_PERCENT = 5.0  # Minimum edge % to consider it +EV
MAX_IMPLIED_PROB = 0.75  # Avoid bets that imply > 75% win (risky odds)

# === FORMAT AMERICAN ODDS ===
def format_american_odds(odds):
    odds = int(odds)
    return f"+{odds}" if odds > 0 else str(odds)

# === ESTIMATE IMPLIED WIN PROBABILITY ===
def implied_probability(american_odds):
    if american_odds < 0:
        return (-american_odds) / ((-american_odds) + 100)
    else:
        return 100 / (american_odds + 100)

# === GET BET QUALITY ===
def classify_bet(edge):
    if edge >= 10:
        return "🟢 Good Bet", "This bet has a strong expected value and is a high-confidence value play."
    elif edge >= 5:
        return "🟡 Okay Bet", "This bet has a modest edge and is reasonably safe for bankroll management."
    else:
        return "🔴 Bad Bet", "This bet has a low edge and is not recommended for value-focused strategy."

# === TELEGRAM SEND ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

# === FETCH +EV BETS ===
def fetch_and_send_bets():
    headers = {"User-Agent": "ValueBot"}
    now = datetime.utcnow().replace(tzinfo=pytz.utc)

    for league in LEAGUES:
        try:
            url = f"https://api.the-odds-api.com/v4/sports/{league}/odds?regions=us&markets=h2h&oddsFormat=american&apiKey={API_KEY}"
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Error fetching odds for {league}: {response.status_code}")
                continue
            data = response.json()

            for match in data:
                try:
                    commence_time_str = match.get("commence_time", "")
                    commence_time = datetime.strptime(commence_time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
                    
                    if commence_time < now:
                        continue  # Skip past games

                    teams = match["teams"]
                    bookmakers = match.get("bookmakers", [])
                    if not bookmakers:
                        continue
                    outcomes = bookmakers[0]["markets"][0]["outcomes"]

                    for outcome in outcomes:
                        team = outcome["name"]
                        odds = int(outcome["price"])

                        prob = implied_probability(odds)
                        edge = (1 - prob) * 100  # naive edge estimate

                        if edge < MIN_EDGE_PERCENT or prob > MAX_IMPLIED_PROB:
                            continue

                        quality_tag, reason = classify_bet(edge)

                        formatted_odds = format_american_odds(odds)
                        home_team = match["home_team"]
                        away_team = match["away_team"]
                        time_display = commence_time.astimezone(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d %I:%M %p")

                        message = (
                            f"*{home_team} vs {away_team}*\n"
                            f"🕒 {time_display} ET\n"
                            f"Bet: *{team}*\n"
                            f"Odds: *{formatted_odds}* (American)\n"
                            f"Edge: *{edge:.2f}%* {quality_tag}\n"
                            f"_Reason_: {reason}"
                        )

                        send_telegram_message(message)

                except Exception as e:
                    print(f"Error parsing match in {league}: {e}")
                    continue

        except Exception as e:
            print(f"Error in league {league}: {e}")

# === MAIN RUN ===
if __name__ == "__main__":
    fetch_and_send_bets()
