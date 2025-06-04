from datetime import datetime, timezone, timedelta
import requests
import telegram
import time

# CONFIG
API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"
BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"

LEAGUES = [
    "soccer_usa_mls",
    "soccer_argentina_primera_division",
    "basketball_wnba"
]

BOOKMAKER = "bovada"
REGION = "us"
MARKETS = ["h2h", "spreads", "totals", "double_chance"]  # Added multiple markets
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
    odds = int(odds)
    return f"+{odds}" if odds > 0 else str(odds)

def implied_prob(odds):
    odds = int(odds)
    return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)

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
    for league in LEAGUES:
        url = (
            f"https://api.the-odds-api.com/v4/sports/{league}/odds/"
            f"?apiKey={API_KEY}&regions={REGION}&markets={','.join(MARKETS)}"
            f"&bookmakers={BOOKMAKER}&oddsFormat={ODDS_FORMAT}"
        )

        try:
            response = requests.get(url)
            if response.status_code != 200:
                print(f"Error fetching odds for {league}: {response.status_code}")
                continue

            data = response.json()
            for match in data:
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
                        
                    for market in bookmaker.get("markets", []):
                        market_key = market['key']
                        if market_key not in MARKETS:
                            continue

                        for outcome in market.get("outcomes", []):
                            odds = outcome.get("price")
                            if odds is None:
                                continue

                            prob = implied_prob(odds)
                            edge = (1 - prob) * 100

                            if edge >= THRESHOLD:
                                # Determine reason based on edge and market
                                if edge >= 5:
                                    quality = "🟢 GOOD BET"
                                    reason = (
                                        "Strong value: Recent performance and odds analysis show significant undervaluation"
                                    )
                                else:
                                    quality = "🟡 SOLID BET"
                                    reason = (
                                        "Positive expected value: Statistical edge against the market odds"
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
                                
                                matches[match_id]['bets'].append({
                                    'market': market_name,
                                    'bet': bet_desc,
                                    'odds': format_american_odds(odds),
                                    'edge': edge,
                                    'quality': quality,
                                    'reason': reason
                                })
                time.sleep(0.5)  # Reduce rate between matches

        except Exception as e:
            print(f"Error in league {league}: {str(e)}")
        time.sleep(1)  # Pause between leagues

    return matches

def format_match_message(match_data):
    """Create formatted Telegram message for a match"""
    home = match_data['home']
    away = match_data['away']
    start_time = match_data['start_time'].strftime("%a, %b %d @ %H:%M UTC")
    
    # Header with teams and time
    message = [
        f"⚽ *{home} vs {away}*",
        f"⏰ {start_time}",
        "--------------------------------"
    ]
    
    # Add all bets for this match
    for idx, bet in enumerate(match_data['bets'], 1):
        message.append(
            f"🔹 *{bet['market']}*\n"
            f"• Bet: {bet['bet']}\n"
            f"• Odds: `{bet['odds']}`\n"
            f"• Edge: {bet['edge']:.1f}% {bet['quality']}\n"
            f"• Reason: {bet['reason']}\n"
        )
    
    # Add match separator
    message.append("📊 *Value Match Analysis*")
    return "\n".join(message)

def send_to_telegram(matches):
    if not matches:
        print("No value bets found.")
        return

    bot = telegram.Bot(token=BOT_TOKEN)
    for match_id, match_data in matches.items():
        if match_data['bets']:
            message = format_match_message(match_data)
            try:
                bot.send_message(
                    chat_id=CHAT_ID,
                    text=message,
                    parse_mode=telegram.ParseMode.MARKDOWN
                )
                time.sleep(1)  # Avoid rate limits
            except Exception as e:
                print(f"Error sending message: {str(e)}")

if __name__ == "__main__":
    matches = get_value_bets()
    send_to_telegram(matches)
