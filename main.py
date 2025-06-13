import os
import re
import requests
from datetime import datetime
from pytz import timezone

# === ENVIRONMENT VARIABLES ===
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
API_KEY = "25af17e62a8d221b05b9b5c5a4911cdb"

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
def process_games(games, telegram_token, telegram_chat_id):
    for game in games:
        try:
            teams = f"{game['home_team']} @ {game['away_team']}"
            game_time_cdt = datetime.fromtimestamp(game['commence_time'], tz=timezone.utc).astimezone(CENTRAL_TIMEZONE)
            game_time_str = game_time_cdt.strftime("%m/%d %I:%M %p CDT")

            header = f"⚾ {teams}\n🕒 {game_time_str}\n"

            best_ml = get_best_bet(game['moneyline'])
            best_spread = get_best_bet(game['spreads'])
            best_total = get_best_bet(game['totals'])

            sections = []

            if best_ml:
                ml_section = format_bet_section(
                    bet_type='moneyline',
                    pick=best_ml['pick'],
                    odds=best_ml['odds'],
                    ev=best_ml['ev'],
                    implied_prob=best_ml['implied_prob'],
                    model_prob=best_ml['model_prob'],
                    edge=best_ml['edge'],
                    vig=best_ml['vig']
                )
                if ml_section:
                    sections.append(ml_section)

            if best_spread:
                spread_section = format_bet_section(
                    bet_type='spread',
                    pick=best_spread['pick'],
                    odds=best_spread['odds'],
                    ev=best_spread['ev'],
                    implied_prob=best_spread['implied_prob'],
                    model_prob=best_spread['model_prob'],
                    edge=best_spread['edge'],
                    vig=best_spread['vig']
                )
                if spread_section:
                    sections.append(spread_section)

            if best_total:
                total_section = format_bet_section(
                    bet_type='total',
                    pick=best_total['pick'],
                    odds=best_total['odds'],
                    ev=best_total['ev'],
                    implied_prob=best_total['implied_prob'],
                    model_prob=best_total['model_prob'],
                    edge=best_total['edge'],
                    vig=best_total['vig']
                )
                if total_section:
                    sections.append(total_section)

            # Only send alert if at least one bet is worth showing
            if sections:
                message = header + "\n\n" + "\n\n".join(sections)
                send_alert(message, telegram_token, telegram_chat_id)

        except Exception as e:
            print(f"Error processing game {game['home_team']} vs {game['away_team']}: {e}")
            
if __name__ == '__main__':
    process_games()
