import requests
import datetime
import pytz
import telegram

# 🔐 User credentials & config
ODDS_API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"  # Replace with your working token
TELEGRAM_CHAT_ID = "964091254"      # Keep as-is if unchanged

# 📈 EV threshold
MIN_EV_THRESHOLD = 0.01  # 1%+ EV required

# 🕒 Timezone
CDT = pytz.timezone("America/Chicago")

# 🏟️ Supported sports
SPORTS = [
    "baseball_mlb",
    "soccer_epl",
    "soccer_uefa_champs_league",
    "soccer_spain_la_liga",
    "soccer_germany_bundesliga",
    "soccer_italy_serie_a",
    "soccer_france_ligue_one",
    "soccer_netherlands_eredivisie",
    "soccer_mexico_liga_mx",
    "soccer_usa_mls",
]

BOOKMAKERS = "pinnacle,betonlineag"
MARKETS = "h2h,spreads,totals"

# 💰 Basic EV model (replace with enhanced logic later)
def calculate_ev(odds, model_prob):
    if odds > 0:
        implied_prob = 100 / (odds + 100)
    else:
        implied_prob = -odds / (-odds + 100)
    edge = model_prob - implied_prob
    ev = (odds / 100 if odds > 0 else 100 / -odds) * model_prob - (1 - model_prob)
    return implied_prob, edge, ev

# 🧠 Simulated model probabilities for testing (replace with real model later)
def get_model_probability(outcome_name):
    simulated_probs = {
        "home": 0.58,
        "away": 0.54,
        "draw": 0.32,
        "over": 0.57,
        "under": 0.56,
        "spread_home": 0.59,
        "spread_away": 0.55,
    }
    return simulated_probs.get(outcome_name, 0.50)

# 📬 Format emoji for EV
def format_ev_emoji(ev):
    if ev >= 0.10:
        return f"+{ev*100:.1f}% 🟢 BEST VALUE"
    elif ev >= 0.03:
        return f"+{ev*100:.1f}% 🟡 GOOD VALUE"
    return None

# 📲 Send alert
def send_telegram_alert(message):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.ParseMode.HTML)
    except telegram.error.Unauthorized:
        print("Telegram error: Unauthorized")

# 🚀 Main run function
def run():
    for sport in SPORTS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": MARKETS,
            "oddsFormat": "american",
            "bookmakers": BOOKMAKERS
        }

        try:
            res = requests.get(url, params=params)
            res.raise_for_status()
            games = res.json()

            for game in games:
                title = f"🏟️ {game['home_team']} vs {game['away_team']}"
                game_time = datetime.datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).astimezone(CDT)
                formatted_time = game_time.strftime("%b %d, %I:%M %p CDT")

                odds_lines = []
                market_results = []

                for bookmaker in game.get("bookmakers", []):
                    for market in bookmaker.get("markets", []):
                        for outcome in market.get("outcomes", []):
                            label = market["key"]
                            odds = outcome["price"]
                            team = outcome["name"]

                            if label == "h2h":
                                model_prob = get_model_probability("home" if team == game["home_team"] else "away")
                            elif label == "totals":
                                model_prob = get_model_probability("over" if "over" in team.lower() else "under")
                            elif label == "spreads":
                                model_prob = get_model_probability("spread_home" if team == game["home_team"] else "spread_away")
                            else:
                                continue

                            implied_prob, edge, ev = calculate_ev(odds, model_prob)
                            if ev >= MIN_EV_THRESHOLD:
                                ev_label = format_ev_emoji(ev)
                                if not ev_label:
                                    continue

                                bet_type = label.upper()
                                pick_line = f"<b>🔥 Pick:</b> {team}"
                                market_odds = f"<b>💵 Odds:</b> {odds}"
                                ev_line = f"<b>📈 Expected Value:</b> {ev_label}"
                                implied = f"<b>🧮 Implied Prob:</b> {implied_prob*100:.1f}%"
                                model = f"<b>🧠 Model Prob:</b> {model_prob*100:.1f}%"
                                diff = f"<b>🔍 Edge:</b> {edge*100:.2f}%"
                                sport_emoji = "⚾" if "mlb" in sport else "⚽"

                                market_results.append(
                                    f"<b>📊 {bet_type} BET</b>\n\n{pick_line}\n{market_odds}\n{ev_line}\n{implied}\n{model}\n{diff}\n{sport_emoji} ——————"
                                )

                if market_results:
                    message = f"{title}\n📅 {formatted_time}\n" + "\n\n" + "\n\n".join(market_results)
                    send_telegram_alert(message)

        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds for {sport}: {e}")

if __name__ == "__main__":
    run()
