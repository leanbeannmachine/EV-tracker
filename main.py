import requests
from datetime import datetime, timedelta
import pytz
import time
import telegram

# === CONFIGURATION ===
api_key = "7b5d540e73c8790a95b84d3713e1a572"
telegram_token = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
chat_id = "964091254"
bookmaker = "bovada"

# Add your sports here, with their OddsAPI keys:
sports = {
    "baseball_mlb": "MLB",
    "basketball_wnba": "WNBA",
    "soccer_epl": "Soccer EPL",
    "tennis_atp": "ATP Tennis"
}

american_timezone = pytz.timezone("US/Eastern")

# === FUNCTIONS ===

def get_today_and_tomorrow_dates():
    now = datetime.now(american_timezone)
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    return today, tomorrow

def get_odds_for_date(sport_key, date):
    url = (
        f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds/"
        f"?apiKey={api_key}&regions=us&markets=h2h,spreads,totals,playerProps&oddsFormat=american&dateFormat=iso&date={date}"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Failed to fetch odds for {sport_key} on {date}: {e}")
        return []

def calculate_ev(odds, probability):
    # Convert American odds to decimal for EV calc
    if odds > 0:
        decimal_odds = (odds / 100) + 1
    else:
        decimal_odds = (100 / abs(odds)) + 1
    ev = (probability * decimal_odds) - 1
    return round(ev, 3)

def get_dummy_probability(market_key, outcome_name, sport_key):
    # Dummy logic for demo, replace with real model as needed
    # Assign probabilities based on bet type and sport
    if sport_key == "baseball_mlb":
        base_prob = 0.55
    elif sport_key == "basketball_wnba":
        base_prob = 0.53
    elif sport_key == "soccer_epl":
        base_prob = 0.52
    elif sport_key == "tennis_atp":
        base_prob = 0.54
    else:
        base_prob = 0.50

    if market_key == "h2h":
        # Moneyline (win) bets
        return base_prob
    elif market_key == "spreads":
        return base_prob - 0.02  # slightly lower for spread
    elif market_key == "totals":
        return base_prob - 0.03  # slightly lower for totals
    elif market_key == "playerProps":
        return base_prob  # player props assumed average for demo
    else:
        return 0.50

def format_bet_message(game, sport_name, bet_type, outcome, odds, ev, start_time, label):
    home = game['home_team']
    away = game['away_team']
    league = sport_name
    match_time = datetime.fromisoformat(start_time).astimezone(american_timezone).strftime('%I:%M %p %Z')

    emoji_map = {
        "h2h": "🎯 Moneyline",
        "spreads": "📊 Spread",
        "totals": "⚖️ Total",
        "playerProps": "⭐ Player Prop"
    }
    bet_emoji = emoji_map.get(bet_type, "🎲 Bet")

    ev_label = "🟢 BEST VALUE" if ev > 0.07 else ("🟡 GOOD VALUE" if ev > 0.03 else "🔴 LOW VALUE")

    message = (
        f"{label} {league} Bet Alert!\n"
        f"🕒 {match_time}\n"
        f"⚾️ {away} @ {home}\n\n"
        f"{bet_emoji}\n"
        f"🔎 Pick: {outcome}\n"
        f"📈 Odds: {odds}\n"
        f"📊 Expected Value: {ev * 100:.1f}%\n"
        f"{ev_label}\n"
        f"Good luck! 🍀\n"
        f"——————"
    )
    return message

def send_telegram_message(message):
    try:
        bot = telegram.Bot(token=telegram_token)
        bot.send_message(chat_id=chat_id, text=message)
        print("✅ Sent to Telegram.")
    except Exception as e:
        print(f"❌ Failed to send message: {e}")

# === MAIN LOGIC ===

def run_bet_alerts():
    today, tomorrow = get_today_and_tomorrow_dates()
    for date in [today, tomorrow]:
        print(f"\n🔍 Checking bets for {date}...")
        for sport_key, sport_name in sports.items():
            games = get_odds_for_date(sport_key, date)
            if not games:
                continue
            for game in games:
                if not game.get("bookmakers"):
                    continue
                for book in game["bookmakers"]:
                    if book["key"] != bookmaker:
                        continue
                    for market in book.get("markets", []):
                        for outcome in market.get("outcomes", []):
                            odds = outcome.get("price")
                            if odds is None:
                                continue

                            # Calculate EV with dummy probability model
                            win_prob = get_dummy_probability(market["key"], outcome["name"], sport_key)
                            ev = calculate_ev(odds, win_prob)

                            # Only alert for positive EV bets above 3%
                            if ev > 0.03:
                                label = "🟢" if ev > 0.07 else "🟡"
                                message = format_bet_message(
                                    game,
                                    sport_name,
                                    bet_type=market["key"],
                                    outcome=outcome["name"],
                                    odds=odds,
                                    ev=ev,
                                    start_time=game["commence_time"],
                                    label=label
                                )
                                send_telegram_message(message)
                                time.sleep(1)  # polite delay to avoid spamming

if __name__ == "__main__":
    run_bet_alerts()
