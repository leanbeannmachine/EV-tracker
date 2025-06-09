import requests
from datetime import datetime, timezone
import math
import time
import sys
import pytz
import os

# Telegram Bot config
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
# Odds API config
SPORTSMONK_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
SPORT_KEY = 'baseball_mlb'  # change as needed

def fetch_odds_api_bets():
    """Fetch today's odds from The Odds API for MLB with ML, spreads, totals"""
    url = f'https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds'
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'h2h,spreads,totals',
        'oddsFormat': 'american',
        'dateFormat': 'iso',
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"🚨 API fetch error: {e}", file=sys.stderr)
        return []

    today = datetime.now(timezone.utc).date()
    games_today = []

    for game in data:
        commence_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
        if commence_time.date() == today:
            games_today.append(game)

    return games_today

def american_to_decimal(odds):
    """Convert American odds to decimal odds"""
    if odds > 0:
        return 1 + (odds / 100)
    else:
        return 1 + (100 / abs(odds))

def implied_probability(odds):
    """Calculate implied probability from American odds"""
    dec = american_to_decimal(odds)
    return 1 / dec

def calc_ev(win_prob, odds):
    """Calculate Expected Value percentage"""
    imp_prob = implied_probability(odds)
    return (win_prob - imp_prob) * 100  # as percentage difference

def calculate_best_bets(game):
    best_bets = {}

    try:
        markets = game.get('bookmakers', [{}])[0].get('markets', {})

        # ----- Moneyline (ML) -----
        if 'h2h' in markets and 'outcomes' in markets['h2h']:
            ml_outcomes = markets['h2h']['outcomes']
            best_ml = max(ml_outcomes, key=lambda x: x.get('win_prob', 0) - x.get('implied_prob', 0))
            ml_diff = best_ml.get('win_prob', 0) - best_ml.get('implied_prob', 0)
            if ml_diff >= 0.05:  # 5% EV threshold
                best_bets['ml'] = {
                    'team': best_ml['name'],
                    'price': best_ml['price'],
                    'win_prob': best_ml.get('win_prob'),
                    'implied_prob': best_ml.get('implied_prob'),
                    'diff': ml_diff
                }

        # ----- Spread -----
        if 'spreads' in markets and 'outcomes' in markets['spreads']:
            spread_outcomes = markets['spreads']['outcomes']
            best_spread = max(spread_outcomes, key=lambda x: x.get('win_prob', 0) - x.get('implied_prob', 0))
            spread_diff = best_spread.get('win_prob', 0) - best_spread.get('implied_prob', 0)
            if spread_diff >= 0.02:  # 2% EV threshold
                best_bets['spread'] = {
                    'team': best_spread['name'],
                    'price': best_spread['price'],
                    'point': best_spread.get('point', 'N/A'),
                    'win_prob': best_spread.get('win_prob'),
                    'implied_prob': best_spread.get('implied_prob'),
                    'diff': spread_diff
                }

        # ----- Total (Over/Under) -----
        if 'totals' in markets and 'outcomes' in markets['totals']:
            total_outcomes = markets['totals']['outcomes']
            best_total = max(total_outcomes, key=lambda x: x.get('win_prob', 0) - x.get('implied_prob', 0))
            total_diff = best_total.get('win_prob', 0) - best_total.get('implied_prob', 0)
            if total_diff >= 0.02:  # 2% EV threshold
                best_bets['total'] = {
                    'side': best_total['name'],
                    'price': best_total['price'],
                    'point': best_total.get('point', 'N/A'),
                    'win_prob': best_total.get('win_prob'),
                    'implied_prob': best_total.get('implied_prob'),
                    'diff': total_diff
                }

    except Exception as e:
        print(f"⚠️ Error calculating best bets: {e}")

    return best_bets

def format_bet_message(game, best_bets):
    """Format the Telegram message with rich emojis and clear structure"""
    # Extract some basics
    commence_time = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
    dt_str = commence_time.strftime('%b %d %I:%M %p %Z')
    teams = game['home_team'] + " vs " + game['away_team']

    # Markets (ML, Spread, Total) - show full lines for clarity
    bookmaker = game['bookmakers'][0]
    markets = {m['key']: m for m in bookmaker['markets']}

    def format_american(odds):
        return f"{odds:+}" if odds > 0 else f"{odds}"

    # ML line
    ml_line = []
    if 'h2h' in markets:
        for o in markets['h2h']['outcomes']:
            ml_line.append(f"{o['name']}: {format_american(o['price'])}")
    ml_str = " | ".join(ml_line)

    # Spread line
    spread_str = ""
    if 'spreads' in markets:
        spread_pts = markets['spreads']['points']
        spread_outcomes = markets['spreads']['outcomes']
        spread_parts = []
        for o in spread_outcomes:
            spread_parts.append(f"{o['name']} {spread_pts} @ {format_american(o['price'])}")
        spread_str = " | ".join(spread_parts)

    # Total line
    total_str = ""
    if 'totals' in markets:
        total_pts = markets['totals']['points']
        total_outcomes = markets['totals']['outcomes']
        total_parts = []
        for o in total_outcomes:
            total_parts.append(f"{o['name']} {total_pts} @ {format_american(o['price'])}")
        total_str = " | ".join(total_parts)

    # Build best bet lines with emojis & stats
    lines = []
    if 'ml' in best_bets:
        b = best_bets['ml']
        lines.append(f"🏆 *Moneyline Best Bet*: {b['team']} @ {format_american(b['odds'])} "
                     f"(Win Prob {b['win_prob']}% vs Implied {b['implied_prob']}% | Diff {b['ev_diff']}%)")
    if 'spread' in best_bets:
        b = best_bets['spread']
        lines.append(f"📏 *Spread Best Bet*: {b['team']} {b['point']} @ {format_american(b['odds'])} "
                     f"(Win Prob {b['win_prob']}% vs Implied {b['implied_prob']}% | Diff {b['ev_diff']}%)")
    if 'total' in best_bets:
        b = best_bets['total']
        lines.append(f"📊 *Total Best Bet*: {b['side']} {b['point']} @ {format_american(b['odds'])} "
                     f"(Win Prob {b['win_prob']}% vs Implied {b['implied_prob']}% | Diff {b['ev_diff']}%)")

    # Compose message
    message = (
        f"🟢 *{teams}*\n"
        f"📅 {dt_str}\n"
        f"🏆 ML: {ml_str}\n"
        f"📏 Spread: {spread_str}\n"
        f"📊 Total: {total_str}\n"
        f"✅ Best Bets:\n" +
        "\n".join(lines)
    )

    return message

def send_telegram_message(message):
    """Send the formatted message to Telegram chat"""
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        resp = requests.post(url, data=payload, timeout=10)
        resp.raise_for_status()
        print(f"✅ Telegram message sent")
    except Exception as e:
        print(f"🚨 Telegram send error: {e}", file=sys.stderr)

def main():
    print("🚀 Fetching odds from API...")
    games_today = fetch_odds_api_bets()
    if not games_today:
        print("⚠️ No games today or fetch failed.")
        return

    for game in games_today:
        best_bets = calculate_best_bets(game)
        if best_bets:
            message = format_bet_message(game, best_bets)
            send_telegram_message(message)
            time.sleep(1)  # avoid hammering Telegram API

if __name__ == "__main__":
    main()
