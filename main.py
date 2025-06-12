import os
import time
import requests
import pytz
from datetime import datetime
import telegram

def send_telegram_alert(message):
    bot_token = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
    chat_id = "964091254"
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print("Failed to send Telegram message:", response.text)
    except Exception as e:
        print("Telegram error:", e)

def calculate_vig_percent(odds1, odds2):
    def implied_prob(odds):
        return abs(odds) / (abs(odds) + 100) if odds < 0 else 100 / (odds + 100)
    prob1 = implied_prob(odds1)
    prob2 = implied_prob(odds2)
    vig = (prob1 + prob2 - 1.0) * 100
    return round(vig, 2)

# ── CONFIG ──
API_KEY           = "8aed519f266c2ab6611693b5c978db8c"      # OddsAPI key
TELEGRAM_TOKEN    = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"  # Telegram bot token
TELEGRAM_CHAT_ID  = "964091254"    # Telegram chat ID
SPORT_KEY         = "baseball_mlb"                   # MLB only
BOOKMAKERS        = "fanduel,bovada"
MARKETS           = "h2h,spreads,totals"
REGION            = "us"
ODDS_FORMAT       = "american"
EV_THRESHOLD_GOOD = 5.0   # minimum EV% for GOOD VALUE
EV_THRESHOLD_BEST = 7.0   # minimum EV% for BEST VALUE
TIMEZONE          = pytz.timezone("America/New_York")

# ── HELPERS ──
def implied_prob(odds):
    odds = int(odds)
    if odds > 0:
        return 100 / (odds + 100)
    return -odds / (-odds + 100)

# ── MLB TEAM ID HELPER ──
def get_mlb_team_ids():
    import requests
    try:
        r = requests.get("https://statsapi.mlb.com/api/v1/teams?sportId=1")
        r.raise_for_status()
        data = r.json()
        return {team["name"]: team["id"] for team in data["teams"]}
    except Exception as e:
        print("MLB Team ID fetch error:", e)
        return {}

def ev_and_edge(model_prob, odds):
    imp = implied_prob(odds)
    edge = model_prob - imp
    ev = edge * 100
    return round(ev, 1), round(imp * 100, 1), round(edge * 100, 1)

def ev_label(ev):
    if ev >= EV_THRESHOLD_BEST:
        return "💎🟢 BEST VALUE"
    if ev >= EV_THRESHOLD_GOOD:
        return "🔝🟡 GOOD VALUE"
    return None

def fmt_time(iso):
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(TIMEZONE)
    return dt.strftime("%b %d, %I:%M %p CDT")

def format_american(odds):
    odds = int(odds)
    return f"+{odds}" if odds > 0 else str(odds)

# ── FETCH ODDS ──
def fetch_odds():
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": REGION,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
        "bookmakers": BOOKMAKERS
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()

# ── BUILD & SEND ALERT ──
def format_bet_section(title, pick, odds, ev, imp_prob, model_prob, vig):
    ev_display = f"{ev:+.1f}%"
    edge_display = f"{(model_prob - imp_prob):+.1f}%"
    vig_display = f"{vig:.2f}%"
    
    return f"""📊 {title.upper()} BET
🔥 Pick: {pick}
💵 Odds: {format_american(odds)}
📈 EV: {ev_display} 💎🟢 BEST VALUE
🧮 Implied Prob: {imp_prob:.1f}%
🧠 Model Prob: {model_prob:.1f}%
🔍 Edge: {edge_display}
⚖️ Vig: {vig_display}
⚾ ——————"""

def send_alert(game):
    try:
        home = game["home_team"]
        away = game["away_team"]
        when = fmt_time(game["commence_time"])

        ml_odds = {}
        spread_odds = {}
        total_odds = {}

        best = {"h2h": None, "spreads": None, "totals": None}
        for bm in game["bookmakers"]:
            for m in bm["markets"]:
                key = m["key"]
                for out in m["outcomes"]:
                    team = out["name"]
                    odds = out["price"]
                    point = out.get("point", "")

                    if key == "h2h":
                        ml_odds[team] = odds
                    elif key == "spreads":
                        spread_odds[f"{team} {point}"] = odds
                    elif key == "totals":
                        total_odds[f"{team} {point}"] = odds

                    model_prob = {"h2h": 0.55, "spreads": 0.53, "totals": 0.58}[key]
                    ev, imp, edge = ev_and_edge(model_prob, odds)
                    label = ev_label(ev)
                    if label and (best[key] is None or ev > best[key]["ev"]):
                        best[key] = {
                            "team": team,
                            "point": point,
                            "odds": odds,
                            "ev": ev,
                            "imp_prob": imp,
                            "model_prob": round(model_prob * 100, 1),
                            "vig": calculate_vig_percent(odds, odds),  # temp default, gets replaced below
                        }

        if not any(best.values()):
            return

        away_ml_odds = format_american(ml_odds.get(away, "N/A"))
        home_ml_odds = format_american(ml_odds.get(home, "N/A"))

        header = (
            f"🏟️ {away} vs {home}\n"
            f"📅 {when}\n"
            f"🏆 ML: {away}: {away_ml_odds} | {home}: {home_ml_odds}\n"
        )

        if best["spreads"]:
            header += f"📏 Spread: {best['spreads']['team']} {best['spreads']['point']} @ {format_american(best['spreads']['odds'])}\n"
        if best["totals"]:
            header += f"📊 Total: {best['totals']['point']} — {best['totals']['team']} @ {format_american(best['totals']['odds'])}\n"

        header += "\n━━━━━━━━━━━━━━━━━━\n"

        sections = []
        if best["h2h"]:
            best["h2h"]["vig"] = calculate_vig_percent(
                ml_odds.get(home, -110), ml_odds.get(away, -110)
            )
            pick = best["h2h"]["team"]
            sections.append(format_bet_section("moneyline", pick, **best["h2h"]))

        if best["spreads"]:
            key = best["spreads"]["team"] + " " + str(best["spreads"]["point"])
            opp = next((v for k, v in spread_odds.items() if k != key), -110)
            best["spreads"]["vig"] = calculate_vig_percent(
                best["spreads"]["odds"], opp
            )
            pick = best["spreads"]["team"] + " " + str(best["spreads"]["point"])
            sections.append(format_bet_section("spread", pick, **best["spreads"]))

        if best["totals"]:
            key = best["totals"]["team"] + " " + str(best["totals"]["point"])
            opp = next((v for k, v in total_odds.items() if k != key), -110)
            best["totals"]["vig"] = calculate_vig_percent(
                best["totals"]["odds"], opp
            )
            pick = best["totals"]["team"] + " " + str(best["totals"]["point"])
            sections.append(format_bet_section("totals", pick, **best["totals"]))

        msg = header + "\n".join(sections)
        send_telegram_alert(msg)
        time.sleep(2)

    except Exception as e:
        print(f"Error processing game: {away} vs {home} — {e}")
    
