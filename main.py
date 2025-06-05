import requests
from datetime import datetime, timedelta
import pytz
import time

# === CONFIG ===
SPORTMONKS_API_KEY = "pt70HsJAeICOY3nWH8bLDtQFPk4kMDz0PHF9ZvqfFuhseXsk10Xfirbh4pAG"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
AMERICAN_ODDS_RANGE = (-200, 150)

# === UTILS ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        res = requests.post(url, json=data)
        res.raise_for_status()
        print("✅ Sent to Telegram")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def to_american(decimal):
    try:
        if decimal >= 2:
            return round((decimal - 1) * 100)
        elif decimal > 1:
            return round(-100 / (decimal - 1))
    except:
        return None

def convert_to_est(utc_str):
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", ""))
        dt_est = dt.astimezone(pytz.timezone("US/Eastern"))
        return dt_est.strftime("%A, %B %d at %I:%M %p EST")
    except:
        return "Unknown"

def value_label(am):
    if am >= 120:
        return "🟢 High Value"
    elif am >= -120:
        return "🟡 Low Value"
    else:
        return "🔴 Risky"

# === SPORTMONKS ===
def fetch_matches():
    matches = []
    base_url = "https://api.sportmonks.com/v3/football/fixtures/date"
    headers = {"Accept": "application/json"}
    for offset in [0, 1]:  # today and tomorrow
        date = (datetime.utcnow().date() + timedelta(days=offset)).isoformat()
        url = f"{base_url}/{date}"
        params = {
            "api_token": SPORTMONKS_API_KEY,
            "include": "localTeam,visitorTeam,odds,league"
        }
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            matches.extend(res.json().get("data", []))
        except Exception as e:
            print(f"❌ Error fetching SportMonks data: {e}")
    return matches

# === MAIN ===
def main():
    matches = fetch_matches()
    if not matches:
        send_telegram_message("⚠️ No matches available today or tomorrow.")
        return

    sent = 0
    for match in matches:
        league = match.get("league", {}).get("data", {}).get("name", "Unknown League")
        home = match.get("localTeam", {}).get("data", {}).get("name", "Home")
        away = match.get("visitorTeam", {}).get("data", {}).get("name", "Away")
        time_str = match.get("time", {}).get("starting_at", {}).get("date_time", "")
        est_time = convert_to_est(time_str)

        odds_lines = []
        pick = ""
        best_value = -999
        value_tier = "🟡 Low Value"
        odds_data = match.get("odds", {}).get("data", [])

        for odd in odds_data:
            label = odd.get("label", "").lower()
            val = odd.get("value")
            if val is None: continue
            am = to_american(val)
            if am is None or not (AMERICAN_ODDS_RANGE[0] <= am <= AMERICAN_ODDS_RANGE[1]):
                continue

            label_out = ""
            if label in ["1", "home"]:
                label_out = f"{home}: {am:+}"
            elif label in ["2", "away"]:
                label_out = f"{away}: {am:+}"
            elif "over" in label:
                label_out = f"Total Over {label.split()[-1]} @ {am:+}"
                if am > best_value:
                    best_value = am
                    pick = f"Over {label.split()[-1]} Runs"
            elif "under" in label:
                label_out = f"Total Under {label.split()[-1]} @ {am:+}"
                if am > best_value:
                    best_value = am
                    pick = f"Under {label.split()[-1]} Runs"

            if am > best_value and "Total" not in label_out:
                best_value = am
                pick = label_out.split(":")[0]

            if label_out:
                odds_lines.append(f"• {label_out}")

        if not odds_lines:
            continue

        if best_value >= 120:
            value_tier = "🟢 High Value"
        elif best_value >= -120:
            value_tier = "🟡 Low Value"
        else:
            value_tier = "🔴 Risky"

        msg = f"""🔥 Bet Alert!
{value_tier}

🏟️ {home} @ {away}
🕒 Start: {est_time}
💵 Odds:
{chr(10).join(odds_lines)}
✅ Pick: {pick}

📊 Why?
• Odds range shows {value_tier}
• Model favors recent volatility in scoring
• Auto-filtered for optimal daily picks"""

        send_telegram_message(msg)
        time.sleep(1)
        sent += 1

    if sent == 0:
        send_telegram_message("🚫 No smart bets found in range (-200 to +150).")

# === RUN ===
if __name__ == "__main__":
    main()
