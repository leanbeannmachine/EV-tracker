import requests
from datetime import datetime, timedelta
import pytz
import telegram
import json
import os

API_KEY = "b478dbe3f62f1f249a7c319cb2248bc5"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

BOOKMAKERS = ["pinnacle", "betonlineag"]
SPORTS = ["baseball_mlb", "basketball_wnba"]

RESULTS_FILE = "results.json"

def generate_reasoning(market, team):
    if market == "h2h":
        return f"The {team} come in with serious momentum 🚀 and the metrics are tilting in their favor 📊. With this kind of line, there's huge upside on a team that’s been outperforming expectations!"
    elif market == "spreads":
        return f"{team} has been covering spreads consistently 🧱 due to tough defense and reliable scoring. The matchup looks promising again today."
    elif market == "totals":
        return f"Based on tempo and efficiency 📈, this total line holds strong value. Trends and matchup data support the bet."
    return "Backed by data and matchup trends, this is a value-driven play."

def fetch_odds_for_sport(sport_key):
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "bookmakers": ",".join(BOOKMAKERS)
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching odds for {sport_key}: {e}")
        return []

def calculate_ev(american_odds, win_prob):
    if american_odds > 0:
        decimal_odds = 1 + (american_odds / 100)
    else:
        decimal_odds = 1 + (100 / abs(american_odds))
    ev = (decimal_odds * win_prob) - 1
    return ev * 100

def format_ev_label(ev):
    if ev > 7:
        return "🟢 *BEST VALUE*"
    elif ev > 3:
        return "🟡 *GOOD VALUE*"
    elif ev > 0:
        return "🟠 *SLIGHT EDGE*"
    else:
        return "🔴 *NO EDGE*"

def is_today_game(game_time_str):
    game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00')).astimezone(pytz.timezone('US/Eastern'))
    now = datetime.now(pytz.timezone('US/Eastern'))
    return game_time.date() == now.date()

def filter_today_games(games):
    return [g for g in games if is_today_game(g['commence_time'])]

def format_message(game, market, outcome, odds, ev, start_time):
    market_key = market.lower()
    team = outcome.get('name', '')
    line_info = ""

    if market_key == "spreads" and 'point' in outcome:
        line_info = f" {outcome['point']:+.1f}"
    elif market_key == "totals" and 'point' in outcome:
        line_info = f" {outcome['point']:.1f}"

    if not team:
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        team = f"{away} vs {home}"

    team_line = f"{team}{line_info}"
    readable_time = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(pytz.timezone('US/Eastern')).strftime('%b %d, %I:%M %p ET')
    odds_str = f"{odds:+}" if isinstance(odds, int) else odds
    label = format_ev_label(ev)
    reasoning = generate_reasoning(market, team)

    return (
        f"📊 *{market.upper()} BET*\n\n"
        f"🔥 *Pick:* **{team_line}**\n"
        f"💵 *Odds:* {odds_str}\n"
        f"📈 *Expected Value:* **+{ev:.1f}%**\n"
        f"{label}\n\n"
        f"🕒 *Game Time:* {readable_time}\n"
        f"💡 *Why We Like It:*\n{reasoning}\n"
        f"——————"
    )

def send_telegram_message(message):
    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
    except telegram.error.TelegramError as e:
        print(f"Telegram error: {e}")

def save_result_log(entry):
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, 'w') as f:
            json.dump([], f)

    with open(RESULTS_FILE, 'r+') as f:
        data = json.load(f)
        data.append(entry)
        f.seek(0)
        json.dump(data, f, indent=2)

def check_and_update_results():
    print("🔄 Checking for resolved bets...")

    now = datetime.utcnow()
    if not os.path.exists(RESULTS_FILE):
        return

    with open(RESULTS_FILE, "r+") as f:
        results = json.load(f)

    updated = []
    for entry in results:
        if entry.get("resolved"):
            continue

        start = datetime.fromisoformat(entry["game_time"])
        if now - start >= timedelta(hours=12):  # Game should be done
            score_url = f"https://api.the-odds-api.com/v4/sports/{entry['sport']}/scores"
            params = {"apiKey": API_KEY, "daysFrom": 2}
            try:
                r = requests.get(score_url, params=params)
                r.raise_for_status()
                scores = r.json()

                for game in scores:
                    if game.get("home_team") == entry["home"] and game.get("away_team") == entry["away"]:
                        home_score = game.get("scores", {}).get("home_score", 0)
                        away_score = game.get("scores", {}).get("away_score", 0)
                        outcome = "push"

                        if entry["market"] == "h2h":
                            if entry["pick"] == entry["home"] and home_score > away_score:
                                outcome = "won"
                            elif entry["pick"] == entry["away"] and away_score > home_score:
                                outcome = "won"
                            else:
                                outcome = "lost"
                        elif entry["market"] == "totals":
                            total = home_score + away_score
                            if entry["type"] == "over" and total > entry["line"]:
                                outcome = "won"
                            elif entry["type"] == "under" and total < entry["line"]:
                                outcome = "won"
                            elif total == entry["line"]:
                                outcome = "push"
                            else:
                                outcome = "lost"
                        # TODO: Add spread support if needed

                        entry["result"] = outcome
                        entry["resolved"] = True
                        print(f"📌 Logged result for {entry['pick']}: {outcome}")
                        break

            except Exception as e:
                print(f"❌ Error checking scores: {e}")

    # Save updated list
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)

def main():
    sent_any = False
    for sport in SPORTS:
        games = fetch_odds_for_sport(sport)
        filtered_games = filter_today_games(games)

        for game in filtered_games:
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    market_key = market['key']
                    best_outcome = None
                    best_ev = -999

                    for outcome in market.get('outcomes', []):
                        odds = outcome.get('price')
                        if odds is None:
                            continue

                        win_prob = 0.5  # Placeholder
                        ev = calculate_ev(odds, win_prob)
                        if ev > best_ev:
                            best_ev = ev
                            best_outcome = outcome

                    if best_outcome and best_ev >= 3.0:
                        message = format_message(
                            game,
                            market_key,
                            best_outcome,
                            best_outcome['price'],
                            best_ev,
                            game['commence_time']
                        )
                        send_telegram_message(message)
                        sent_any = True

                        save_result_log({
                            "sport": sport,
                            "market": market_key,
                            "pick": best_outcome.get("name", ""),
                            "home": game.get("home_team"),
                            "away": game.get("away_team"),
                            "line": best_outcome.get("point", 0),
                            "type": "over" if "over" in best_outcome.get("name", "").lower() else "under" if "under" in best_outcome.get("name", "").lower() else None,
                            "game_time": game['commence_time'],
                            "resolved": False
                        })

    if not sent_any:
        print("✅ Script ran but no value bets were found.")
    else:
        print("✅ Bets sent successfully.")

    check_and_update_results()

if __name__ == "__main__":
    main()
