import requests
import json
from datetime import datetime, timedelta
import pytz

# --- SETTINGS ---
TELEGRAM_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
ODDS_API_KEY = "9007d620a2ee59fb441c45ffdf058ea6"
SPORTMONKS_KEY = "UGsOsScp4nhqCjJNaZ1HLRf6f0ru0G-BLTAplBKVHt8YL6m0jNZpmUbCu4szH"
ODDSAPI_SPORTS = ["baseball_mlb", "soccer_usa_mls", "soccer_usa_nwsl"]

tz = pytz.timezone("US/Eastern")
today = datetime.now(tz)
tomorrow = today + timedelta(days=1)

def get_today_date_range():
    start = today.replace(hour=0, minute=0, second=0, microsecond=0)
    end = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, end

def american_odds_to_prob(odds):
    # Converts American odds to implied probability
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return -odds / (-odds + 100)

def estimate_mlb_win_prob(game):
    # Placeholder: Basic model for MLB win probability based on starting pitchers or recent form
    # Here: Use moneyline odds implied probabilities as a base, adjusted slightly (for example)
    # In a real deployment, you replace with a model based on team stats, starting pitchers, etc.
    bookmakers = game.get("bookmakers", [])
    if not bookmakers:
        return 0.5
    h2h = next((m for m in bookmakers[0]["markets"] if m["key"] == "h2h"), None)
    if not h2h:
        return 0.5
    probs = [american_odds_to_prob(o["price"]) for o in h2h["outcomes"]]
    # Just return favorite's probability as estimate (simplified)
    return max(probs)

def label_ev(value_diff):
    # Label value bet quality by difference of implied prob vs estimated prob
    if value_diff > 0.07:
        return "🟢 Best Bet"
    elif value_diff > 0.03:
        return "🟡 Medium Value"
    else:
        return "🔴 Low Value"

def format_odds(value):
    return f"{'+' if value > 0 else ''}{value}"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Telegram error:", e)

def fetch_oddsapi_bets():
    start, end = get_today_date_range()
    results = []

    for sport in ODDSAPI_SPORTS:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
            "dateFormat": "iso"
        }
        try:
            r = requests.get(url, params=params)
            if r.status_code != 200:
                print(f"OddsAPI HTTP {r.status_code}: {r.text}")
                continue

            try:
                games = r.json()
            except json.JSONDecodeError:
                print("OddsAPI returned invalid JSON:", r.text)
                continue

            for game in games:
                game_time = datetime.fromisoformat(game["commence_time"].replace("Z", "+00:00")).astimezone(tz)
                if not (start <= game_time <= end):
                    continue

                match = f"{game['home_team']} vs {game['away_team']}"
                bookmakers = game.get("bookmakers", [])

                # EV/value calculation for Moneyline
                ev_analysis = "No value edge detected."
                if bookmakers:
                    h2h = next((m for m in bookmakers[0]["markets"] if m["key"] == "h2h"), None)
                    if h2h:
                        # Take first team for example
                        outcome = h2h["outcomes"][0]
                        implied_prob = american_odds_to_prob(outcome["price"])
                        est_prob = estimate_mlb_win_prob(game)
                        value_diff = est_prob - implied_prob
                        label = label_ev(value_diff)

                        ev_analysis = (
                            f"{label}: Estimated Win Prob {est_prob:.2%} vs Implied {implied_prob:.2%} "
                            f"(Diff {value_diff:.2%})"
                        )

                msg = format_telegram_message(match, game_time, bookmakers, ev_analysis)
                results.append(msg)

        except Exception as e:
            print("OddsAPI error:", e)

    return results

def get_team_form(team_id, fixtures, count=5):
    # Get last 'count' results for a team from fixtures
    recent = []
    for f in sorted(fixtures, key=lambda x: x["time"]["starting_at"]["date_time"], reverse=True):
        local = f["localTeam"]["data"]["id"]
        visitor = f["visitorTeam"]["data"]["id"]
        status = f.get("time", {}).get("status")
        if status != "FT":
            continue
        if team_id == local or team_id == visitor:
            # Win/loss/draw
            home_score = f["scores"]["localteam_score"]
            away_score = f["scores"]["visitorteam_score"]
            if home_score is None or away_score is None:
                continue
            if team_id == local:
                if home_score > away_score:
                    recent.append("W")
                elif home_score == away_score:
                    recent.append("D")
                else:
                    recent.append("L")
            else:
                if away_score > home_score:
                    recent.append("W")
                elif away_score == home_score:
                    recent.append("D")
                else:
                    recent.append("L")
            if len(recent) == count:
                break
    return recent

def estimate_soccer_win_prob(home_form, away_form):
    # Basic model: more wins in last 5 = better chance, add some weighting
    home_wins = home_form.count("W")
    away_wins = away_form.count("W")
    base = 0.5 + (home_wins - away_wins) * 0.06  # each W advantage = +6%
    # Clamp between 0.2 and 0.8 for sanity
    return max(0.2, min(0.8, base))

