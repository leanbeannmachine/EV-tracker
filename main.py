import requests
import datetime
import pytz
import telegram

# ====== CONFIG ======
API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"  # Your OddsAPI key
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"  # Your Telegram Bot Token
TELEGRAM_CHAT_ID = "964091254"  # Your Telegram Chat ID
TIMEZONE = pytz.timezone('America/Chicago')  # Central Daylight Time

# Minimum EV % threshold for BEST VALUE bets
MIN_EV_THRESHOLD = 5.0  # You can tweak this

# MLB sport key for OddsAPI
SPORT_KEY = "baseball_mlb"

# Bookmakers to consider
BOOKMAKERS = ["pinnacle", "betonlineag"]


# ====== UTILS ======

def american_to_implied_prob(odds):
    """Convert American odds to implied probability."""
    odds = int(odds)
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return -odds / (-odds + 100)


def format_american_odds(odds):
    """Ensure odds show with + or - sign properly."""
    odds = int(odds)
    return f"+{odds}" if odds > 0 else str(odds)


def ev_percentage(model_prob, implied_prob):
    """Calculate expected value %."""
    return (model_prob - implied_prob) * 100  # In percent


def format_datetime(dt_str):
    """Format and convert datetime string from API to CDT."""
    dt_utc = datetime.datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    dt_cdt = dt_utc.astimezone(TIMEZONE)
    return dt_cdt.strftime("%b %d, %I:%M %p CDT")


def pick_emoji(value):
    """Emoji for EV levels."""
    if value >= 10:
        return "💎🟢"  # Diamond + Green circle for best value
    elif value >= 7:
        return "🔥🟢"  # Fire + Green circle for very good value
    elif value >= MIN_EV_THRESHOLD:
        return "🟡"   # Yellow circle for good value
    else:
        return "🔴"   # Red circle for no edge (should not show no edge)


# ====== FETCH AND PROCESS ODDS ======

def fetch_odds():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "bookmakers": ",".join(BOOKMAKERS),
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def process_matchup(matchup):
    home_team = matchup.get("home_team")
    away_team = matchup.get("away_team")
    commence_time = format_datetime(matchup.get("commence_time"))

    # Collect all moneyline, spread, totals odds from bookmakers
    moneylines = []
    spreads = []
    totals = []

    for bookmaker in matchup.get("bookmakers", []):
        if bookmaker["key"] not in BOOKMAKERS:
            continue
        for market in bookmaker.get("markets", []):
            if market["key"] == "h2h":
                for outcome in market["outcomes"]:
                    # Add team, odds
                    team = outcome["name"]
                    odds = outcome["price"]
                    implied = american_to_implied_prob(odds)
                    moneylines.append({
                        "team": team,
                        "odds": odds,
                        "implied_prob": implied,
                        "bookmaker": bookmaker["title"],
                    })
            elif market["key"] == "spreads":
                for outcome in market["outcomes"]:
                    team = outcome["name"]
                    odds = outcome["price"]
                    point = outcome.get("point")
                    implied = american_to_implied_prob(odds)
                    spreads.append({
                        "team": team,
                        "odds": odds,
                        "point": point,
                        "implied_prob": implied,
                        "bookmaker": bookmaker["title"],
                    })
            elif market["key"] == "totals":
                for outcome in market["outcomes"]:
                    over_under = outcome["name"]  # "Over" or "Under"
                    odds = outcome["price"]
                    point = outcome.get("point")
                    implied = american_to_implied_prob(odds)
                    totals.append({
                        "over_under": over_under,
                        "odds": odds,
                        "point": point,
                        "implied_prob": implied,
                        "bookmaker": bookmaker["title"],
                    })

    return {
        "home_team": home_team,
        "away_team": away_team,
        "commence_time": commence_time,
        "moneylines": moneylines,
        "spreads": spreads,
        "totals": totals,
    }


def model_probability_stub(team_name):
    """
    Stub for model probability:
    Right now returns a slight variation around implied probability + random small margin.
    This should be replaced with your real model later.
    """
    import random
    base = 0.5  # baseline 50%
    variation = random.uniform(-0.1, 0.1)
    return max(0, min(1, base + variation))


