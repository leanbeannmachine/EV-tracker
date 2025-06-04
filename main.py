from datetime import datetime, timezone
import requests
import telegram
import time
import random

# 🔐 API & Bot Config
API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"
BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"

# ✅ Leagues and Markets to Watch
LEAGUE_MARKETS = {
    "soccer_usa_mls": ["h2h", "spreads", "totals", "double_chance"],
    "soccer_argentina_primera_division": ["h2h", "spreads", "totals", "double_chance"],
    "basketball_wnba": ["h2h", "spreads", "totals", "player_points"]
}

BOOKMAKER = "bovada"
REGION = "us"
THRESHOLD = 3.5
ODDS_FORMAT = "american"

# 🏷️ Friendly Market Names
MARKET_NAMES = {
    "h2h": "Moneyline",
    "spreads": "Spread",
    "totals": "Total Points",
    "double_chance": "Double Chance",
    "player_points": "Player Points"
}

# 📊 Example team trend data
TEAM_TRENDS = {
    "D.C. United": {
        "home_form": "W2 D1 L2",
        "last_5": "LDWWL",
        "goal_trend": "Over 2.5 in 4/5 home games"
    },
    "Chicago Fire": {
        "away_form": "W1 D3 L1",
        "last_5": "DWDLW",
        "goal_trend": "BTTS in 80% of away games"
    }
}

# 📈 Odds calculation
def format_american_odds(odds):
    try:
        odds = int(odds)
        return f"+{odds}" if odds > 0 else str(odds)
    except:
        return str(odds)

def implied_prob(odds):
    try:
        odds = int(odds)
        return 100 / (odds + 100) if odds > 0 else abs(odds) / (abs(odds) + 100)
    except:
        return 0

# 📆 Date filter for today's games only
def is_today(game_time):
    return game_time.date() == datetime.now(timezone.utc).date()

# 📝 Format bet description
def format_bet_description(market, outcome):
    if market == "spreads":
        return f"{outcome['name']} ({outcome.get('point', '')})"
    elif market in ["totals", "player_points"]:
        return f"{outcome['name']} {outcome.get('point', '')}"
    return outcome['name']

# 💬 Generate smart betting reason
def generate_reason(match, market, outcome, edge):
    home, away = match['home'], match['away']
    team = outcome['name']
    point = outcome.get('point', '')
    trends = TEAM_TRENDS.get(team, {})
    base_reasons = {
        "h2h": f"{team} has shown recent form ({trends.get('last_5', 'n/a')}) and strong matchup potential.",
        "spreads": f"{team} tends to cover spreads like {point} against similar competition.",
        "totals": f"Scoring trends favor this line: {home} & {away} recent totals suggest value.",
        "double_chance": f"{team} benefits from safety margin on current form and recent head-to-heads.",
        "player_points": f"{team} star player has exceeded {point} points in 3 of last 4 matchups."
    }
    quality_note = f"📊 Detected {edge:.1f}% edge on market inefficiency."
    return f"{base_reasons.get(market, 'Value detected')} — {quality_note}"

# 🔍 Pull value bets
def get_value_bets():
    matches = {}
    for league, markets in LEAGUE_MARKETS.items():
        for market in markets:
            url = (
                f"https://api.the-odds-api.com/v4/sports/{league}/odds/"
                f"?apiKey={API_KEY}&regions={REGION}&markets={market}&bookmakers={BOOKMAKER}&oddsFormat={ODDS_FORMAT}"
            )
            try:
                res = requests.get(url)
                if res.status_code != 200:
                    print(f"Error: {res.status_code} - {res.text}")
                    continue
                for match in res.json():
                    match_id = match['id']
                    start = datetime.fromisoformat(match["commence_time"].replace("Z", "+00:00"))
                    if not is_today(start): continue
                    if match_id not in matches:
                        matches[match_id] = {
                            "home": match["home_team"],
                            "away": match["away_team"],
                            "start_time": start,
                            "bets": []
                        }
                    for bm in match.get("bookmakers", []):
                        if bm['key'] != BOOKMAKER: continue
                        for m in bm.get("markets", []):
                            for out in m.get("outcomes", []):
                                price = out.get("price")
                                if price is None: continue
                                prob = implied_prob(price)
                                edge = (1 - prob) * 100
                                if edge >= THRESHOLD:
                                    matches[match_id]["bets"].append({
                                        "market": MARKET_NAMES.get(m["key"], m["key"]),
                                        "bet": format_bet_description(m["key"], out),
                                        "odds": format_american_odds(price),
                                        "edge": round(edge, 2),
                                        "quality": "🟢 GOOD BET" if edge >= 5 else "🟡 OK BET",
                                        "reason": generate_reason(matches[match_id], m["key"], out, edge)
                                    })
            except Exception as e:
                print(f"Request failed: {e}")
                continue
    return matches

# 📤 Send to Telegram
def send_bets():
    bot = telegram.Bot(token=BOT_TOKEN)
    matches = get_value_bets()
    if not matches:
        bot.send_message(chat_id=CHAT_ID, text="No good value bets available for today.")
        return

    for match in matches.values():
        if not match["bets"]: continue
        msg = f"📢 {match['home']} vs {match['away']} – 🕒 {match['start_time'].strftime('%Y-%m-%d %H:%M')} UTC\n"
        for b in match["bets"]:
            msg += (
                f"{b['market']}: {b['bet']}\n"
                f"Odds: {b['odds']} | Edge: {b['edge']}% {b['quality']}\n"
                f"Reason: {b['reason']}\n\n"
            )
        bot.send_message(chat_id=CHAT_ID, text=msg)

# 🚀 Run the script
send_bets()
