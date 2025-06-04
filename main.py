from datetime import datetime, timezone, timedelta
import requests
import telegram
import time

# CONFIG
API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"
BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"

LEAGUE_MARKETS = {
    "soccer_usa_mls": ["h2h", "spreads", "totals", "double_chance"],
    "soccer_argentina_primera_division": ["h2h", "spreads", "totals", "double_chance"],
    "basketball_wnba": ["h2h", "spreads", "totals"]
}

BOOKMAKER = "bovada"
REGION = "us"
THRESHOLD = 3.5
ODDS_FORMAT = "american"

# Market display names
MARKET_NAMES = {
    "h2h": "Moneyline",
    "spreads": "Spread",
    "totals": "Total Points",
    "double_chance": "Double Chance"
}

def format_american_odds(odds):
    try:
        odds = int(odds)
        return f"+{odds}" if odds > 0 else str(odds)
    except (TypeError, ValueError):
        return str(odds)

def implied_prob(odds):
    try:
        odds = int(odds)
        return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)
    except (TypeError, ValueError, ZeroDivisionError):
        return 0

def is_this_week(game_time):
    today = datetime.now(timezone.utc)
    start_week = today - timedelta(days=today.weekday())  # Monday
    end_week = start_week + timedelta(days=6)  # Sunday
    return start_week <= game_time <= end_week

def format_bet_description(market, outcome):
    """Create human-readable bet description based on market type"""
    if market == "spreads":
        point = outcome.get('point', '')
        return f"{outcome['name']} ({point})"
    elif market == "totals":
        point = outcome.get('point', '')
        return f"{outcome['name']} {point}"
    return outcome['name']

def get_value_bets():
    matches = {}
    
    for league, markets in LEAGUE_MARKETS.items():
        for market in markets:
            url = (
                f"https://api.the-odds-api.com/v4/sports/{league}/odds/"
                f"?apiKey={API_KEY}&regions={REGION}&markets={market}"
                f"&bookmakers={BOOKMAKER}&oddsFormat={ODDS_FORMAT}"
            )

            try:
                response = requests.get(url)
                if response.status_code != 200:
                    print(f"Error fetching {market} for {league}: {response.status_code} - {response.text[:100]}")
                    time.sleep(2)
                    continue

                data = response.json()
                print(f"Successfully fetched {market} for {league} ({len(data)} matches)")
                
                for match in data:
                    try:
                        match_id = match['id']
                        home = match.get("home_team", "Home")
                        away = match.get("away_team", "Away")
                        start_time = datetime.fromisoformat(match["commence_time"].replace("Z", "+00:00"))

                        if not is_this_week(start_time):
                            continue

                        # Initialize match entry
                        if match_id not in matches:
                            matches[match_id] = {
                                'home': home,
                                'away': away,
                                'start_time': start_time,
                                'bets': []
                            }

                        for bookmaker in match.get("bookmakers", []):
                            if bookmaker['key'] != BOOKMAKER:
                                continue
                                
                            for market_data in bookmaker.get("markets", []):
                                market_key = market_data['key']
                                if market_key != market:
                                    continue

                                for outcome in market_data.get("outcomes", []):
                                    odds = outcome.get("price")
                                    if odds is None:
                                        continue

                                    prob = implied_prob(odds)
                                    if prob == 0:  # Skip invalid probabilities
                                        continue
                                        
                                    edge = (1 - prob) * 100

                                    if edge >= THRESHOLD:
                                        # Determine reason based on edge and market
                                        if edge >= 5:
                                            quality = "🟢 GOOD BET"
                                            reason = (
                                                "Strong value: Significant undervaluation detected"
                                            )
                                        else:
                                            quality = "🟡 SOLID BET"
                                            reason = (
                                                "Positive expected value: Statistical edge against market"
                                            )
                                        
                                        # Market-specific context
                                        if market_key == "spreads":
                                            reason += " based on point differential trends"
                                        elif market_key == "totals":
                                            reason += " based on scoring patterns"
                                        elif market_key == "double_chance":
                                            reason += " considering team consistency"

                                        # Format bet details
                                        bet_desc = format_bet_description(market_key, outcome)
                                        market_name = MARKET_NAMES.get(market_key, market_key)
                                        
                                        matches[match_id]['bets'].
