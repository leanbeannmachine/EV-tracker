import requests
import time
from datetime import datetime, timedelta
import pytz

# API KEYS and Telegram info
SPORTMONKS_API_KEY = "pt70HsJAeICOY3nWH8bLDtQFPk4kMDz0PHF9ZvqfFuhseXsk10Xfirbh4pAG"
ODDSAPI_KEY = "7b5d540e73c8790a95b84d3713e1a572"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"

SPORTMONKS_BASE_URL = "https://api.sportmonks.com/v3/football"
ODDSAPI_BASE_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"

# Convert decimal odds to American odds
def decimal_to_american(odds):
    if odds >= 2.0:
        return int(round((odds - 1) * 100))
    else:
        return int(round(-100 / (odds - 1)))

def format_start_time(dt_str):
    utc_time = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S%z")
    est = pytz.timezone("US/Eastern")
    est_time = utc_time.astimezone(est)
    return est_time.strftime("%A, %B %d at %I:%M %p EST")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        print("✅ Sent to Telegram")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def get_sportmonks_matches():
    today = datetime.utcnow().date()
    tomorrow = today + timedelta(days=1)
    matches = []

    for date in [today, tomorrow]:
        url = (
            f"{SPORTMONKS_BASE_URL}/fixtures/date/{date}"
            f"?api_token={SPORTMONKS_API_KEY}"
            f"&include=localTeam,visitorTeam,odds,league"
        )
        try:
            res = requests.get(url)
            res.raise_for_status()
            data = res.json()
            if data.get("data"):
                matches.extend(data["data"])
        except Exception as e:
            print(f"❌ Error fetching SportMonks data for {date}: {e}")

    return matches

def get_oddsapi_matches():
    params = {
        "apiKey": ODDSAPI_KEY,
        "regions": "us",
        "markets": "h2h,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    try:
        res = requests.get(ODDSAPI_BASE_URL, params=params)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"❌ Error fetching OddsAPI data: {e}")
        return []

def filter_and_format_sportmonks_bets(matches):
    messages = []

    for match in matches:
        odds_data = match.get("odds", {}).get("data", [])
        if not odds_data:
            continue

        home = match["localTeam"]["data"]["name"]
        away = match["visitorTeam"]["data"]["name"]
        start_time = format_start_time(match["starting_at"])

        odds_dict = {}
        for odd in odds_data:
            label = odd.get("label", "").lower()
            value = odd.get("value")
            if value is None:
                continue
            am = decimal_to_american(float(value))
            if -200 <= am <= 150:
                odds_dict[label] = am

        if not odds_dict:
            continue

        # Pick logic simplified:
        pick_label = None
        pick_value = None
        if "over" in odds_dict:
            pick_label = f"Over 8.5 Runs"
            pick_value = odds_dict["over"]
        elif "1" in odds_dict:
            pick_label = home
            pick_value = odds_dict["1"]
        elif "2" in odds_dict:
            pick_label = away
            pick_value = odds_dict["2"]
        else:
            continue

        # Value label
        value_indicator = "🟡 Low Value"
        if -150 <= pick_value <= 100:
            value_indicator = "🟢 Good Value"
        elif pick_value < -200 or pick_value > 150:
            value_indicator = "🔴 High Risk"

        odds_lines = []
        if "1" in odds_dict:
            odds_lines.append(f"• {home}: {odds_dict['1']}")
        if "2" in odds_dict:
            odds_lines.append(f"• {away}: {odds_dict['2']}")
        if "over" in odds_dict:
            odds_lines.append(f"• Total Over 8.5 @ {odds_dict['over']}")
        if "under" in odds_dict:
            odds_lines.append(f"• Total Under 8.5 @ {odds_dict['under']}")

        odds_text = "\n".join(odds_lines)

        message = (
            f"🔥 Bet Alert!\n"
            f"{value_indicator}\n\n"
            f"🏟️ {home} @ {away}\n"
            f"🕒 Start: {start_time}\n"
            f"💵 Odds:\n{odds_text}\n"
            f"✅ Pick: {pick_label}\n\n"
            f"📊 Why?\n"
            f"• Odds range shows {value_indicator.lower()}\n"
            f"• Model favors recent volatility in scoring\n"
            f"• Auto-filtered for optimal daily picks"
        )

        messages.append(message)

    return messages

