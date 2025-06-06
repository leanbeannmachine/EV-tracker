import requests
import html
import os
import logging
import math

# ===== Logging Setup =====
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ===== Load Environment Variables =====
ODDS_API_KEY = os.getenv('ODDS_API_KEY')
SPORTMONKS_API_KEY = os.getenv('SPORTMONKS_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# ===== Check for Missing Keys =====
required_keys = [ODDS_API_KEY, SPORTMONKS_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]
if not all(required_keys):
    logging.error("❌ One or more API keys or Telegram credentials are missing.")
    exit(1)

# ===== API Endpoints =====
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/upcoming/odds"
SPORTMONKS_API_URL = "https://api.sportmonks.com/v3/football/fixtures"

# ===== Fetch Odds Data =====
def get_odds_data():
    try:
        logging.info("📡 Fetching Odds API data...")
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

# ===== Fetch Fixture Data =====
def get_fixture_data():
    try:
        logging.info("📡 Fetching SportMonks fixture data...")
        response = requests.get(
            SPORTMONKS_API_URL,
            params={
                "api_token": SPORTMONKS_API_KEY,
                "include": "participants",
                "per_page": 1
            },
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except Exception as e:
        logging.error(f"SportMonks API error: {str(e)}")
        return None

# ===== Betting Analysis Function (unchanged logic) =====
# [You can leave the analyze_betting_markets() function exactly as it is.]

# ===== Format Message for Telegram =====
def format_telegram_message(odds_data, fixture_data):
    if not fixture_data:
        return "⚠️ No upcoming fixtures found"

    try:
        fixture = fixture_data[0]
        participants = fixture.get('participants', [])
        if len(participants) < 2:
            raise ValueError("Fixture does not contain both teams")

        home = participants[0].get('name', 'Home')
        away = participants[1].get('name', 'Away')
        start_time = fixture.get('starting_at', 'N/A')

        # Format date/time
        date_str = start_time[:10] if len(start_time) >= 10 else "N/A"
        time_str = start_time[11:16] if len(start_time) >= 16 else "N/A"

        # Analyze odds
        analysis = analyze_betting_markets(odds_data, home, away) if odds_data else {}

        # Build message
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
        return "⚠️ Error formatting betting alert message"

# ===== Send Message to Telegram =====
def send_telegram_message(message):
    try:
        logging.info("📬 Sending message to Telegram...")
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code != 200:
            logging.error(f"Telegram API error: {response.status_code} - {response.text}")
            return None

        return response.json()
    except Exception as e:
        logging.error(f"Telegram send error: {str(e)}")
        return None

# ===== Main Script Runner =====
if __name__ == "__main__":
    logging.info("🚀 Starting bet alert script...")

    odds_data = get_odds_data()
    fixture_data = get_fixture_data()

    message = format_telegram_message(odds_data, fixture_data)
    logging.info(f"📨 Prepared message:\n{message}")

    result = send_telegram_message(message)

    if result and result.get('ok'):
        logging.info("✅ Message sent successfully!")
    else:
        logging.error("❌ Failed to send message")
        if result:
            logging.error(f"Telegram response: {result}")

    logging.info("✅ Script finished.")
