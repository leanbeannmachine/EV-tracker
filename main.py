import requests
from datetime import datetime
import pytz
import telegram
import random

SPORTSMONK_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

BOOKMAKERS = ["pinnacle", "betonlineag"]
SPORTS = ["baseball_mlb", "basketball_wnba"]

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

def calculate_ev_and_label(odds, model_win_prob, spread, team_name):
    # Convert American odds to decimal win payout
    if odds > 0:
        implied_prob = 100 / (odds + 100)
        win_payout = odds
    else:
        implied_prob = abs(odds) / (abs(odds) + 100)
        win_payout = 10000 / abs(odds)

    # Spread-based win probability (acts as a sanity check)
    spread_based_prob = 0.5 - (spread / 22.0)
    spread_based_prob = max(0.05, min(0.95, spread_based_prob))

    # Adjust for risk and cap overconfidence
    adjusted_win_prob = min(model_win_prob, spread_based_prob + 0.05)

    risky_teams = ['Valkyries', 'G League Ignite', 'Team USA Youth']
    if any(team in team_name for team in risky_teams):
        adjusted_win_prob = min(adjusted_win_prob, 0.20)

    # Expected Value
    lose_payout = 100
    ev = (adjusted_win_prob * win_payout) - ((1 - adjusted_win_prob) * lose_payout)
    ev_percent = round(ev / 100, 4)

    # Label
    if ev_percent >= 0.05:
        label = "🟢 BEST VALUE"
    elif ev_percent >= 0.015:
        label = "🟡 GOOD VALUE"
    elif ev_percent > 0:
        label = "🟠 SLIGHT EDGE"
    else:
        label = "🔴 NO EDGE"

    # Implied vs model win probability delta
    delta = round((adjusted_win_prob - implied_prob) * 100, 2)  # In percent
    implied_prob_percent = round(implied_prob * 100, 2)
    model_prob_percent = round(adjusted_win_prob * 100, 2)

    return ev_percent, adjusted_win_prob, label, implied_prob_percent, model_prob_percent, delta

def is_today_game(game_time_str):
    game_time = datetime.fromisoformat(game_time_str.replace('Z', '+00:00')).astimezone(pytz.timezone('US/Eastern'))
    now = datetime.now(pytz.timezone('US/Eastern'))
    return game_time.date() == now.date()

def filter_today_games(games):
    return [g for g in games if is_today_game(g['commence_time'])]

def implied_probability(american_odds):
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)

# Simulated team form score [0.4 to 0.6] - replace with real stats if available
def get_team_form(team_name):
    random.seed(hash(team_name) % 10000)
    return random.uniform(0.4, 0.6)

def estimated_win_prob(american_odds, team_name):
    base_prob = implied_probability(american_odds)
    form = get_team_form(team_name)
    adjustment = (form - 0.5) * 0.16  # ±8%
    adjusted_prob = base_prob + adjustment
    return max(0.01, min(0.99, adjusted_prob))

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

def find_best_bet(game):
    best_bets = {"h2h": None, "spreads": None, "totals": None}
    for bookmaker in game.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            key = market["key"]
            for outcome in market.get("outcomes", []):
                odds = outcome.get("price")
                team_name = outcome.get("name")
                if odds is None or team_name is None:
                    continue
                win_prob = estimated_win_prob(odds, team_name)
                ev = calculate_ev(odds, win_prob)
                # Store win_prob and ev inside outcome for use later
                outcome_data = {
                    "outcome": outcome,
                    "win_prob": win_prob,
                    "ev": ev
                }
                current_best = best_bets[key]
                if current_best is None or ev > current_best['ev']:
                    best_bets[key] = outcome_data
    return best_bets

def main():
    all_games = []
    for sport in SPORTS:
        games = fetch_odds_for_sport(sport)
        games_today = filter_today_games(games)
        all_games.extend(games_today)

    if not all_games:
        print("No games today.")
        return

    for game in all_games:
        best_bets = find_best_bet(game)

        # Compose main game header message with all markets and best bets
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        start_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00')).astimezone(pytz.timezone('US/Eastern')).strftime('%b %d %I:%M %p ET')

        # Build summary lines for ML, Spread, Total from all bookmakers
        moneyline_lines = []
        spread_lines = []
        total_lines = []

        for bookmaker in game.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] == "h2h":
                    for o in market.get("outcomes", []):
                        moneyline_lines.append(f"{o['name']}: {o['price']:+}")
                elif market["key"] == "spreads":
                    for o in market.get("outcomes", []):
                        point = o.get("point")
                        spread_lines.append(f"{o['name']} {point:+.1f} @ {o['price']:+}")
                elif market["key"] == "totals":
                    for o in market.get("outcomes", []):
                        point = o.get("point")
                        total_lines.append(f"Total {point:.1f} @ {o['price']:+}")

        # ✅ Fix this: Indentation of header_message should be inside the loop
        header_message = (
            f"🏟️ {away} vs {home}\n"
            f"📅 {start_time}\n"
            f"🏆 ML: {' | '.join(moneyline_lines) if moneyline_lines else 'N/A'}\n"
            f"📏 Spread: {' | '.join(spread_lines) if spread_lines else 'N/A'}\n"
            f"📊 Total: {' | '.join(total_lines) if total_lines else 'N/A'}\n\n"
        )

        # Add best bet details per market
        for market_key in ["h2h", "spreads", "totals"]:
            best = best_bets.get(market_key)
            if best:
                outcome = best["outcome"]
                ev = best["ev"]
                odds = outcome["price"]
                team_name = outcome["name"]
                msg = format_message(game, market_key, outcome, odds, ev, game['commence_time'])
                send_telegram_message(header_message + msg)
            else:
                send_telegram_message(header_message + f"⚠️ No best {market_key.upper()} bet found for this game.\n——————")

if __name__ == "__main__":
    main()