def format_telegram_message(match, game_time, bookmakers, analysis="No analysis available"):
    msg = f"🟢 *{match}*\n"
    msg += f"📅 {game_time.strftime('%b %d %I:%M %p')}\n"

    if not bookmakers:
        return msg + "\n⚠️ No bookmaker data available."

    markets = {m["key"]: m for m in bookmakers[0].get("markets", [])}

    if "h2h" in markets:
        h2h_odds = markets["h2h"]["outcomes"]
        ml_lines = [f"{o['name']}: {format_odds(o['price'])}" for o in h2h_odds]
        msg += "🏆 ML: " + " | ".join(ml_lines) + "\n"

    if "spreads" in markets:
        spreads = markets["spreads"]["outcomes"]
        spread_lines = [f"{s['name']} {s['point']} @ {format_odds(s['price'])}" for s in spreads]
        msg += "📏 Spread: " + " | ".join(spread_lines) + "\n"

    if "totals" in markets:
        totals = markets["totals"]["outcomes"]
        total_lines = [f"{t['name']} {t['point']} @ {format_odds(t['price'])}" for t in totals]
        msg += "📊 Total: " + " | ".join(total_lines) + "\n"

    msg += f"✅ *Analysis*: {analysis}"

    return msg

def fetch_sportmonks_bets():
    start, end = get_today_date_range()
    url = (
        f"https://soccer.sportmonks.com/api/v2.0/fixtures?"
        f"api_token={SPORTMONKS_KEY}&include=league,localTeam,visitorTeam,scores&date_from={start.strftime('%Y-%m-%d')}&date_to={end.strftime('%Y-%m-%d')}"
    )
    try:
        res = requests.get(url)
        data = res.json()
        matches = data.get("data", [])
        messages = []

        # Fetch recent fixtures for form analysis (last 15 days)
        form_url = (
            f"https://soccer.sportmonks.com/api/v2.0/fixtures?"
            f"api_token={SPORTMONKS_KEY}&include=scores&date_from={(today - timedelta(days=15)).strftime('%Y-%m-%d')}&date_to={today.strftime('%Y-%m-%d')}"
        )
        form_res = requests.get(form_url)
        form_data = form_res.json()
        form_fixtures = form_data.get("data", [])

        for match in matches:
            league = match["league"]["data"]["name"]
            home = match["localTeam"]["data"]["name"]
            away = match["visitorTeam"]["data"]["name"]
            kickoff = datetime.fromisoformat(match["time"]["starting_at"]["date_time"]).astimezone(tz)
            match_str = f"🟢 *{home} vs {away}*\n"
            match_str += f"📅 {kickoff.strftime('%b %d %I:%M %p')}\n"
            match_str += f"🏟️ {league}\n"

            # Historical form: get last 5 results each team
            home_id = match["localTeam"]["data"]["id"]
            away_id = match["visitorTeam"]["data"]["id"]
            home_form = get_team_form(home_id, form_fixtures, 5)
            away_form = get_team_form(away_id, form_fixtures, 5)
            home_form_str = " ".join(home_form) if home_form else "N/A"
            away_form_str = " ".join(away_form) if away_form else "N/A"

            est_prob = estimate_soccer_win_prob(home_form, away_form)

            # We'll pretend bookmaker odds come from OddsAPI for Soccer too (mock)
            # For now just basic value check by comparing estimated prob with implied odds from OddsAPI - simplified:
            ev_label = "🔴 Low Value"
            analysis = f"{home} form: {home_form_str}, {away} form: {away_form_str}. "
            analysis += f"Estimated home win chance ~{est_prob:.0%}. "

            # If we had bookmaker odds, compare implied prob for value; no bookmaker data here, so just basic reasoning
            if est_prob > 0.55:
                ev_label = "🟢 Best Bet"
                analysis += "Good value bet candidate based on form."
            elif est_prob > 0.45:
                ev_label = "🟡 Medium Value"
                analysis += "Moderate value bet candidate."

            match_str += f"✅ *Analysis*: {ev_label} | {analysis}"

            messages.append(match_str)

        return messages

    except Exception as e:
        print("SportMonks error:", e)
        return []

def main():
    print("✅ Fetching OddsAPI bets...")
    oddsapi_bets = fetch_oddsapi_bets()
    print("✅ Fetching SportMonks bets...")
    sportmonks_bets = fetch_sportmonks_bets()

    all_bets = oddsapi_bets + sportmonks_bets
    if all_bets:
        for msg in all_bets:
            send_telegram_message(msg)
        print(f"✅ Sent {len(all_bets)} total bets.")
    else:
        print("⚠️ No bets found.")

if __name__ == "__main__":
    main()
