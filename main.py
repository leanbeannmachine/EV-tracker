import requests
import telegram
import time
from datetime import datetime, timedelta
import pytz

# === CONFIG ===
API_KEY = "7b5d540e73c8790a95b84d3713e1a572"
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"

BOOKMAKERS_ALLOWED = ["draftkings", "fanduel"]
TIMEZONE = pytz.timezone("US/Eastern")

# --- Functions ---

def get_date_strings():
    now = datetime.now(TIMEZONE)
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    return today, tomorrow

def fetch_odds(sport_key, date):
    url = (
        f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
        f"?apiKey={API_KEY}&regions=us&markets=h2h,spreads,totals,playerProps"
        f"&oddsFormat=american&dateFormat=iso&date={date}"
    )
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching odds for {sport_key} on {date}: {e}")
        return []

def american_to_decimal(american_odds):
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1

def calculate_ev(odds, probability):
    decimal_odds = american_to_decimal(odds)
    ev = (probability * decimal_odds) - 1
    return round(ev, 3)

def dummy_probability(market_key, outcome_name, sport_key):
    # Placeholder, adjust as needed for your real model
    base_prob = 0.5
    if sport_key == "baseball_mlb":
        base_prob = 0.55
    elif sport_key == "basketball_wnba":
        base_prob = 0.53
    elif sport_key == "soccer_epl":
        base_prob = 0.52
    elif sport_key == "tennis_atp":
        base_prob = 0.54

    if market_key == "h2h":
        return base_prob
    elif market_key == "spreads":
        return base_prob - 0.02
    elif market_key == "totals":
        return base_prob - 0.03
    elif market_key == "playerProps":
        return base_prob
    else:
        return 0.5

def format_message(game, sport_name, bet_type, outcome_name, odds, ev, commence_time, label):
    home = game["home_team"]
    away = game["away_team"]
    league = sport_name
    local_time = datetime.fromisoformat(commence_time).astimezone(TIMEZONE).strftime("%I:%M %p %Z")

    emojis = {
        "h2h": "🎯 Moneyline",
        "spreads": "📊 Spread",
        "totals": "⚖️ Totals",
        "playerProps": "⭐ Player Prop"
    }
    bet_emoji = emojis.get(bet_type, "🎲 Bet")

    ev_label = "🟢 BEST VALUE" if ev > 0.07 else ("🟡 GOOD VALUE" if ev > 0.03 else "🔴 LOW VALUE")

    message = (
        f"{label} {league} Bet Alert!\n"
        f"🕒 {local_time}\n"
        f"{away} @ {home}\n\n"
        f"{bet_emoji}\n"
        f"Pick: {outcome_name}\n"
        f"Odds: {odds}\n"
        f"Expected Value: {ev * 100:.1f}%\n"
        f"{ev_label}\n"
        f"Good luck! 🍀\n"
        "——————"
    )
    return message

def send_telegram(text):
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        bot.send_message(chat_id=CHAT_ID, text=text)
        print("Sent to Telegram")
    except Exception as e:
        print(f"Telegram send failed: {e}")

# --- Main ---

def main():
    today, tomorrow = get_date_strings()

    sports = {
        "baseball_mlb": "MLB",
        "basketball_wnba": "WNBA",
        "soccer_epl": "Soccer EPL",
        "tennis_atp": "ATP Tennis"
    }

    for date in [today, tomorrow]:
        print(f"Fetching bets for {date}")
        for sport_key, sport_name in sports.items():
            games = fetch_odds(sport_key, date)
            if not games:
                continue
            for game in games:
                if "bookmakers" not in game:
                    continue
                for bookmaker in game["bookmakers"]:
                    if bookmaker["key"] not in BOOKMAKERS_ALLOWED:
                        continue
                    for market in bookmaker.get("markets", []):
                        for outcome in market.get("outcomes", []):
                            odds = outcome.get("price")
                            if odds is None:
                                continue
                            prob = dummy_probability(market["key"], outcome["name"], sport_key)
                            ev = calculate_ev(odds, prob)

                            if ev > 0.03:  # Only send positive EV bets above 3%
                                label = "🟢" if ev > 0.07 else "🟡"
                                msg = format_message(
                                    game, sport_name, market["key"], outcome["name"], odds, ev, game["commence_time"], label
                                )
                                send_telegram(msg)
                                time.sleep(1)  # delay to avoid spamming

if __name__ == "__main__":
    main()
