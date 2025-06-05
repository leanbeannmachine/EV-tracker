import requests
import datetime
import pytz
import time

# YOUR KEYS
SPORTMONKS_API_KEY = "pt70HsJAeICOY3nWH8bLDtQFPk4kMDz0PHF9ZvqfFuhseXsk10Xfirbh4pAG"
ODDSAPI_KEY = "7b5d540e73c8790a95b84d3713e1a572"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

# Timezone for formatting
LOCAL_TZ = pytz.timezone("US/Eastern")


def to_american(decimal_odds):
    """
    Convert decimal odds to American odds.
    """
    decimal_odds = float(decimal_odds)
    if decimal_odds >= 2.0:
        return f"+{int((decimal_odds - 1) * 100)}"
    else:
        return f"{int(-100 / (decimal_odds - 1))}"


def fetch_sportmonks_matches(date_str):
    """
    Fetch matches from SportMonks API for a given date.
    """
    url = f"https://api.sportmonks.com/v3/football/fixtures/date/{date_str}"
    params = {
        "api_token": SPORTMONKS_API_KEY,
        "include": "localTeam,visitorTeam,odds,league",
    }
    try:
        r = requests.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])
    except Exception as e:
        print(f"❌ Error fetching SportMonks data for {date_str}: {e}")
        return []


def fetch_oddsapi_matches(date_str):
    """
    Fetch matches from OddsAPI for a given date.
    We fetch all sports, filter after.
    """
    url = "https://api.the-odds-api.com/v4/sports/"
    headers = {"x-api-key": ODDSAPI_KEY}
    try:
        # First get sports list
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        sports = r.json()
    except Exception as e:
        print(f"❌ Error fetching sports list from OddsAPI: {e}")
        return []

    all_matches = []
    for sport in sports:
        key = sport.get("key")
        if not key:
            continue
        # Fetch odds for sport for date (today/tomorrow filtering later)
        odds_url = f"https://api.the-odds-api.com/v4/sports/{key}/odds"
        params = {
            "regions": "us",  # Change if you want other regions
            "markets": "h2h,totals",
            "dateFormat": "iso",
            "apiKey": ODDSAPI_KEY,
        }
        try:
            r = requests.get(odds_url, params=params)
            r.raise_for_status()
            matches = r.json()
            all_matches.extend(matches)
        except Exception as e:
            print(f"❌ Error fetching odds for {key}: {e}")

    # Filter matches by date_str (ISO date)
    filtered = []
    for m in all_matches:
        start_time = m.get("commence_time")
        if not start_time:
            continue
        # Convert to date only
        match_date = start_time.split("T")[0]
        if match_date == date_str:
            filtered.append(m)
    return filtered


def filter_odds(odds):
    """
    Filter odds to include only those with American odds between -200 and +150.
    odds: list of dictionaries with keys 'price' or 'odds' in decimal format.
    Return filtered odds with American odds within range.
    """
    filtered = []
    for outcome in odds:
        price = None
        if "price" in outcome:
            price = outcome["price"]
        elif "odds" in outcome:
            price = outcome["odds"]
        else:
            continue
        try:
            price_float = float(price)
        except:
            continue
        american = convert_decimal_to_american(price_float)
        # American odds are strings like '-150' or '+120'
        # Remove + sign for comparison
        if american.startswith("+"):
            val = int(american[1:])
        else:
            val = int(american)
        # Check if val in range -200 to +150 (inclusive)
        if -200 <= val <= 150:
            filtered.append({"name": outcome.get("name", "Unknown"), "american": american, "decimal": price_float})
    return filtered


def convert_decimal_to_american(decimal_odds):
    decimal_odds = float(decimal_odds)
    if decimal_odds >= 2.0:
        return f"+{int(round((decimal_odds - 1) * 100))}"
    else:
        return f"{int(round(-100 / (decimal_odds - 1)))}"


def format_match_time(iso_time):
    dt = datetime.datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
    dt_local = dt.astimezone(LOCAL_TZ)
    return dt_local.strftime("%A, %b %d at %I:%M %p %Z")


