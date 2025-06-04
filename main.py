import requests
from datetime import datetime
from telegram import Bot

# --- CONFIGURATION ---
ODDS_API_KEY = '85c7c9d1acaad09cae7e93ea02f627ae'
TELEGRAM_BOT_TOKEN = '7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI'
TELEGRAM_CHAT_ID = '964091254'
SPORT = 'baseball_mlb'

# --- HELPERS ---
def implied_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)

def risk_rating(odds):
    prob = implied_prob(odds)
    if prob < 0.45:
        return "✅ (Safe value)"
    elif prob < 0.55:
        return "⚠️ (Medium risk)"
    else:
        return "❌ (Low value)"

def format_bet_message(game):
    teams = f"{game['away_team']} @ {game['home_team']}"
    start_time = datetime.strptime(game['commence_time'], "%Y-%m-%dT%H:%M:%SZ")
    start_utc = start_time.strftime("%Y-%m-%d %H:%M UTC")

    bookmaker = game['bookmakers'][0]
    markets = {m['key']: m for m in bookmaker['markets']}

    message = f"""📊 MLB Bet Preview
🕒 {start_utc}
⚔️ {teams}
🏦 {bookmaker['title']} Sportsbook
"""

    # Moneyline
    if 'h2h' in markets:
        ml_outcomes = markets['h2h']['outcomes']
        message += "\n💰 Moneyline:\n"
        for o in ml_outcomes:
            message += f"- {o['name']}: {o['price']} {risk_rating(o['price'])}\n"

    # Spread
    if 'spreads' in markets:
        message += "\n🟩 Spread:\n"
        for s in markets['spreads']['outcomes']:
            message += f"- {s['name']} {s['point']}: {s['price']} {risk_rating(s['price'])}\n"

    # Totals
    if 'totals' in markets:
        message += "\n📈 Total:\n"
        for t in markets['totals']['outcomes']:
            label = "Over" if t['name'].lower().startswith("over") else "Under"
            message += f"- {label} {t['point']}: {t['price']} {risk_rating(t['price'])}\n"

    # Trends (placeholder)
    message += f"""
📊 Trends:
- {game['away_team']}: 🔥 4-1 ATS in last 5
- {game['home_team']}: ❄️ 1-4 in last 5 vs division

🔎 *Lean: {game['away_team']} +1.5 spread ✅*
📌 Bet smart. Look for 🔒 low-risk run lines.
"""
    return message

# --- MAIN FUNCTION ---
def fetch_and_send_bets():
    url = (
        f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/"
        f"?apiKey={ODDS_API_KEY}&regions=us&markets=h2h,spreads,totals&oddsFormat=american&dateFormat=iso"
    )
    try:
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception(f"{response.status_code} - {response.text}")

        games = response.json()
        if not games:
            Bot(token=TELEGRAM_BOT_TOKEN).send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text="📭 No MLB games available for today."
            )
            return

        for game in games:
            msg = format_bet_message(game)
            Bot(token=TELEGRAM_BOT_TOKEN).send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)

    except Exception as e:
        Bot(token=TELEGRAM_BOT_TOKEN).send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=f"🚨 OddsAPI Error:\n{e}"
        )

# Run this on Heroku or trigger manually
fetch_and_send_bets()
