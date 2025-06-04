import requests
import pytz
from datetime import datetime

# === CONFIG ===
API_KEY = "183b79e95844e2300faa30f9383890b5"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"


LEAGUES = [
    "soccer_argentina_primera_division",
    "soccer_brazil_campeonato",
    "soccer_usa_mls",
    "basketball_wnba"
]

MIN_EDGE_PERCENT = 0.0
MAX_IMPLIED_PROB = 1.0

# === UTILS ===
def format_american_odds(odds):
    odds = int(odds)
    return f"+{odds}" if odds > 0 else str(odds)

def implied_probability(american_odds):
    if american_odds < 0:
        return (-american_odds) / ((-american_odds) + 100)
    else:
        return 100 / (american_odds + 100)

def classify_bet(edge):
    if edge >= 10:
        return "🟢 Good Bet", "This bet has a strong expected value and is a high-confidence value play."
    elif edge >= 5:
        return "🟡 Okay Bet", "This bet has a modest edge and is reasonably safe for bankroll management."
    else:
        return "🔴 Bad Bet", "This bet has a low edge and is not recommended for value-focused strategy."

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

# === MAIN FETCH + FILTER ===
def fetch_and_send_bets():
    now = datetime.utcnow().replace(tzinfo=pytz.utc)
    headers = {"User-Agent": "ValueBot"}

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
                    # Time filtering
                    if "commence_time" not in match:
                        continue
                    commence_time = datetime.strptime(match["commence_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
                    if commence_time < now:
                        continue

                    if "teams" not in match or "home_team" not in match:
                        continue
                    home_team = match["home_team"]
                    away_team = [team for team in match["teams"] if team != home_team][0]

                    # Bookmakers and odds
                    bookmakers = match.get("bookmakers", [])
                    if not bookmakers:
                        continue
                    markets = bookmakers[0].get("markets", [])
                    if not markets:
                        continue
                    outcomes = markets[0].get("outcomes", [])
                    if not outcomes:
                        continue

                    for outcome in outcomes:
                        team = outcome.get("name")
                        odds = outcome.get("price")
                        if team is None or odds is None:
                            continue

                        odds = int(odds)
                        prob = implied_probability(odds)
                        edge = (1 - prob) * print(f"{team} @ {odds} ➝ Prob: {prob:.2f}, Edge: {edge:.2f}")


                        if edge < MIN_EDGE_PERCENT or prob > MAX_IMPLIED_PROB:
                            continue

                        quality_tag, reason = classify_bet(edge)
                        formatted_odds = format_american_odds(odds)
                        local_time = commence_time.astimezone(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d %I:%M %p")

                        message = (
                            f"*{home_team} vs {away_team}*\n"
                            f"🕒 {local_time} ET\n"
                            f"Bet: *{team}*\n"
                            f"Odds: *{formatted_odds}*\n"
                            f"Edge: *{edge:.2f}%* {quality_tag}\n"
                            f"_Reason_: {reason}"
                        )
                        send_telegram_message(message)

                except Exception as inner_e:
                    print(f"Error parsing match in {league}: {inner_e}")

        except Exception as outer_e:
            print(f"Error in league {league}: {outer_e}")

# === RUN ===
if __name__ == "__main__":
    fetch_and_send_bets()