# ── MAIN ──
def main():
    try:
        games = fetch_odds()
    except Exception as e:
        print("Fetch error:", e)
        return

    team_ids = get_mlb_team_ids()  # ✅ Fetch MLB team IDs once
    today = datetime.now(TIMEZONE).date()  # ✅ Get today's date

    for g in games:
        home = g["home_team"]
        away = g["away_team"]

        if home not in team_ids or away not in team_ids:
            continue

        try:
            game_time = datetime.fromisoformat(g["commence_time"].replace("Z", "+00:00")).astimezone(TIMEZONE)
        except Exception as e:
            print(f"Time parse error for {away} vs {home}:", e)
            continue

        if game_time.date() != today:
            continue

        try:
            bookmaker = g['bookmakers'][0]
            markets = {m['key']: m for m in bookmaker['markets']}

            # === MONEYLINE ===
            ml = markets['h2h']
            ml_home = ml['outcomes'][0]['price']
            ml_away = ml['outcomes'][1]['price']
            vig_ml = calculate_vig_percent(ml_home, ml_away)

            # === SPREAD ===
            spread = markets['spreads']
            sp_home = spread['outcomes'][0]
            sp_away = spread['outcomes'][1]
            spread_pick = sp_home['name']
            spread_line = sp_home['point']
            spread_odds = sp_home['price']
            spread_opposite_odds = sp_away['price']
            vig_spread = calculate_vig_percent(spread_odds, spread_opposite_odds)

            # === TOTALS ===
            total = markets['totals']
            over = total['outcomes'][0]
            under = total['outcomes'][1]
            total_line = over['point']
            total_odds = over['price']
            total_opposite_odds = under['price']
            vig_total = calculate_vig_percent(total_odds, total_opposite_odds)

            # === MODEL + EV EXAMPLE LOGIC (TEMP) ===
            model_prob_ml = 0.55
            implied_prob_ml = 100 / (ml_away + 100) if ml_away > 0 else abs(ml_away) / (abs(ml_away) + 100)
            ev_ml = round((model_prob_ml * (ml_away if ml_away > 0 else ml_away / 100)) - (1 - model_prob_ml), 4) * 100
            edge_ml = round((model_prob_ml - implied_prob_ml) * 100, 1)

            game_time_str = game_time.strftime('%b %d, %I:%M %p CDT')

            # === BUILD & SEND ALERT ===
            alert_msg = f"""
🏟️ {home} vs {away}
📅 {game_time_str}
🏆 ML: {home}: {ml_home} | {away}: {ml_away}
📏 Spread: {spread_pick} {spread_line} @ {spread_odds}
📊 Total: {total_line} — Over @ {total_odds}

━━━━━━━━━━━━━━━━━━
📊 MONEYLINE BET
🔥 Pick: {away}
💵 Odds: {ml_away}
📈 EV: +{ev_ml:.1f}% 💎🟢 BEST VALUE
🧮 Implied Prob: {implied_prob_ml*100:.1f}%
🧠 Model Prob: {model_prob_ml*100:.1f}%
🔍 Edge: +{edge_ml:.1f}%
⚖️ Vig: {vig_ml}%
⚾ ——————
📊 SPREAD BET
🔥 Pick: {spread_pick} {spread_line}
💵 Odds: {spread_odds}
📈 EV: +8.0% 💎🟢 BEST VALUE
🧮 Implied Prob: 45.0%
🧠 Model Prob: 53.0%
🔍 Edge: +8.0%
⚖️ Vig: {vig_spread}%
⚾ ——————
📊 TOTALS BET
🔥 Pick: Over {total_line}
💵 Odds: {total_odds}
📈 EV: +10.4% 💎🟢 BEST VALUE
🧮 Implied Prob: 47.6%
🧠 Model Prob: 58.0%
🔍 Edge: +10.4%
⚖️ Vig: {vig_total}%
⚾ ——————
"""

            send_telegram_alert(alert_msg)  # Replace this with `print(alert_msg)` if testing
            time.sleep(2)

        except Exception as e:
            print(f"Error processing game: {away} vs {home} — {e}")

if __name__ == "__main__":
    main()
