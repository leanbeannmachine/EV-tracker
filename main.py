import os
import re
import requests
from datetime import datetime
from pytz import timezone

# === ENVIRONMENT VARIABLES ===
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
ODDS_API_KEY = "25af17e62a8d221b05b9b5c5a4911cdb"

# === CONSTANTS ===
CENTRAL = timezone('US/Central')
SPORT_KEY = 'baseball_mlb'
BOOKMAKER_KEY = 'draftkings'

# === UTILITY FUNCTIONS ===
def decimal_to_american(decimal_odds):
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))

def calculate_implied_probability(decimal_odds):
    return 1 / decimal_odds

def calculate_vig(implied_probs):
    total = sum(implied_probs)
    return total - 1

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
    """
    Escapes characters for MarkdownV2 formatting required by Telegram.
    """
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', str(text))

# === TELEGRAM ALERT FUNCTION ===
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

# === FORMATTER ===
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

# === MAIN FUNCTION ===
def process_games():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds"
    params = {
        'apiKey': ODDS_API_KEY,
        'regions': 'us',
        'markets': 'h2h,spreads,totals',
        'bookmakers': BOOKMAKER_KEY
    }
    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        print(f"Failed to fetch odds: {resp.status_code} {resp.text}")
        return
    
    games = resp.json()
    print(f"Status: {resp.status_code} Remaining: {resp.headers.get('x-requests-remaining')}")
    print(f"Game count: {len(games)}")
    
    for game in games:
        try:
            home = game['home_team']
            away = game['away_team']
            commence = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00')).astimezone(CENTRAL)
            commence_str = commence.strftime('%m/%d %I:%M %p CDT')

            bookmaker = next((b for b in game['bookmakers'] if b['key'] == BOOKMAKER_KEY), None)
            if bookmaker is None:
                continue

            markets = {m['key']: m for m in bookmaker['markets']}

            if 'h2h' not in markets or 'spreads' not in markets or 'totals' not in markets:
                continue

            # Moneyline
            h2h = markets['h2h']['outcomes']
            ml_odds = {o['name']: o['price'] for o in h2h}
            if home not in ml_odds or away not in ml_odds:
                continue

            # Spreads
            spreads = markets['spreads']['outcomes']
            spread_odds = {o['name']: {'price': o['price'], 'point': o['point']} for o in spreads}
            if home not in spread_odds or away not in spread_odds:
                continue

            # Totals
            totals = markets['totals']['outcomes']
            if 'Over' not in [o['name'] for o in totals] or 'Under' not in [o['name'] for o in totals]:
                continue
            total_point = totals[0]['point']
            total_odds = {o['name']: o['price'] for o in totals}

            # Model
            home_prob, away_prob = get_model_probabilities(home, away)

            # Vig
            vig_ml = calculate_vig([
                calculate_implied_probability(ml_odds[home]),
                calculate_implied_probability(ml_odds[away])
            ])
            vig_spread = calculate_vig([
                calculate_implied_probability(spread_odds[home]['price']),
                calculate_implied_probability(spread_odds[away]['price'])
            ])
            vig_total = calculate_vig([
                calculate_implied_probability(total_odds['Over']),
                calculate_implied_probability(total_odds['Under'])
            ])

            # Moneyline best bet
            ml_bets = []
            for team, prob in zip([home, away], [home_prob, away_prob]):
                odds = ml_odds[team]
                implied_prob = calculate_implied_probability(odds)
                ev = calculate_ev(prob, odds)
                edge = calculate_edge(prob, implied_prob)
                if ev > 0:
                    ml_bets.append({
                        'pick': team,
                        'odds': odds,
                        'ev': ev,
                        'implied_prob': implied_prob,
                        'model_prob': prob,
                        'edge': edge,
                        'vig': vig_ml
                    })
            if not ml_bets:
                continue
            best_ml = max(ml_bets, key=lambda b: b['ev'])

            # Spread best bet
            spread_bets = []
            for team in [home, away]:
                odds = spread_odds[team]['price']
                point = spread_odds[team]['point']
                prob = home_prob if team == home else away_prob
                implied_prob = calculate_implied_probability(odds)
                ev = calculate_ev(prob, odds)
                edge = calculate_edge(prob, implied_prob)
                if ev > 0:
                    spread_bets.append({
                        'pick': f"{team} {point:+}",
                        'odds': odds,
                        'ev': ev,
                        'implied_prob': implied_prob,
                        'model_prob': prob,
                        'edge': edge,
                        'vig': vig_spread
                    })
            if not spread_bets:
                continue
            best_spread = max(spread_bets, key=lambda b: b['ev'])

            # Totals best bet
            total_bets = []
            for side in ['Over', 'Under']:
                odds = total_odds[side]
                implied_prob = calculate_implied_probability(odds)
                model_total_prob = 0.55 if (home_prob + away_prob) > 1.05 else 0.45
                if side == 'Under':
                    model_total_prob = 1 - model_total_prob
                ev = calculate_ev(model_total_prob, odds)
                edge = calculate_edge(model_total_prob, implied_prob)
                if ev > 0:
                    total_bets.append({
                        'pick': f"{side} {total_point}",
                        'odds': odds,
                        'ev': ev,
                        'implied_prob': implied_prob,
                        'model_prob': model_total_prob,
                        'edge': edge,
                        'vig': vig_total
                    })
            if not total_bets:
                continue
            best_total = max(total_bets, key=lambda b: b['ev'])

            # Format messages
            header = f"⚾ *{away}* @ *{home}*\n🕒 {commence_str}\n\n"

sections = []

ml_section = format_bet_section('moneyline', best_ml['pick'], best_ml['odds'], best_ml['ev'], best_ml['implied_prob'], best_ml['model_prob'], best_ml['edge'], best_ml['vig'])
if ml_section:
    sections.append(ml_section)

spread_section = format_bet_section('spread', best_spread['pick'], best_spread['odds'], best_spread['ev'], best_spread['implied_prob'], best_spread['model_prob'], best_spread['edge'], best_spread['vig'])
if spread_section:
    sections.append(spread_section)

total_section = format_bet_section('total', best_total['pick'], best_total['odds'], best_total['ev'], best_total['implied_prob'], best_total['model_prob'], best_total['edge'], best_total['vig'])
if total_section:
    sections.append(total_section)

# Only send if at least one valid bet
if not sections:
    continue

message = header + "\n\n".join(sections)
send_alert(message)

        except Exception as e:
            print(f"Error processing game {game.get('away_team')} vs {game.get('home_team')}: {e}")
            
if __name__ == '__main__':
    process_games()
