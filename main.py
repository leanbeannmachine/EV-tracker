import requests

# === CONFIGURATION ===
API_KEY = "183b79e95844e2300faa30f9383890b5"  # Your OddsAPI key here
TELEGRAM_BOT_TOKEN ="7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"  # Replace with your Telegram bot token
TELEGRAM_CHAT_ID = "964091254"      # Replace with your Telegram chat ID

# Define leagues you want to track (only leagues known to OddsAPI, avoid deprecated ones)
LEAGUES = [
    "soccer_australia_aleague",
    "soccer_belgium_jupiler_pro_league",
    "soccer_england_premier_league",
    "soccer_usa_mls",
    # Add or remove leagues as you like
]

# OddsAPI endpoint template
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/{league}/odds?apiKey={key}&regions=us&markets=h2h&oddsFormat=american"

# Minimum value edge threshold for bet quality classification
MIN_EDGE_GREEN = 5  # % edge for green (good)
MIN_EDGE_YELLOW = 2 # % edge for yellow (okay)

def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(url, data=data)
        r.raise_for_status()
    except Exception as e:
        print(f"Error sending telegram message: {e}")

# === FORMAT AMERICAN ODDS ===
def format_american_odds(odds):
    odds = int(odds)
    return f"+{odds}" if odds > 0 else str(odds)

def calculate_edge(odds: int, implied_prob: float) -> float:
    # edge = (implied probability from odds) - (estimated winning probability)
    dec = american_to_decimal(odds)
    odds_prob = 1 / dec
    return (implied_prob - odds_prob) * 100  # in percent

def classify_bet(edge: float):
    if edge >= MIN_EDGE_GREEN:
        return ("🟢 Good Bet", "This bet has a positive expected value and is a strong value play.")
    elif edge >= MIN_EDGE_YELLOW:
        return ("🟡 Okay Bet", "This bet has a small edge but still might be profitable with proper bankroll management.")
    else:
        return ("🔴 Bad Bet", "This bet is too risky or has negative expected value; avoid for bankroll protection.")

def fetch_and_send_bets():
    for league in LEAGUES:
        url = ODDS_API_URL.format(league=league, key=API_KEY)
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 404:
                print(f"League not found or no odds: {league}")
                continue
            resp.raise_for_status()
            matches = resp.json()
        except Exception as e:
            print(f"Error fetching odds for league {league}: {e}")
            continue

        for match in matches:
            try:
                home_team = match['home_team']
                away_team = match['away_team']
                bookmakers = match['bookmakers']
                if not bookmakers:
                    continue
                # Use first bookmaker for simplicity
                markets = bookmakers[0]['markets']
                if not markets:
                    continue
                h2h = next((m for m in markets if m['key'] == 'h2h'), None)
                if not h2h:
                    continue
                outcomes = h2h['outcomes']

                # Find home, away, and draw odds in American odds format
                home_odds = next((o for o in outcomes if o['name'] == home_team), None)
                away_odds = next((o for o in outcomes if o['name'] == away_team), None)
                draw_odds = next((o for o in outcomes if o['name'].lower() == "draw"), None)

                # Simple example model: Use implied probability from odds (this is raw)
                # For demonstration, let's say we have a winning probability estimate (dummy example)
                # In a real model, replace these with your actual win probability estimates per team.
                # Here, as a placeholder, estimate equal probability for all teams.
                estimated_prob_home = 0.35
                estimated_prob_away = 0.35
                estimated_prob_draw = 0.3

                messages = []

                # Evaluate Home Bet
                if home_odds:
                    edge = calculate_edge(home_odds['price'], estimated_prob_home)
                    label, reason = classify_bet(edge)
                    msg = f"<b>{home_team} vs {away_team}</b>\nBet: {home_team}\nOdds: {home_odds['price']} (American)\nEdge: {edge:.2f}% {label}\nReason: {reason}\n"
                    messages.append(msg)

                # Evaluate Away Bet
                if away_odds:
                    edge = calculate_edge(away_odds['price'], estimated_prob_away)
                    label, reason = classify_bet(edge)
                    msg = f"<b>{home_team} vs {away_team}</b>\nBet: {away_team}\nOdds: {away_odds['price']} (American)\nEdge: {edge:.2f}% {label}\nReason: {reason}\n"
                    messages.append(msg)

                # Evaluate Draw Bet
                if draw_odds:
                    edge = calculate_edge(draw_odds['price'], estimated_prob_draw)
                    label, reason = classify_bet(edge)
                    msg = f"<b>{home_team} vs {away_team}</b>\nBet: Draw\nOdds: {draw_odds['price']} (American)\nEdge: {edge:.2f}% {label}\nReason: {reason}\n"
                    messages.append(msg)

                # Send only green and yellow bets to Telegram to limit noise
                for message in messages:
                    if "🔴" not in message:
                        send_telegram_message(message)

            except Exception as e:
                print(f"Error parsing match in league {league}: {e}")

if __name__ == "__main__":
    fetch_and_send_bets()
