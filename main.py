import requests
from datetime import datetime, timedelta
import pytz
import os

# ✅ Your actual credentials
ODDS_API_KEY = '7b5d540e73c8790a95b84d3713e1a572'
TELEGRAM_TOKEN = '7031551190:AAGn-XiQt_XYduf3Pbgl4GzFym-2-YhAG5A'
TELEGRAM_CHAT_ID = '6212506988'

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram error:", e)

def estimated_win_prob(odds, team):
    if odds >= 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def calculate_ev_and_label(odds, model_win_prob, spread, team_name):
    if odds > 0:
        implied_prob = 100 / (odds + 100)
        win_payout = odds
    else:
        implied_prob = abs(odds) / (abs(odds) + 100)
        win_payout = 10000 / abs(odds)

    spread_based_prob = 0.5 - (spread / 22.0)
    spread_based_prob = max(0.05, min(0.95, spread_based_prob))
    adjusted_win_prob = min(model_win_prob, spread_based_prob + 0.05)

    risky_teams = ['Valkyries', 'G League Ignite', 'Team USA Youth']
    if any(team in team_name for team in risky_teams):
        adjusted_win_prob = min(adjusted_win_prob, 0.20)

    lose_payout = 100
    ev = (adjusted_win_prob * win_payout) - ((1 - adjusted_win_prob) * lose_payout)
    ev_percent = round(ev / 100, 4)

    if ev_percent >= 0.05:
        label = "🟢 BEST VALUE"
    elif ev_percent >= 0.015:
        label = "🟡 GOOD VALUE"
    elif ev_percent > 0:
        label = "🟠 SLIGHT EDGE"
    else:
        label = "🔴 NO EDGE"

    implied_prob_percent = round(implied_prob * 100, 2)
    model_prob_percent = round(adjusted_win_prob * 100, 2)
    prob_delta = round((adjusted_win_prob - implied_prob) * 100, 2)

    return ev_percent, adjusted_win_prob, label, implied_prob_percent, model_prob_percent, prob_delta

def generate_reasoning(market, team_name):
    if market == "h2h":
        return f"{team_name} has value based on our win probability model exceeding the implied odds."
    elif market == "spreads":
        return f"{team_name} has a favorable spread line compared to their expected margin."
    elif market == "totals":
        return f"Market mispriced the total line for {team_name}, based on game pace and recent trends."
    return "Strong edge detected based on pricing and model projection."

def format_message(game, market, outcome, odds, ev_percent, label, implied_prob, model_prob, delta, start_time):
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
    reasoning = generate_reasoning(market, team)

    return (
        f"📊 *{market.upper()} BET*\n\n"
        f"🔥 *Pick:* **{team_line}**\n"
        f"💵 *Odds:* {odds_str}\n"
        f"📈 *Expected Value:* **{ev_percent*100:+.1f}%**\n"
        f"{label}\n\n"
        f"📊 *Win Probability:* {model_prob:.2f}% vs Implied: {implied_prob:.2f}%\n"
        f"📉 *Edge:* {delta:+.2f}% difference\n\n"
        f"🕒 *Game Time:* {readable_time}\n"
        f"💡 *Why We Like It:*\n{reasoning}\n"
        f"——————"
    )

def find_best_bet(game):
    best_bets = {"h2h": None, "spreads": None, "totals": None}
    for bookmaker in game.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            key = market["key"]
            for outcome in market.get("outcomes", []):
                odds = outcome.get("price")
                team_name = outcome.get("name")
                spread = outcome.get("point", 0.0)

                if odds is None or team_name is None:
                    continue

                model_win_prob = estimated_win_prob(odds, team_name)
                ev, win_prob, label, implied_prob, model_prob, delta = calculate_ev_and_label(
                    odds, model_win_prob, spread, team_name
                )

                outcome_data = {
                    "outcome": outcome,
                    "odds": odds,
                    "ev": ev,
                    "label": label,
                    "implied_prob": implied_prob,
                    "model_prob": model_prob,
                    "delta": delta
                }

                current_best = best_bets[key]
                if current_best is None or ev > current_best["ev"]:
                    best_bets[key] = outcome_data
    return best_bets

def fetch_games():
    url = f"https://api.the-odds-api.com/v4/sports/?apiKey={ODDS_API_KEY}"
    sports = requests.get(url).json()

    target_keys = ['basketball.wnba', 'soccer.usa.nwsl', 'soccer.usa.mls', 'baseball.mlb']
    events = []

    for sport in sports:
        if sport["key"] in target_keys:
            odds_url = f"https://api.the-odds-api.com/v4/sports/{sport['key']}/odds/?apiKey={ODDS_API_KEY}&regions=us&markets=h2h,spreads,totals&oddsFormat=american"
            try:
                response = requests.get(odds_url)
                data = response.json()
                for game in data:
                    start_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00')).astimezone(pytz.timezone('US/Eastern'))
                    now = datetime.now(pytz.timezone('US/Eastern'))
                    if now.date() <= start_time.date() <= (now + timedelta(days=1)).date():
                        events.append(game)
            except Exception as e:
                print(f"Error fetching {sport['key']}:", e)

    return events

def main():
    games = fetch_games()
    if not games:
        send_telegram_message("⚠️ No games found today.")
        return

    for game in games:
        league = game.get("sport_title", "Unknown League")
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        header_message = f"🏟️ *{league}*\n\n📢 {away} @ {home}\n\n"
        best_bets = find_best_bet(game)

        for market_key in ["h2h", "spreads", "totals"]:
            best = best_bets.get(market_key)
            if best:
                msg = format_message(
                    game, market_key, best["outcome"], best["odds"],
                    best["ev"], best["label"],
                    best["implied_prob"], best["model_prob"], best["delta"],
                    game['commence_time']
                )
                send_telegram_message(header_message + msg)
            else:
                send_telegram_message(header_message + f"⚠️ No best {market_key.upper()} bet found.\n——————")

if __name__ == "__main__":
    main()
