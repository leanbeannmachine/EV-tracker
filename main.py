import requests
import html

# ===== 🔐 API Keys & Tokens (Hardcoded for simplicity) =====
ODDS_API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"
SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# ===== API Endpoints =====
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/upcoming/odds"
SPORTMONKS_API_URL = "https://api.sportmonks.com/v3/football/fixtures"

# ===== Analyze Betting Data =====
def analyze_betting_markets(odds_data, home, away):
    result = {}
    try:
        for event in odds_data:
            if home.lower() in event['home_team'].lower() or away.lower() in event['away_team'].lower():
                bookmakers = event.get('bookmakers', [])
                for book in bookmakers:
                    markets = book.get('markets', [])
                    for market in markets:
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
def get_fixture_data():
    try:
        response = requests.get(SPORTMONKS_API_URL, params={
            "api_token": SPORTMONKS_API_KEY,
            "include": "participants",
            "per_page": 1
        }, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get('data', [])
    except Exception as e:
        print(f"❌ SportMonks API error: {e}")
        return None

# ===== Format Telegram Message =====
def escape_markdown_v2(text):
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

def format_telegram_message(odds_data, fixture_data):
    if not fixture_data:
        return "⚠️ No upcoming fixtures found"

    try:
        fixture = fixture_data[0]
        participants = fixture.get('participants', [])
        if len(participants) < 2:
            return "⚠️ Not enough teams"

        home = participants[0].get('name', 'Home')
        away = participants[1].get('name', 'Away')
        start_time = fixture.get('starting_at', 'N/A')
        date_str = start_time[:10] if len(start_time) >= 10 else "N/A"
        time_str = start_time[11:16] if len(start_time) >= 16 else "N/A"

        home_escaped = escape_markdown_v2(home)
        away_escaped = escape_markdown_v2(away)

        analysis = analyze_betting_markets(odds_data, home, away) if odds_data else {}

        message = f"📅 *Match:* {home_escaped} vs {away_escaped}\n"
        message += f"⏰ *Kickoff:* {date_str} at {time_str}\n"
        message += "─────────────────\n"

        message += "🟩 *MONEY LINE WINNER:*\n"
        message += f"{analysis.get('money_line', '⚠️ No data')}\n"
        message += "─────────────────\n"

        message += "📊 *SPREAD WINNER:*\n"
        message += f"{analysis.get('spread', '⚠️ No data')}\n"
        message += "─────────────────\n"

        message += "📈 *OVER/UNDER WINNER:*\n"
        message += f"{analysis.get('over_under', '⚠️ No data')}\n"
        message += "─────────────────\n"

        message += "✌️ *DOUBLE CHANCE WINNER:*\n"
        message += f"{analysis.get('double_chance', '⚠️ No data')}\n"
        message += "─────────────────\n"

        message += "💡 *TIP:* Picks are based on best bookmaker odds & probabilities\n"

        return message

    except Exception as e:
        print(f"⚠️ Message formatting error: {e}")
        return "⚠️ Error formatting message"
# ===== Main Run =====
if __name__ == "__main__":
    print("🚀 Running Betting Alert Script...")

    odds_data = get_odds_data()
    fixture_data = get_fixture_data()

    message = format_telegram_message(odds_data, fixture_data)
    print("📨 Message:\n", message)

    send_telegram_message(message)

    print("✅ Script complete.")