def select_best_bet(bets, bet_type):
    """
    Given a list of bets (moneyline/spread/total), compute EV, model prob, edge,
    and return only the best one above MIN_EV_THRESHOLD.
    """
    best_bet = None
    best_ev = float("-inf")

    for bet in bets:
        model_prob = model_probability_stub(bet.get("team") or bet.get("over_under") or "")
        implied_prob = bet["implied_prob"]
        ev = ev_percentage(model_prob, implied_prob)
        edge = ev
        if ev >= MIN_EV_THRESHOLD and ev > best_ev:
            best_ev = ev
            best_bet = {
                **bet,
                "ev": ev,
                "model_prob": model_prob,
                "edge": edge,
            }
    return best_bet


# ====== FORMAT MESSAGE ======

def build_message(matchup):
    home = matchup["home_team"]
    away = matchup["away_team"]
    time = matchup["commence_time"]

    # Select best bets
    best_ml_home = select_best_bet(
        [bet for bet in matchup["moneylines"] if bet["team"] == home],
        "moneyline",
    )
    best_ml_away = select_best_bet(
        [bet for bet in matchup["moneylines"] if bet["team"] == away],
        "moneyline",
    )
    best_ml = best_ml_home if (best_ml_home and (not best_ml_away or best_ml_home["ev"] >= best_ml_away["ev"])) else best_ml_away

    best_spread_home = select_best_bet(
        [bet for bet in matchup["spreads"] if bet["team"] == home],
        "spread",
    )
    best_spread_away = select_best_bet(
        [bet for bet in matchup["spreads"] if bet["team"] == away],
        "spread",
    )
    best_spread = best_spread_home if (best_spread_home and (not best_spread_away or best_spread_home["ev"] >= best_spread_away["ev"])) else best_spread_away

    best_total_over = select_best_bet(
        [bet for bet in matchup["totals"] if bet["over_under"].lower() == "over"],
        "total",
    )
    best_total_under = select_best_bet(
        [bet for bet in matchup["totals"] if bet["over_under"].lower() == "under"],
        "total",
    )
    best_total = best_total_over if (best_total_over and (not best_total_under or best_total_over["ev"] >= best_total_under["ev"])) else best_total_under

    if not any([best_ml, best_spread, best_total]):
        # No bets qualify as best value over threshold, skip message
        return None

    # Header & odds summary line
    header = f"🏟️ {home} vs {away}\n📅 {time}"
    ml_line = " | ".join([
        f"{best_ml['team']}: {format_american_odds(best_ml['odds'])}" if best_ml else "",
        ])
    spread_line = " | ".join([
        f"{best_spread['team']} {best_spread['point']} @ {format_american_odds(best_spread['odds'])}" if best_spread else "",
    ])
    total_line = ""
    if best_total:
        point = best_total["point"]
        ou = best_total["over_under"]
        odds = format_american_odds(best_total["odds"])
        total_line = f"{point} — {ou} @ {odds}"

    message = f"{header}\n🏆 ML: {ml_line}\n📏 Spread: {spread_line}\n📊 Total: {total_line}\n\n━━━━━━━━━━━━━━━━━━\n"

    def format_bet(bet, bet_type):
        ev = bet["ev"]
        emoji = pick_emoji(ev)
        return (f"📊 {bet_type.upper()} BET\n"
                f"🔥 Pick: {bet['team'] if 'team' in bet else bet['over_under'] + ' ' + str(bet['point'])}\n"
                f"💵 Odds: {format_american_odds(bet['odds'])}\n"
                f"📈 Expected Value: {ev:+.1f}% {emoji} BEST VALUE\n"
                f"🧮 Implied Prob: {bet['implied_prob']*100:.1f}%\n"
                f"🧠 Model Prob: {bet['model_prob']*100:.1f}%\n"
                f"🔍 Edge: {bet['edge']:+.1f}%\n"
                f"⚾ ——————\n")

    if best_ml:
        message += format_bet(best_ml, "moneyline")
    if best_spread:
        message += format_bet(best_spread, "spread")
    if best_total:
        message += format_bet(best_total, "totals")

    return message


# ====== MAIN ======

def main():
    try:
        odds_data = fetch_odds()
        for matchup in odds_data:
            processed = process_matchup(matchup)
            msg = build_message(processed)
            if msg:
                bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
                bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
