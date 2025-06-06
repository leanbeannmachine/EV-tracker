import requests
from datetime import datetime, timedelta

# ===== 🔐 API Keys & Tokens =====
ODDS_API_KEY = "7b5d540e73c8790a95b84d3713e1a572"
SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# ===== API Endpoints =====
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/upcoming/odds"
SPORTMONKS_API_URL = "https://api.sportmonks.com/v3/football/fixtures"

# ===== Analyze Betting Markets =====
def analyze_betting_markets(odds_data, home, away):
    result = {}
    try:
        for event in odds_data:
            if home.lower() in event['home_team'].lower() or away.lower() in event['away_team'].lower():
                for book in event.get('bookmakers', []):
                    for market in book.get('markets', []):
                        key = market.get('key')
                        outcomes = market.get('outcomes', [])
                        if not outcomes:
                            continue
                        if key == "h2h":
                            best = max(outcomes, key=lambda x: x['price'])
                            result['money_line'] = f"{best['name']} @ {best['price']}"
                        elif key == "spreads":
                            best = max(outcomes, key=lambda x: x['price'])
                            result['spread'] = f"{best['name']} {best['point']} @ {best['price']}"
                        elif key == "totals":
                            over = next((o for o in outcomes if "Over" in o['name']), None)
                            under = next((o for o in outcomes if "Under" in o['name']), None)
                            if over and under:
                                result['over_under'] = f"Over {over['point']} @ {over['price']} or Under @ {under['price']}"
        result.setdefault('money_line', '⚠️ No data')
        result.setdefault('spread', '⚠️ No data')
        result.setdefault('over_under', '⚠️ No data')
        result['double_chance'] = "✔️ Safer pick (win or draw)"
        return result
    except Exception as e:
        print(f"⚠️ Error analyzing betting data: {e}")
        return result

# ===== Fetch Odds Data =====
def get_odds_data():
    try:
        response = requests.get(ODDS_API_URL, params={
            "regions": "eu",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "decimal",
            "apiKey": ODDS_API_KEY
        }, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Odds API error: {e}")
        return None

# ===== Fetch Fixture Data =====
import requests
from datetime import datetime, timedelta

def get_fixture_data():
    try:
        response = requests.get(SPORTMONKS_API_URL, params={
            "api_token": SPORTMONKS_API_KEY,
            "include": "participants",
            "per_page": 50
        }, timeout=15)

        response.raise_for_status()
        data = response.json()
        fixtures = data.get('data', [])

        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)

        filtered = []

        for f in fixtures:
            start_info = f.get('starting_at')

            if not start_info:
                continue

            try:
                # Handles full ISO format: e.g. "2025-06-06T20:30:00+00:00"
                start_date = datetime.fromisoformat(start_info[:10]).date()
                if start_date in [today, tomorrow]:
                    filtered.append(f)
            except Exception as e:
                print(f"⚠️ Failed to parse fixture date: {start_info} → {e}")
                continue

        return filtered

    except requests.RequestException as e:
        print(f"❌ Error fetching fixtures: {e}")
        return []
        
# ===== Format Telegram Message =====
def format_telegram_message(odds_data, fixture):
    try:
        participants = fixture.get('participants', [])
        if len(participants) < 2:
            return "⚠️ Not enough teams"

        home = participants[0].get('name', 'Home')
        away = participants[1].get('name', 'Away')
        start_time = fixture.get('starting_at', 'N/A')
        date_str = start_time[:10] if len(start_time) >= 10 else "N/A"
        time_str = start_time[11:16] if len(start_time) >= 16 else "N/A"

        analysis = analyze_betting_markets(odds_data, home, away) if odds_data else {}

        message = f"""🔥 *Today's Top Bet Preview:*
📅 {date_str} at {time_str}
🏆 {home} vs {away}

✌️ *DOUBLE CHANCE WINNER:*
{analysis.get('double_chance', '⚠️ No data')}

📈 *OVER/UNDER WINNER:*
{analysis.get('over_under', '⚠️ No data')}

🟩 *MONEY LINE WINNER:*
{analysis.get('money_line', '⚠️ No data')}

📊 *SPREAD WINNER:*
{analysis.get('spread', '⚠️ No data')}

💡 *TIP:* Picks are based on best bookmaker odds & probabilities"""
        return message

    except Exception as e:
        print(f"⚠️ Message formatting error: {e}")
        return "⚠️ Error formatting message"

# ===== Send Telegram Message =====
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Sent to Telegram!")
        else:
            print(f"❌ Telegram error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Telegram send error: {e}")

# ===== Main Run Block =====
if __name__ == "__main__":
    print("🚀 Running Betting Alert Script...")

    odds_data = get_odds_data()
    fixture_data = get_fixture_data()

    filtered_fixtures = filter_fixtures(fixture_data)

    if not filtered_fixtures:
        print("⚠️ No valid fixtures for today or tomorrow.")
    else:
        for fixture in filtered_fixtures:
            message = format_telegram_message(odds_data, fixture)
            print("📨 Message:\n", message)
            send_telegram_message(message)

    print("✅ Script complete.")
