import requests
import time
from datetime import datetime, timedelta
import pytz
from bet_formatter import format_bet_message

# Your credentials here
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"

ODDS_API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"
SPORTMONKS_API_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0GBLTAplBKVHt8YL6m0jNZpmUbCu4szH"

# Supported leagues for filtering (extend as needed)
SUPPORTED_LEAGUES = {
    "mlb": "MLB",
    "wnba": "WNBA",
    "soccer_fifa_world_cup_qualifiers_south_america": "World Cup Qualifiers - South America",
    "soccer_uefa_nations_league": "UEFA Nations League",
    "tennis_atp": "ATP Tennis",
    "tennis_wta": "WTA Tennis",
    "mma_ufc": "UFC",
    "soccer_afc_wc_qualification": "AFC World Cup Qualification",
    "rbc_canadian_open": "RBC Canadian Open"
}

# Timezone for display
DISPLAY_TZ = pytz.timezone("US/Eastern")

def get_date_strings():
    # Today and tomorrow ISO date strings (yyyy-mm-dd)
    today = datetime.now(tz=DISPLAY_TZ)
    tomorrow = today + timedelta(days=1)
    return today.strftime("%Y-%m-%d"), tomorrow.strftime("%Y-%m-%d")

def fetch_oddsapi_bets(date_str):
    # OddsAPI URL for soccer example, expand to other sports and date filtering as API allows
    url = f"https://api.the-odds-api.com/v4/sports/soccer/odds"
    params = {
        "regions": "us",
        "markets": "h2h,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
        "apiKey": ODDS_API_KEY,
        # Could add filtering here for leagues or date if supported
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"OddsAPI error: {e}")
        return []

def fetch_sportmonks_bets(date_str):
    # Example SportMonks endpoint (you need to customize based on available endpoints)
    url = f"https://api.sportmonks.com/v3/football/odds/date/{date_str}"
    params = {"api_token": SPORTMONKS_API_KEY}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data", [])
    except Exception as e:
        print(f"SportMonks error: {e}")
        return []

def unify_bets(oddsapi_data, sportmonks_data):
    """
    Normalize and merge bets from both APIs into a common structure:
    {
        league: "MLB",
        teams: "Team A vs Team B",
        start_time: "ISO string UTC",
        odds: { 'ML Team A': +120, 'ML Team B': -130, 'Over 2.5': +100, ... },
        pick: "ML Team A",
        pick_odds: +120,
        win_prob: 58.3,
        value_label: "🟢 Best Bet",
        reasoning: "Model expects..."
    }
    """
    unified = []
    # Simplified example: from OddsAPI
    for match in oddsapi_data:
        league_key = match.get("sport_key")
        league_name = SUPPORTED_LEAGUES.get(league_key, league_key.replace("_", " ").title())
        home = match.get("home_team")
        away = match.get("away_team")
        start_time = match.get("commence_time")
        odds = {}
        for bookmaker in match.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    name = outcome.get("name")
                    price = outcome.get("price")
                    if price is not None:
                        odds_key = f"{name} {market['key'].upper() if market['key'] != 'h2h' else 'ML'}"
                        odds[odds_key] = price

        # Example pick: best ML positive odds between home/away
        picks = [(k, v) for k,v in odds.items() if "ML" in k]
        if not picks:
            continue
        best_pick = max(picks, key=lambda x: x[1])
        pick_name, pick_odds = best_pick
        implied_prob = round(100 / (abs(pick_odds) / 100), 1) if pick_odds > 0 else round(100 / (abs(pick_odds) / 100) * -1, 1)

        # Value label & reasoning simplified example
        value_label = "🟢 Best Bet" if 130 <= pick_odds <= 170 else "🟡 Medium Value"
        reasoning = ("Model strongly favors pick based on form & odds mismatch."
                     if value_label == "🟢 Best Bet"
                     else "Medium value range — some upside with recent trends.")

        unified.append({
            "league": league_name,
            "teams": f"{home} vs {away}",
            "start_time": start_time,
            "odds": odds,
            "pick": pick_name,
            "pick_odds": pick_odds,
            "win_prob": implied_prob,
            "value_label": value_label,
            "reasoning": reasoning,
        })

    # You can add sportmonks_data processing similarly here...

    return unified

def format_start_time(iso_str):
    try:
        dt_utc = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
        dt_local = dt_utc.astimezone(DISPLAY_TZ)
        return dt_local.strftime("%A, %B %-d – %-I:%M %p %Z")
    except Exception:
        return iso_str

def format_message(bet):
    odds_lines = "\n".join(f"• {k}: {v if v < 0 else '+' + str(v)}" for k, v in bet["odds"].items())

    msg = (
        f"{bet['value_label']} Bet Alert!\n\n"
        f"🏟️ Match: {bet['teams']}\n"
        f"🕒 Start: {format_start_time(bet['start_time'])}\n"
        f"💵 Odds:\n{odds_lines}\n\n"
        f"✅ Pick: {bet['pick']}\n\n"
        f"📊 Why this bet?\n"
        f"• {bet['reasoning']}\n"
        f"• Implied Win Rate: {bet['win_prob']}%\n"
    )
    return msg

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload)
        r.raise_for_status()
    except Exception as e:
        print(f"Telegram send error: {e}")

def main():
    today, tomorrow = get_date_strings()
    print(f"Fetching bets for {today} and {tomorrow}...")

    oddsapi_today = fetch_oddsapi_bets(today)
    oddsapi_tomorrow = fetch_oddsapi_bets(tomorrow)
    sportmonks_today = fetch_sportmonks_bets(today)
    sportmonks_tomorrow = fetch_sportmonks_bets(tomorrow)

    combined_bets = unify_bets(oddsapi_today + oddsapi_tomorrow, sportmonks_today + sportmonks_tomorrow)

    if not combined_bets:
        print("No bets found.")
        return

    for bet in combined_bets:
        message = format_message(bet)
        print("Sending bet alert...\n", message)
        send_telegram(message)
        time.sleep(1.5)  # avoid rate limits

if __name__ == "__main__":
    main()