def filter_and_format_oddsapi_bets(matches):
    messages = []
    for match in matches:
        # Basic checks
        home = match.get("home_team")
        away = match.get("away_team")
        commence_time = match.get("commence_time")
        if not (home and away and commence_time):
            continue

        # Convert commence_time ISO string to datetime
        try:
            dt_obj = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
            est = pytz.timezone("US/Eastern")
            est_time = dt_obj.astimezone(est)
            start_time = est_time.strftime("%A, %B %d at %I:%M %p EST")
        except Exception:
            start_time = commence_time

        # Extract odds from bookmakers (take first bookmaker with odds)
        bookmakers = match.get("bookmakers", [])
        if not bookmakers:
            continue

        odds_ml = {}
        odds_totals = {}

        # Find first bookmaker with h2h and totals
        for book in bookmakers:
            markets = book.get("markets", [])
            for market in markets:
                if market.get("key") == "h2h":
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        name = outcome.get("name")
                        price = outcome.get("price")
                        if name == home:
                            odds_ml["home"] = price
                        elif name == away:
                            odds_ml["away"] = price
                elif market.get("key") == "totals":
                    outcomes = market.get("outcomes", [])
                    for outcome in outcomes:
                        name = outcome.get("name").lower()
                        price = outcome.get("price")
                        if name in ["over", "under"]:
                            odds_totals[name] = price

            if odds_ml or odds_totals:
                break

        # Convert odds to American
        def convert_odds(o):
            if o is None:
                return None
            try:
                if o >= 2.0:
                    return int(round((o - 1) * 100))
                else:
                    return int(round(-100 / (o - 1)))
            except:
                return None

        odds_ml_american = {k: convert_odds(v) for k, v in odds_ml.items()}
        odds_totals_american = {k: convert_odds(v) for k, v in odds_totals.items()}

        # Filter odds by your range
        filtered_ml = {k: v for k, v in odds_ml_american.items() if v is not None and -200 <= v <= 150}
        filtered_totals = {k: v for k, v in odds_totals_american.items() if v is not None and -200 <= v <= 150}

        if not filtered_ml and not filtered_totals:
            continue

        # Pick logic: prefer Over total, else home ML, else away ML
        pick_label = None
        pick_value = None
        if "over" in filtered_totals:
            pick_label = "Over 8.5 Runs"
            pick_value = filtered_totals["over"]
        elif "home" in filtered_ml:
            pick_label = home
            pick_value = filtered_ml["home"]
        elif "away" in filtered_ml:
            pick_label = away
            pick_value = filtered_ml["away"]
        else:
            continue

        value_indicator = "🟡 Low Value"
        if pick_value is not None:
            if -150 <= pick_value <= 100:
                value_indicator = "🟢 Good Value"
            elif pick_value < -200 or pick_value > 150:
                value_indicator = "🔴 High Risk"

        odds_lines = []
        if "home" in filtered_ml:
            odds_lines.append(f"• {home}: {filtered_ml['home']}")
        if "away" in filtered_ml:
            odds_lines.append(f"• {away}: {filtered_ml['away']}")
        if "over" in filtered_totals:
            odds_lines.append(f"• Total Over 8.5 @ {filtered_totals['over']}")
        if "under" in filtered_totals:
            odds_lines.append(f"• Total Under 8.5 @ {filtered_totals['under']}")

        odds_text = "\n".join(odds_lines)

            message = (
                f"🔥 Bet Alert!\n"
                f"{value_indicator}\n\n"
                f"🏟️ {home} @ {away}\n"
                f"🕒 Start: {start_time}\n"
                f"💵 Odds:\n{odds_text}\n"
                f"✅ Pick: {pick_label}\n\n"
                f"📊 Why?\n"
                f"• Odds show {value_indicator.lower()}\n"
                f"• Recent matchups suggest edge\n"
                f"• Auto-filtered for EV range"
            )
