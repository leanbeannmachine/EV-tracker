import os
import re
import requests
from datetime import datetime
import pytz
from pytz import timezone

# === ENVIRONMENT VARIABLES ===
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
API_KEY = "25af17e62a8d221b05b9b5c5a4911cdb"

CENTRAL = timezone('US/Central')
SPORT_KEY = 'baseball_mlb'
BOOKMAKER_KEY = 'draftkings'

def decimal_to_american(decimal_odds):
    if decimal_odds >= 2.0:
        return f"+{int((decimal_odds - 1) * 100)}"
    else:
        return f"{int(-100 / (decimal_odds - 1))}"

def calculate_implied_probability(decimal_odds):
    return 1 / decimal_odds

def calculate_vig(implied_probs):
    return max(0, sum(implied_probs) - 1)

def calculate_ev(model_prob, decimal_odds):
    return (model_prob * (decimal_odds - 1)) - (1 - model_prob)

def calculate_edge(model_prob, implied_prob):
    return model_prob - implied_prob

def get_model_probabilities(home_team, away_team):
    home_score = sum(ord(c) for c in home_team.lower())
    away_score = sum(ord(c) for c in away_team.lower())
    total = home_score + away_score
    home_prob = home_score / total
    away_prob = away_score / total
    return home_prob, away_prob

def escape_markdown(text):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

def send_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'MarkdownV2'
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print(f"Telegram send failed: {response.text}")