def build_message_sportmonks(match):
    # Check for odds data existence
    odds = match.get("odds", {}).get("data", [])
    if not odds:
        return None

    # Extract teams
    local_team = match.get("localTeam", {}).get("data", {}).get("name", "Unknown")
    visitor_team = match.get("visitorTeam", {}).get("data", {}).get("name", "Unknown")

    # Extract league name
    league_name = match.get("league", {}).get("data", {}).get("name", "Unknown League")

    # Match time
    start_time = match.get("starting_at")
    if not start_time:
        return None
    start_time_fmt = format_match_time(start_time)

    # Parse odds markets
    # We want moneyline (h2h) and totals
    moneyline = None
    totals = None
    for odd in odds:
        if odd.get("bookmaker_id") is None:
            continue
        # Odd markets sometimes nested; skipping bookmaker_id==None
        # SportMonks format: market_type field
        if odd.get("type") == "h2h":
            moneyline = odd
        elif odd.get("type") == "totals":
            totals = odd

    # If no moneyline or totals, try to parse odds from first entry as fallback
    if not moneyline and odds:
        moneyline = odds[0]

    if not moneyline:
        return None

    # Extract moneyline outcomes
    ml_outcomes = moneyline.get("outcomes", [])
    filtered_ml = filter_odds(ml_outcomes)
    if not filtered_ml:
        return None

    # Pick best moneyline pick (lowest absolute odds in range)
    ml_pick = min(filtered_ml, key=lambda x: abs(int(x["american"])))

    # Extract totals line if available
    total_line = None
    over_price = None
    under_price = None
    if totals:
        tot_outcomes = totals.get("outcomes", [])
        for o in tot_outcomes:
            if "over" in o.get("name", "").lower():
                over_price = o.get("price")
                total_line = totals.get("line")
            elif "under" in o.get("name", "").lower():
                under_price = o.get("price")

    # Format odds text
    odds_lines = []
    # Moneyline odds for teams
    odds_lines.append(f"• {visitor_team}: {ml_pick['american']}")
    # Find opposing team odds
    # SportMonks odds structure can vary, so try best effort:
    other_teams = [x for x in filtered_ml if x != ml_pick]
    if other_teams:
        odds_lines.append(f"• {local_team}: {other_teams[0]['american']}")
    else:
        odds_lines.append(f"• {local_team}: N/A")

    # Totals odds if present
    if total_line and over_price and under_price:
        odds_lines.append(f"• Total Over {total_line} @ {convert_decimal_to_american(over_price)}")
        odds_lines.append(f"• Total Under {total_line} @ {convert_decimal_to_american(under_price)}")

    odds_text = "\n".join(odds_lines)

    # Build message
    message = (
        "🔥 Bet Alert!\n"
        "🟡 Low Value\n\n"
        f"🏟️ {visitor_team} @ {local_team}\n"
        f"🕒 Start: {start_time_fmt}\n"
        "💵 Odds:\n"
        f"{odds_text}\n"
        f"✅ Pick: {ml_pick['name']}\n\n"
        "📊 Why?\n"
        "• Odds range shows 🟡 low value\n"
        "• Model favors recent volatility in scoring\n"
        "• Auto-filtered for optimal daily picks"
    )
    return message


def build_message_oddsapi(match):
    # Extract teams (adjust keys to match your API response)
    teams = match.get("teams", [])
    if not teams or len(teams) < 2:
        # fallback in case teams info is missing or incomplete
        teams = [match.get("home_team", "Home"), match.get("away_team", "Away")]

    # Extract odds (adjust keys as needed)
    outcomes = match.get("bookmakers", [{}])[0].get("markets", [{}])[0].get("outcomes", [])

    # Filter odds in range -200 to +150
    filtered_outcomes = []
    for outcome in outcomes:
        price = outcome.get("price", 0)
        if -200 <= price <= 150:
            filtered_outcomes.append(outcome)

    # Compose odds text with bullet points using unicode to avoid syntax issues
    odds_text = "\n".join(
        [f"\u2022 {outcome['name']}: {to_american(outcome['price'])}" for outcome in filtered_outcomes]
    )

    # Example: Build message with formatted date/time
    start_time = match.get("commence_time", "TBD")
    # Convert to local time if needed here

    message = (
        "🔥 Bet Alert!\n"
        "🟡 Low Value\n\n"
        f"🏟️ {teams[0]} @ {teams[1]}\n"
        f"🕒 Start: {start_time}\n"
        f"💵 Odds:\n{odds_text}\n"
        "✅ Pick: (Your pick here)\n\n"
        "📊 Why?\n"
        "• Odds range shows 🟡 low value\n"
        "• Model favors recent volatility in scoring\n"
        "• Auto-filtered for optimal daily picks"
    )
    return message
def main():
    # Your main code here: fetch data, send Telegram messages, etc.
    print("Running main process...")
    # Call your fetch and message building functions here
    # e.g.
    # matches = fetch_sportmonks_matches(today_date)
    # for match in matches:
    #    msg = build_message_sportmonks(match)
    #    send_telegram_message(msg)
   if __name__ == "__main__":
    import time
    while True:
        main()
        print("Waiting 15 minutes...")
        time.sleep(15 * 60) 
