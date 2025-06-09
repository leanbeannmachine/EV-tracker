import requests
from datetime import datetime, timedelta
import pytz
import telegram

# === CONFIG ===
ODDS_API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
SPORTMONKS_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0G-BLTAplBKVHt8YL6m0jNZpmUbCu4szH"
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"
LEAGUES = ["mlb"]  # Extend as needed

# === TELEGRAM BOT ===
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# === FUNCTIONS ===

def american_to_implied_prob(odds):
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def fetch_odds():
    today = datetime.now().strftime('%Y-%m-%d')
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    response = requests.get(url, params=params)
    return response.json() if response.status_code == 200 else []

def format_bet_message(game, best_bet_msg):
    dt = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
    local_time = dt.astimezone(pytz.timezone("US/Eastern")).strftime("%b %d, %I:%M %p")
    home = game['home_team']
    away = game['away_team']
    return f"""
🟢 *{away} @ {home}*
📅 *{local_time} ET*
🏆 *Moneyline:*
   - {away}: {best_bet_msg.get('ml_away', 'N/A')}
   - {home}: {best_bet_msg.get('ml_home', 'N/A')}

📏 *Spread:*
   - {away} {best_bet_msg.get('spread_away', 'N/A')}
   - {home} {best_bet_msg.get('spread_home', 'N/A')}

📊 *Total:*
   - Over {best_bet_msg.get('total_over', 'N/A')}
   - Under {best_bet_msg.get('total_under', 'N/A')}

✅ *Best Bet:* {best_bet_msg['best_bet']}

""".strip()

def parse_game(game):
    outcomes = {"ml_home": None, "ml_away": None, "spread_home": None, "spread_away": None, "total_over": None, "total_under": None, "best_bet": "N/A"}
    try:
        for market in game['bookmakers'][0]['markets']:
            if market['key'] == 'h2h':
                for o in market['outcomes']:
                    if o['name'] == game['home_team']:
                        prob = american_to_implied_prob(o['price'])
                        outcomes['ml_home'] = f"{o['price']} ({round(prob*100)}%)"
                    elif o['name'] == game['away_team']:
                        prob = american_to_implied_prob(o['price'])
                        outcomes['ml_away'] = f"{o['price']} ({round(prob*100)}%)"

            elif market['key'] == 'spreads':
                for o in market['outcomes']:
                    if o['name'] == game['home_team']:
                        outcomes['spread_home'] = f"{o['point']} @ {o['price']}"
                    elif o['name'] == game['away_team']:
                        outcomes['spread_away'] = f"{o['point']} @ {o['price']}"

            elif market['key'] == 'totals':
                for o in market['outcomes']:
                    if o['name'] == "Over":
                        outcomes['total_over'] = f"{o['point']} @ {o['price']}"
                    elif o['name'] == "Under":
                        outcomes['total_under'] = f"{o['point']} @ {o['price']}"

        # Best Bet Logic (simple EV detection for demo)
        best_value = None
        best_ev = -1
        for market in game['bookmakers'][0]['markets']:
            for o in market['outcomes']:
                if "price" in o:
                    imp = american_to_implied_prob(o['price'])
                    ev = 1 - imp  # Simplified EV placeholder
                    if ev > best_ev:
                        best_ev = ev
                        best_value = f"{o.get('name')} @ {o['price']}"

        outcomes['best_bet'] = f"🟢 {best_value}" if best_value else "No clear edge"

    except Exception as e:
        outcomes['best_bet'] = f"⚠️ Parsing error: {str(e)}"
    return outcomes

def main():
    games = fetch_odds()
    for game in games:
        parsed = parse_game(game)
        msg = format_bet_message(game, parsed)
        bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)

# === RUN ===
if __name__ == "__main__":
    main()
