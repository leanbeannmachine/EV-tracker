import requests
import datetime
import time
import pytz
import math
import telegram

# --- CONFIG ---
API_KEY = "7b5d540e73c8790a95b84d3713e1a572"
SPORTS = "baseball_mlb,basketball_wnba,soccer_usa_mls,soccer_usa_nws,mma_mixed_martial_arts"
REGIONS = "us"
MARKETS = "h2h,spreads,totals"
ODDS_FORMAT = "american"
DATE_FORMAT = "%Y-%m-%d %H:%M"
BOOKMAKERS = ["draftkings", "fanduel"]
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def get_us_time():
    return datetime.datetime.now(pytz.timezone("US/Eastern"))

def calculate_ev(probability, odds):
    decimal_odds = 100 / abs(odds) + 1 if odds < 0 else (odds / 100) + 1
    ev = (probability * decimal_odds - 1) * 100
    return round(ev, 2)

def convert_prob_to_american(probability):
    if probability == 0 or probability >= 1:
        return None
    return int(round(-100 * probability / (1 - probability)) if probability > 0.5 else round(100 * (1 - probability) / probability))

def get_bet_quality_label(ev):
    if ev >= 10:
        return "🟢 BEST VALUE"
    elif ev >= 5:
        return "🟡 GOOD VALUE"
    elif ev >= 2:
        return "🟠 DECENT VALUE"
    else:
        return "🔴 LOW VALUE"

def fetch_odds():
    url = "https://api.the-odds-api.com/v4/sports/odds"
    params = {
        "apiKey": API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT
    }

    try:
        response = requests.get(f"{url}?apiKey={API_KEY}&regions={REGIONS}&markets={MARKETS}&oddsFormat={ODDS_FORMAT}&bookmakers=draftkings,fanduel")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("Error fetching odds:", e)
        return []

def process_bets():
    data = fetch_odds()
    today = get_us_time().date()
    sent_bets = set()

    for game in data:
        try:
            commence_time = datetime.datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).astimezone(pytz.timezone("US/Eastern"))
            if commence_time.date() > today + datetime.timedelta(days=1):
                continue

            teams = game["home_team"], game["away_team"]
            for bookmaker in game.get("bookmakers", []):
                if bookmaker["key"] not in BOOKMAKERS:
                    continue
                for market in bookmaker.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        team = outcome.get("name")
                        if team not in teams:
                            continue

                        american_odds = outcome.get("price")
                        if not isinstance(american_odds, (int, float)):
                            continue

                        # Use dummy win probability estimate (replace with model if needed)
                        win_prob = 0.55 if "home" in team.lower() else 0.45
                        ev = calculate_ev(win_prob, american_odds)
                        if ev < 2:
                            continue

                        label = get_bet_quality_label(ev)
                        matchup = f"{teams[1]} vs {teams[0]}"
                        match_time = commence_time.strftime(DATE_FORMAT)
                        market_name = market.get("key", "").upper()

                        bet_id = f"{matchup}-{market_name}-{team}-{bookmaker['key']}"
                        if bet_id in sent_bets:
                            continue
                        sent_bets.add(bet_id)

                        msg = f"""📊 *{market_name}*
🏟️ *Match*: {matchup}
📅 *Time*: {match_time}
🎯 *Pick*: {team}
💰 *Odds*: {american_odds}
📈 *Expected Value*: {ev}%
{label}
—
Good luck! 🍀"""
                        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode=telegram.ParseMode.MARKDOWN)

        except Exception as e:
            print(f"Error processing game: {e}")

if __name__ == "__main__":
    process_bets()
