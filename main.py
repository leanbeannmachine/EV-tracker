from datetime import datetime, timezone, timedelta
import requests
import telegram
import time
import random

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

def generate_reason(market, outcome, edge, is_home, is_away):
    """Generate specific, analytical reasoning for each bet type"""
    team_name = outcome['name']
    base_reason = ""
    
    # Market-specific reasoning
    if market == "h2h":
        if edge >= 5:
            base_reason = f"Strong value: {team_name} are significantly undervalued based on recent performance metrics"
        else:
            base_reason = f"Positive expected value: {team_name} show a statistical edge against current odds"
            
        if is_home:
            base_reason += ", with strong home form influencing the valuation"
        elif is_away:
            base_reason += ", with recent away performances suggesting underestimated potential"
            
    elif market == "spreads":
        point = outcome.get('point', '')
        if edge >= 5:
            base_reason = f"Strong spread value: {team_name} covering {point} shows significant statistical edge"
        else:
            base_reason = f"Spread opportunity: {team_name} covering {point} presents positive expected value"
            
        if float(point or 0) > 0:
            base_reason += ", with underdog performance metrics exceeding expectations"
        else:
            base_reason += ", with favorite consistency creating value against the spread"
            
    elif market == "totals":
        point = outcome.get('point', '')
        over_under = "Over" if "Over" in team_name else "Under"
        if edge >= 5:
            base_reason = f"Strong total value: {over_under} {point} shows significant mispricing"
        else:
            base_reason = f"Total opportunity: {over_under} {point} presents statistical value"
            
        if over_under == "Over":
            base_reason += ", with offensive efficiency trends supporting higher scoring"
        else:
            base_reason += ", with defensive solidity patterns suggesting lower scoring"
            
    elif market == "double_chance":
        options = {
            "Home or Draw": f"{outcome['home_team']} not to lose",
            "Away or Draw": f"{outcome['away_team']} not to lose",
            "Home or Away": "No draw in this matchup"
        }
        desc = options.get(team_name, team_name)
        
        if edge >= 5:
            base_reason = f"Strong double chance value: {desc} shows significant safety margin"
        else:
            base_reason = f"Double chance opportunity: {desc} presents positive expected value"
            
        if "Draw" in team_name:
            base_reason += ", with draw probability underestimated by the market"
        else:
            base_reason += ", with team quality differential creating value"
    
    # Add edge-specific quantification
    if edge >= 8:
        base_reason += f" (high confidence - {edge:.1f}% edge)"
    elif edge >= 5:
        base_reason += f" (moderate confidence - {edge:.1f}% edge)"
    else:
        base_reason += f" ({edge:.1f}% statistical edge)"
        
    return base_reason

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

                                    prob
