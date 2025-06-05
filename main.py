
from datetime import datetime

def format_bet_message(match):
    home = match.get("home_team", "Home")
    away = match.get("away_team", "Away")
    start_time_raw = match.get("commence_time", "")
    start_time = datetime.strptime(start_time_raw, "%Y-%m-%dT%H:%M:%SZ")
    start_str = start_time.strftime("%A, %B %d at %I:%M %p EST")

    markets = match.get("bookmakers", [{}])[0].get("markets", [])
    odds_summary = ""
    best_pick = ""
    risk_tag = "🟢 Best Value"  # Default tag

    for market in markets:
        if market["key"] == "h2h":
            for outcome in market["outcomes"]:
                team = outcome.get("name")
                odd = outcome.get("price")
                odds_summary += f"• {team}: {odd}\n"
                if odd and 130 <= abs(odd) <= 170:
                    best_pick = f"Moneyline: {team}"
        elif market["key"] == "spreads":
            for outcome in market["outcomes"]:
                spread = outcome.get("point")
                team = outcome.get("name")
                odds_summary += f"• Spread {team}: {spread} @ {outcome.get('price')}\n"
        elif market["key"] == "totals":
            for outcome in market["outcomes"]:
                point = outcome.get("point")
                pick = outcome.get("name")
                odds_summary += f"• Total {pick} {point} @ {outcome.get('price')}\n"
                if pick == "Over":
                    best_pick = f"Over {point} Runs"

    # Fallback if no best pick detected
    if not best_pick:
        best_pick = "Most favorable odds detected (Moneyline or Over)"

    # Risk color coding
    odds = [o.get("price") for m in markets for o in m.get("outcomes", []) if o.get("price")]
    avg_odds = sum(map(abs, odds)) / len(odds) if odds else 100
    if avg_odds > 150:
        risk_tag = "🟢 Best Value"
    elif avg_odds > 120:
        risk_tag = "🟡 Low Value"

    message = f"""🔥 *Bet Alert!*
{risk_tag}

🏟️ *{away} @ {home}*
🕒 *Start:* {start_str}
💵 *Odds:*
{odds_summary.strip()}
✅ *Pick:* {best_pick}

📊 *Why?*
• Odds range shows {risk_tag.lower()}
• {match.get("team_form", "Model favors recent consistency")}
• Auto-filtered for optimal daily picks
"""

    return message
