import requests
import datetime
import time
from telegram import Bot
from telegram.error import TelegramError

# Your keys and chat ID here
SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Helper function to fetch fixtures with odds and markets
def fetch_fixtures():
    # Fetching fixtures for the next 3 days
    now = datetime.datetime.utcnow()
    three_days_later = now + datetime.timedelta(days=3)
    url = (
        f"https://api.sportmonks.com/v3/football/fixtures"
        f"?api_token={SPORTMONKS_API_KEY}"
        f"&include=odds.bookmakers.markets,localteam,visitorteam"
        f"&filter[starts_between]={now.isoformat()},{three_days_later.isoformat()}"
        f"&sort=starting_at"
        f"&per_page=50"
    )
    try:
        resp = requests.get(url)
        resp.raise_for_status()
        data = resp.json()
        return data.get('data', [])
    except Exception as e:
        print(f"Error fetching fixtures: {e}")
        return []

# Function to fetch recent player stats for props (simplified placeholder)
def fetch_player_props(team_id):
    # In real implementation, you'd pull player stats and analyze last 5-10 games
    # Here, we simulate standout players randomly or based on some criteria
    # Returning a dummy list for example
    standout_players = [
        {"name": "John Doe", "stat": "2 goals in last 5 games"},
        {"name": "Jane Smith", "stat": "3 assists in last 7 games"},
    ]
    return standout_players

# Analyze odds and assign confidence levels
def evaluate_bet(odds):
    american_odds = odds
    # Simple heuristic: odds between -150 and +150 considered good
    if -150 <= american_odds <= 150:
        confidence = "✅ Good bet"
    elif -200 <= american_odds < -150 or 150 < american_odds <= 200:
        confidence = "⚠️ Medium risk"
    else:
        confidence = "❌ Risky bet"
    return confidence

# Convert decimal to American odds (if needed)
def decimal_to_american(decimal_odds):
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))

def format_match_message(fixture):
    local_team = fixture['localteam']['data']['name']
    visitor_team = fixture['visitorteam']['data']['name']
    start_time = fixture['starting_at']
    start_time_fmt = datetime.datetime.fromisoformat(start_time[:-1]).strftime('%Y-%m-%d %H:%M UTC')
    
    message = f"⚽ *{local_team}* vs *{visitor_team}*\n"
    message += f"🕒 Starts at: {start_time_fmt}\n\n"
    
    # Odds & markets
    odds_info = []
    try:
        odds_data = fixture['odds']['data']
        for bookmaker in odds_data:
            name = bookmaker['bookmaker']['data']['name']
            for market in bookmaker['markets']['data']:
                # Only process common markets: spreads, totals, moneyline
                if market['key'] in ['spreads', 'totals', 'h2h']:
                    for outcome in market['outcomes']:
                        label = outcome['label']
                        odds = outcome['price']
                        american_odds = decimal_to_american(odds)
                        confidence = evaluate_bet(american_odds)
                        
                        # Build detailed reasoning
                        reasoning = (
                            f"{confidence} | "
                            f"Market: {market['key'].capitalize()} | "
                            f"Pick: {label} | "
                            f"Odds: {american_odds} | "
                            f"Bookmaker: {name}"
                        )
                        odds_info.append(reasoning)
    except Exception as e:
        print(f"Error processing odds: {e}")
    
    if not odds_info:
        message += "⚠️ No odds available at the moment.\n"
    else:
        for line in odds_info:
            # Add emoji based on confidence for better visual cue
            if "✅" in line:
                message += f"✅ {line}\n"
            elif "⚠️" in line:
                message += f"⚠️ {line}\n"
            else:
                message += f"❌ {line}\n"
    
    # Player props (simplified)
    player_props = fetch_player_props(fixture['localteam']['data']['id']) + fetch_player_props(fixture['visitorteam']['data']['id'])
    if player_props:
        message += "\n🧍‍♂️ *Player Props Highlights:*\n"
        for player in player_props:
            message += f"- {player['name']}: {player['stat']}\n"
    
    return message

def send_telegram_message(text):
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="Markdown")
    except TelegramError as e:
        print(f"Telegram error: {e}")

def main():
    print("Fetching fixtures and sending bets...")
    fixtures = fetch_fixtures()
    if not fixtures:
        send_telegram_message("🚨 No good value bets available for the next 3 days. Stay tuned!")
        return
    
    for fixture in fixtures:
        msg = format_match_message(fixture)
        send_telegram_message(msg)
        time.sleep(1)  # To avoid hitting Telegram rate limits

if __name__ == "__main__":
    main()
