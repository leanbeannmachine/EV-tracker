import requests
import html
import json

# ===== CONFIGURATION =====
ODDS_API_KEY = "7b5d540e73c8790a95b84d3713e1a572"
SPORTMONKS_API_KEY = "YOUR_SPORTMONKS_API_KEY"
TELEGRAM_BOT_TOKEN = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
TELEGRAM_CHAT_ID = "964091254"

# ===== API ENDPOINTS =====
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/upcoming/odds"
SPORTMONKS_API_URL = "https://api.sportmonks.com/v3/football/fixtures"

# ===== API PARAMETERS =====
ODDS_API_PARAMS = {
    "regions": "eu",
    "markets": "h2h",
    "oddsFormat": "decimal",
    "apiKey": ODDS_API_KEY
}

SPORTMONKS_PARAMS = {
    "api_token": SPORTMONKS_API_KEY,
    "include": "participants"
}

# ===== FETCH DATA FROM APIs =====
def get_odds_data():
    try:
        response = requests.get(ODDS_API_URL, params=ODDS_API_PARAMS)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Odds API error: {e}")
        return None

def get_fixture_data():
    try:
        response = requests.get(SPORTMONKS_API_URL, params=SPORTMONKS_PARAMS)
        response.raise_for_status()
        return response.json()['data']
    except requests.exceptions.RequestException as e:
        print(f"SportMonks API error: {e}")
        return None

# ===== FORMAT MESSAGE WITH PROPER ESCAPING =====
def format_telegram_message(odds_data, fixture_data):
    if not odds_data or not fixture_data:
        return "⚠️ Failed to fetch data from one or more APIs"
    
    try:
        # Process first fixture for example
        fixture = fixture_data[0]
        home = fixture['participants'][0]['name']
        away = fixture['participants'][1]['name']
        
        # Find matching odds
        match_odds = next((item for item in odds_data 
                          if item['home_team'] == home and item['away_team'] == away), None)
        
        if not match_odds:
            return f"🔍 No odds found for {home} vs {away}"
        
        # Extract best odds
        best_home = max(market['outcomes'][0]['price'] for market in match_odds['bookmakers'] 
                       if market['markets'][0]['key'] == 'h2h' and len(market['markets'][0]['outcomes']) >= 2)
        
        best_away = max(market['outcomes'][2]['price'] for market in match_odds['bookmakers'] 
                       if market['markets'][0]['key'] == 'h2h' and len(market['markets'][0]['outcomes']) >= 3)
        
        # Format message with HTML tags and proper escaping
        message = f"""
⚽️ <b>{html.escape(home)} vs {html.escape(away)}</b>
─────────────────
🏠 <i>Home Win Best Odds:</i> <b>{best_home:.2f}</b>
✈️ <i>Away Win Best Odds:</i> <b>{best_away:.2f}</b>
─────────────────
📅 <code>{fixture['starting_at'][:10]}</code> | ⏰ <code>{fixture['starting_at'][11:16]} UTC</code>
🔗 <a href="https://example.com/details/{fixture['id']}">View Details</a>
        """
        return message
        
    except (KeyError, IndexError, StopIteration) as e:
        print(f"Data processing error: {e}")
        return "⚠️ Error processing match data"

# ===== SEND TO TELEGRAM =====
def send_
