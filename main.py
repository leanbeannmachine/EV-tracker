import os
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
    """
    Placeholder for a model that returns realistic win probabilities.
    Here we simulate by comparing team names alphabetically,
    but you can replace this with actual ML/statistical models.
    Returns tuple: (home_prob, away_prob) summing to 1.
    """
    # Example simplistic model logic:
    home_score = sum(ord(c) for c in home_team.lower())
    away_score = sum(ord(c) for c in away_team.lower())
    total = home_score + away_score
    home_prob = home_score / total
    away_prob = away_score / total
    return home_prob, away_prob

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

# === FORMATTERS ===
def format_bet_section(bet_type, pick, odds_decimal, ev, implied_prob, model_prob, edge, vig):
    odds_american = decimal_to_american(odds_decimal)
    ev_pct = round(ev * 100, 1)
    implied_pct = round(implied_prob * 100, 1)
    model_pct = round(model_prob * 100, 1)
    edge_pct = round(edge * 100, 1)
    vig_pct = round(vig * 100, 2)
    
    # Only show if EV positive (good or best value)
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
        f"{emoji} *{bet_type.upper()} BET*\n"
        f"⚠️ Pick: {pick}\n"
        f"💵 Odds: {odds_american}\n"
        f"📈 EV: {ev_pct}% {value_label}\n"
        f"🧮 Implied Prob: {implied_pct}%\n"
        f"🧠 Model Prob: {model_pct}%\n"
        f"🔍 Edge: {edge_pct}%\n"
        f"⚖️ Vig: {vig_pct}%\n"
        "⚾ ——————"
    )
    return section

# === MAIN PROCESSING ===
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

            # Extract DraftKings bookmaker odds
            bookmaker = next((b for b in game['bookmakers'] if b['key'] == BOOKMAKER_KEY), None)
            if bookmaker is None:
                print(f"❌ DraftKings odds not available for {away} vs {home}")
                continue

            # Parse markets
            markets = {m['key']: m for m in bookmaker['markets']}

            # Parse odds for moneyline
            if 'h2h' not in markets:
                print(f"❌ Moneyline not available for {away} vs {home}")
                continue
            h2h = markets['h2h']['outcomes']
            ml_odds = {o['name']: o['price'] for o in h2h}
            if home not in ml_odds or away not in ml_odds:
                print(f"❌ Moneyline odds missing teams for {away} vs {home}")
                continue

            # Parse spreads
            if 'spreads' not in markets:
                print(f"❌ Spread not available for {away} vs {home}")
                continue
            spreads = markets['spreads']['outcomes']
            spread_odds = {o['name']: {'price': o['price'], 'point': o['point']} for o in spreads}
            if home not in spread_odds or away not in spread_odds:
                print(f"❌ Spread odds missing teams for {away} vs {home}")
                continue

            # Parse totals
            if 'totals' not in markets:
                print(f"❌ Totals not available for {away} vs {home}")
                continue
            totals = markets['totals']['outcomes']
            total_point = totals[0]['point']  # both over and under share same point
            total_odds = {o['name']: o['price'] for o in totals}
            if 'Over' not in total_odds or 'Under' not in total_odds:
                print(f"❌ Totals odds missing for {away} vs {home}")
                continue

            # Get model probabilities
            home_prob, away_prob = get_model_probabilities(home, away)

            # Calculate implied probs and vig
            implied_ml_probs = [calculate_implied_probability(ml_odds[home]),
                                calculate_implied_probability(ml_odds[away])]
            vig_ml = calculate_vig(implied_ml_probs)

            implied_spread_probs = [calculate_implied_probability(spread_odds[home]['price']),
                                   calculate_implied_probability(spread_odds[away]['price'])]
            vig_spread = calculate_vig(implied_spread_probs)

            implied_total_probs = [calculate_implied_probability(total_odds['Over']),
                                   calculate_implied_probability(total_odds['Under'])]
            vig_total = calculate_vig(implied_total_probs)

            # Calculate EV and edge for moneyline (pick team with positive EV)
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
                # no positive EV moneyline bet found, skip game
                continue

            # Choose best moneyline bet by EV
            best_ml = max(ml_bets, key=lambda b: b['ev'])

            # Spread bets
            spread_bets = []
            for team in [home, away]:
                odds = spread_odds[team]['price']
                point = spread_odds[team]['point']
                implied_prob = calculate_implied_probability(odds)
                # Assume model prob aligns with moneyline probabilities for spreads (simplification)
                prob = home_prob if team == home else away_prob
                ev = calculate_ev(prob, odds)
                edge = calculate_edge(prob, implied_prob)
                if ev > 0:
                    pick_str = f"{team} {point:+}"
                    spread_bets.append({
                        'pick': pick_str,
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

            # Total bets (Over/Under)
            total_bets = []
            for side in ['Over', 'Under']:
                odds = total_odds[side]
                implied_prob = calculate_implied_probability(odds)
                # For model probability: total line is often 50/50, but adjust slightly by comparing model probs
                # Simplified assumption: model total prob 55% for Over if home_prob + away_prob > 1.05 else 45%
                model_total_prob = 0.55 if (home_prob + away_prob) > 1.05 else 0.45
                if side == 'Under':
                    model_total_prob = 1 - model_total_prob
                ev = calculate_ev(model_total_prob, odds)
                edge = calculate_edge(model_total_prob, implied_prob)
                if ev > 0:
                    pick_str = f"{side} {total_point}"
                    total_bets.append({
                        'pick': pick_str,
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

            # Compose alert message
            header = f"⚾ *{away}* @ *{home}*\n🕒 {commence_str}\n\n"

            ml_section = format_bet_section('moneyline', best_ml['pick'], best_ml['odds'], best_ml['ev'], best_ml['implied_prob'], best_ml['model_prob'], best_ml['edge'], best_ml['vig'])
            spread_section = format_bet_section('spread', best_spread['pick'], best_spread['odds'], best_spread['ev'], best_spread['implied_prob'], best_spread['model_prob'], best_spread['edge'], best_spread['vig'])
            total_section = format_bet_section('total', best_total['pick'], best_total['odds'], best_total['ev'], best_total['implied_prob'], best_total['model_prob'], best_total['edge'], best_total['vig'])

            # Skip if any section is None (meaning no positive EV bet)
            if None in [ml_section, spread_section, total_section]:
                continue

            message = header + ml_section + "\n\n" + spread_section + "\n\n" + total_section

            send_alert(message)

        except Exception as e:
            print(f"Error processing game {game.get('away_team')} vs {game.get('home_team')}: {e}")

if __name__ == '__main__':
    process_games()