def fetch_games():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds?regions=us&markets=h2h,spreads,totals&oddsFormat=decimal&bookmakers={BOOKMAKER_KEY}&apiKey={API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Failed to fetch odds: {response.text}")
        return []

    data = response.json()
    games = []

    for game in data:
        try:
            if not game.get('bookmakers'):
                continue

            bookmaker = game['bookmakers'][0]
            markets = bookmaker['markets']

            home = game['home_team']
            away = game['away_team']
            commence = game['commence_time']

            moneyline = {}
            spreads = []
            totals = []

            for market in markets:
                if market['key'] == 'h2h':
                    for outcome in market['outcomes']:
                        moneyline[outcome['name']] = outcome['price']
                elif market['key'] == 'spreads':
                    for outcome in market['outcomes']:
                        spreads.append({
                            'name': outcome['name'],
                            'point': outcome['point'],
                            'price': outcome['price']
                        })
                elif market['key'] == 'totals':
                    for outcome in market['outcomes']:
                        totals.append({
                            'name': outcome['name'],
                            'point': outcome['point'],
                            'price': outcome['price']
                        })

            games.append({
                'home_team': home,
                'away_team': away,
                'commence_time': datetime.strptime(commence, "%Y-%m-%dT%H:%M:%SZ").timestamp(),
                'moneyline': moneyline,
                'spreads': spreads,
                'totals': totals
            })

        except Exception as e:
            print(f"Error parsing game: {e}")
            continue

    return games

def get_best_bet(bet_list, bet_type, home_team=None, away_team=None):
    if not bet_list:
        return None

    best_bet = None
    best_ev = 0

    implied_probs = []
    for bet in bet_list:
        price = bet.get('price')
        if price is None:
            continue
        implied_probs.append(calculate_implied_probability(price))

    vig = calculate_vig(implied_probs) if len(implied_probs) >= 2 else 0

    for bet in bet_list:
        pick = bet.get('name')
        price = bet.get('price')
        if pick is None or price is None:
            continue

        implied_prob = calculate_implied_probability(price)

        if bet_type == 'moneyline':
            model_home, model_away = get_model_probabilities(home_team, away_team)
            model_prob = model_home if pick == home_team else model_away
        elif bet_type == 'spread':
            model_prob = 0.55  # placeholder for spread model confidence
        elif bet_type == 'total':
            model_prob = 0.665 if pick.lower() == 'over' else 0.335
        else:
            model_prob = 0.5

        ev = calculate_ev(model_prob, price)
        edge = calculate_edge(model_prob, implied_prob)

        if ev > best_ev and ev > 0:
            best_ev = ev
            best_bet = {
                'pick': pick,
                'odds_decimal': price,
                'implied_prob': implied_prob,
                'model_prob': model_prob,
                'ev': ev,
                'edge': edge,
                'vig': vig,
                'point': bet.get('point')
            }

    return best_bet

def format_bet_section(bet_type, pick, odds_decimal, ev, implied_prob, model_prob, edge, vig):
    odds_american = decimal_to_american(odds_decimal)
    ev_pct = round(ev * 100, 1)
    implied_pct = round(implied_prob * 100, 1)
    model_pct = round(model_prob * 100, 1)
    edge_pct = round(edge * 100, 1)
    vig_pct = round(vig * 100, 2)

    if ev <= 0:
        return None

    emoji_map = {
        'moneyline': '💰',
        'spread': '📉',
        'total': '⚖️'
    }
    emoji = emoji_map.get(bet_type, '📊')
    value_label = "💎🟢 BEST VALUE" if ev_pct > 5 else "⚠️ GOOD VALUE"

    section = (
        f"{emoji} *{escape_markdown(bet_type.upper())} BET*\n"
        f"⚠️ Pick: {escape_markdown(pick)}\n"
        f"💵 Odds: {escape_markdown(odds_american)}\n"
        f"📈 EV: {escape_markdown(ev_pct)}% {escape_markdown(value_label)}\n"
        f"🧮 Implied Prob: {escape_markdown(implied_pct)}%\n"
        f"🧠 Model Prob: {escape_markdown(model_pct)}%\n"
        f"🔍 Edge: {escape_markdown(edge_pct)}%\n"
        f"⚖️ Vig: {escape_markdown(vig_pct)}%\n"
        f"⚾ ——————"
    )
    return section

def process_games(games):
    for game in games:
        try:
            teams = f"{game['away_team']} @ {game['home_team']}"
            game_time_cdt = datetime.fromtimestamp(game['commence_time'], tz=pytz.utc).astimezone(CENTRAL)
            game_time_str = game_time_cdt.strftime("%m/%d %I:%M %p CDT")

            header = f"⚾ {escape_markdown(teams)}\n🕒 {escape_markdown(game_time_str)}\n"

            best_ml = get_best_bet([{ 'name': k, 'price': v } for k, v in game['moneyline'].items()], 'moneyline', home_team=game['home_team'], away_team=game['away_team'])
            best_spread = get_best_bet(game['spreads'], 'spread')
            best_total = get_best_bet(game['totals'], 'total')

            sections = []

            if best_ml:
                sections.append(format_bet_section(
                    'moneyline', best_ml['pick'], best_ml['odds_decimal'], best_ml['ev'],
                    best_ml['implied_prob'], best_ml['model_prob'], best_ml['edge'], best_ml['vig']
                ))

            if best_spread:
                spread_pick = f"{best_spread['pick']} {best_spread['point']}"
                sections.append(format_bet_section(
                    'spread', spread_pick, best_spread['odds_decimal'], best_spread['ev'],
                    best_spread['implied_prob'], best_spread['model_prob'], best_spread['edge'], best_spread['vig']
                ))

            if best_total:
                total_pick = f"{best_total['pick']} {best_total['point']}"
                sections.append(format_bet_section(
                    'total', total_pick, best_total['odds_decimal'], best_total['ev'],
                    best_total['implied_prob'], best_total['model_prob'], best_total['edge'], best_total['vig']
                ))

            if any(sections):
                message = header + "\n\n" + "\n\n".join(filter(None, sections))
                send_alert(message)

        except Exception as e:
            print(f"Error processing game {game.get('home_team')} vs {game.get('away_team')}: {e}")

# === MAIN ENTRY ===
if __name__ == '__main__':
    games = fetch_games()
    if games:
        process_games(games)
