import requests
import html
import os
import logging
import math
from datetime import datetime, timedelta

# ===== SET UP LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# ===== CONFIGURATION =====
ODDS_API_KEY = "7b5d540e73c8790a95b84d3713e1a572"
SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# ===== API ENDPOINTS =====
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/upcoming/odds"
SPORTMONKS_API_URL = "https://api.sportmonks.com/v3/football/fixtures"

# ===== FETCH FIXTURE DATA =====
def get_fixture_data():
    try:
        logging.info("Fetching fixture data...")
        response = requests.get(
            SPORTMONKS_API_URL,
            params={
                "api_token": SPORTMONKS_API_KEY,
                "include": "participants",
                "per_page": 50
            },
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        fixtures = data.get('data', [])
        
        # Get UTC dates for filtering
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        filtered = []
        
        for fixture in fixtures:
            start_info = fixture.get('starting_at')
            if not start_info:
                continue
                
            try:
                # Handle both space and T separated formats
                if " " in start_info:  # Handle "YYYY-MM-DD HH:MM:SS"
                    date_str = start_info.split(" ")[0]
                else:  # Handle "YYYY-MM-DDTHH:MM:SS+00:00"
                    date_str = start_info.split("T")[0]
                
                fixture_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                # Check if fixture is today or tomorrow
                if fixture_date in (today, tomorrow):
                    filtered.append(fixture)
            except Exception as e:
                logging.error(f"Failed to parse fixture date: {start_info} → {str(e)}")
                continue
                
        logging.info(f"Found {len(filtered)} fixtures for today/tomorrow")
        return filtered

    except requests.RequestException as e:
        logging.error(f"Error fetching fixtures: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error in get_fixture_data: {str(e)}")
        return []

# ===== FETCH ODDS DATA =====
def get_odds_data():
    try:
        logging.info("Fetching odds data...")
        response = requests.get(
            ODDS_API_URL,
            params={
                "regions": "eu",
                "markets": "h2h,spreads,totals",
                "oddsFormat": "decimal",
                "apiKey": ODDS_API_KEY
            },
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Odds API error: {str(e)}")
        return None

# ===== ANALYZE BETTING MARKETS =====
def analyze_betting_markets(odds_data, home_team, away_team):
    money_line_winner = "⚠️ No data"
    spread_winner = "⚠️ No data"
    over_under_winner = "⚠️ No data"
    double_chance_winner = "⚠️ No data"
    
    if not odds_data:
        return {
            "money_line": money_line_winner,
            "spread": spread_winner,
            "over_under": over_under_winner,
            "double_chance": double_chance_winner
        }
    
    for match in odds_data:
        if match.get('home_team') == home_team and match.get('away_team') == away_team:
            # Money Line (H2H) Analysis
            home_odds = []
            away_odds = []
            draw_odds = []
            
            # Spread Analysis
            spread_home_odds = []
            spread_away_odds = []
            spread_points = None
            
            # Over/Under Analysis
            over_odds = []
            under_odds = []
            total_points = None
            
            # Double Chance Analysis
            home_draw_odds = []
            away_draw_odds = []
            home_away_odds = []
            
            for bookmaker in match.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    # Money Line (H2H)
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home_team:
                                home_odds.append(outcome['price'])
                            elif outcome['name'] == away_team:
                                away_odds.append(outcome['price'])
                            elif outcome['name'] == 'Draw':
                                draw_odds.append(outcome['price'])
                    
                    # Point Spread
                    elif market['key'] == 'spreads':
                        for outcome in market['outcomes']:
                            if outcome['name'] == home_team:
                                spread_home_odds.append(outcome['price'])
                                spread_points = outcome['point']
                            elif outcome['name'] == away_team:
                                spread_away_odds.append(outcome['price'])
                    
                    # Over/Under
                    elif market['key'] == 'totals':
                        for outcome in market['outcomes']:
                            if outcome['name'] == 'Over':
                                over_odds.append(outcome['price'])
                                total_points = outcome['point']
                            elif outcome['name'] == 'Under':
                                under_odds.append(outcome['price'])
            
            # Calculate Double Chance odds
            if home_odds and draw_odds:
                home_draw_odds = [1/(1/home_odd + 1/draw_odd) for home_odd, draw_odd in zip(home_odds, draw_odds)]
            if away_odds and draw_odds:
                away_draw_odds = [1/(1/away_odd + 1/draw_odd) for away_odd, draw_odd in zip(away_odds, draw_odds)]
            if home_odds and away_odds:
                home_away_odds = [1/(1/home_odd + 1/away_odd) for home_odd, away_odd in zip(home_odds, away_odds)]
            
            # Determine Money Line Winner
            if home_odds and away_odds and draw_odds:
                avg_home = sum(home_odds)/len(home_odds)
                avg_away = sum(away_odds)/len(away_odds)
                avg_draw = sum(draw_odds)/len(draw_odds)
                
                if avg_home < avg_away and avg_home < avg_draw:
                    money_line_winner = f"🏠 {home_team} WIN (Best: {max(home_odds):.2f})"
                elif avg_away < avg_home and avg_away < avg_draw:
                    money_line_winner = f"✈️ {away_team} WIN (Best: {max(away_odds):.2f})"
                else:
                    money_line_winner = f"🟰 DRAW (Best: {max(draw_odds):.2f})"
            
            # Determine Spread Winner
            if spread_home_odds and spread_away_odds and spread_points:
                home_edge = max(spread_home_odds) - min(spread_home_odds)
                away_edge = max(spread_away_odds) - min(spread_away_odds)
                
                if home_edge > away_edge:
                    spread_winner = f"🏠 {home_team} +{spread_points} (Best: {max(spread_home_odds):.2f})"
                else:
                    spread_winner = f"✈️ {away_team} -{spread_points} (Best: {max(spread_away_odds):.2f})"
            
            # Determine Over/Under Winner
            if over_odds and under_odds and total_points:
                over_edge = max(over_odds) - min(over_odds)
                under_edge = max(under_odds) - min(under_odds)
                
                if over_edge > under_edge:
                    over_under_winner = f"⬆️ OVER {total_points} (Best: {max(over_odds):.2f})"
                else:
                    over_under_winner = f"⬇️ UNDER {total_points} (Best: {max(under_odds):.2f})"
            
            # Determine Double Chance Winner
            dc_options = []
            if home_draw_odds:
                dc_options.append(("🏠/🟰 Home/Draw", max(home_draw_odds)))
            if away_draw_odds:
                dc_options.append(("✈️/🟰 Away/Draw", max(away_draw_odds)))
            if home_away_odds:
                dc_options.append(("🏠/✈️ Home/Away", max(home_away_odds)))
            
            if dc_options:
                dc_options.sort(key=lambda x: x[1], reverse=True)
                double_chance_winner = f"{dc_options[0][0]} (Best: {dc_options[0][1]:.2f})"
            
            break  # Found our match, exit loop
    
    return {
        "money_line": money_line_winner,
        "spread": spread_winner,
        "over_under": over_under_winner,
        "double_chance": double_chance_winner
    }

# ===== FORMAT TELEGRAM MESSAGE =====
def format_telegram_message(odds_data, fixture_data):
    if not fixture_data:
        return "⚠️ No upcoming fixtures found"
    
    try:
        fixture = fixture_data[0]
        participants = fixture.get('participants', [])
        
        if len(participants) < 2:
            return "⚠️ Fixture data incomplete"
        
        home = participants[0].get('name', 'Home Team')
        away = participants[1].get('name', 'Away Team')
        start_time = fixture.get('starting_at', '')
        
        # Format date and time
        if "T" in start_time:
            date_str = start_time.split("T")[0]
            time_part = start_time.split("T")[1]
            time_str = time_part[:5] if len(time_part) >= 5 else "N/A"
        else:
            parts = start_time.split(" ")
            date_str = parts[0] if len(parts) > 0 else "N/A"
            time_str = parts[1][:5] if len(parts) > 1 and len(parts[1]) >= 5 else "N/A"
        
        # Analyze all betting markets
        analysis = analyze_betting_markets(odds_data, home, away)
        
        # Build clear winning recommendations
        message = f"""
🎯 *BETTING WINNERS FOR TODAY* 🎯
⚽️ *{html.escape(home)} vs {html.escape(away)}*
📅 *Date:* {date_str} | ⏰ *Time:* {time_str} UTC
─────────────────
        
🟩 *MONEY LINE WINNER:*
   {analysis.get('money_line', '⚠️ No data')}
        
📊 *SPREAD WINNER:*
   {analysis.get('spread', '⚠️ No data')}
        
📈 *OVER/UNDER WINNER:*
   {analysis.get('over_under', '⚠️ No data')}
        
✌️ *DOUBLE CHANCE WINNER:*
   {analysis.get('double_chance', '⚠️ No data')}
─────────────────
💡 *TIP:* These are calculated based on best value across bookmakers
"""

        return message
        
    except Exception as e:
        logging.error(f"Formatting error: {str(e)}")
        return "⚠️ Error formatting message"

# ===== SEND TO TELEGRAM =====
def send_telegram_message(message):
    try:
        logging.info("Sending Telegram message...")
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logging.error(f"Telegram send error: {str(e)}")
        return None

# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    logging.info("🚀 Running Betting Alert Script...")
    
    # Get data from APIs
    odds_data = get_odds_data()
    fixture_data = get_fixture_data()  # This already returns filtered fixtures
    
    # Format message
    message = format_telegram_message(odds_data, fixture_data)
    logging.info(f"Formatted message:\n{message}")
    
    # Send to Telegram
    result = send_telegram_message(message)
    
    if result and result.get('ok'):
        logging.info("✅ Message sent successfully!")
    else:
        logging.error("❌ Failed to send message")
        if result:
            logging.error(f"Telegram response: {result}")
    
    logging.info("🏁 Script completed")
