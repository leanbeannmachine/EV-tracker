import requests
import datetime
import os
from telegram import Bot

# 🔑 Your credentials (already plugged in)
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
ODDS_API_KEY = "85c7c9d1acaad09cae7e93ea02f627ae"

# 📅 Only pull today's MLB games
today = datetime.datetime.utcnow()
today_str = today.strftime("%Y-%m-%d")
url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
params = {
    "apiKey": ODDS_API_KEY,
    "regions": "us",
    "markets": "h2h,spreads,totals",
    "oddsFormat": "american",
    "dateFormat": "iso",
}

def get_game_trends(home_team, away_team):
    # Dummy logic — customize with real data if needed
    trends = {
        home_team: "❄️ 1-4 in last 5 vs division",
        away_team: "🔥 4-1 ATS in last 5",
    }
    return trends

def get_value_tag(odds):
    if odds is None:
        return "❓"
    try:
        odds = int(odds)
        if odds >= 150 or odds <= -150:
            return "❌"
        elif 120 <= abs(odds) < 150:
            return "⚠️"
        else:
            return "✅"
    except:
        return "❓"

def send_telegram_message(message):
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        print(f"Telegram error: {e}")

def format_game(game):
    bookmaker = game.get("bookmakers", [])[0] if game.get("bookmakers") else None
    if not bookmaker:
        return None

    comm = []
    home = game["home_team"]
    away = game["away_team"]
    start_time = game["commence_time"].replace("T", " ").replace("Z", " UTC")
    book = bookmaker["title"]
    markets = {m["key"]: m for m in bookmaker["markets"]}

    # Moneyline
    h2h = markets.get("h2h", {}).get("outcomes", [])
    moneyline_lines = {
        outcome["name"]: outcome["price"] for outcome in h2h
    }

    # Spread
    spread_lines = {
        outcome["name"]: (outcome["point"], outcome["price"])
        for outcome in markets.get("spreads", {}).get("outcomes", [])
    }

    # Totals
    total_lines = {
        outcome["name"]: (outcome["point"], outcome["price"])
        for outcome in markets.get("totals", {}).get("outcomes", [])
    }

    # Build Message
    comm.append(f"📊 MLB Bet Preview")
    comm.append(f"🕒 {start_time}")
    comm.append(f"⚔️ {away} @ {home}")
    comm.append(f"🏦 {book} Sportsbook\n")

    comm.append("💰 Moneyline:")
    for team, odd in moneyline_lines.items():
        comm.append(f"- {team}: {odd} {get_value_tag(odd)}")

    comm.append("\n🟩 Spread:")
    for team, (pt, price) in spread_lines.items():
        comm.append(f"- {team} {pt}: {price} {get_value_tag(price)}")

    comm.append("\n📈 Total:")
    for team, (pt, price) in total_lines.items():
        comm.append(f"- {team} {pt}: {price} {get_value_tag(price)}")

    # 🔥 Trends
    trends = get_game_trends(home, away)
    comm.append("\n📊 Trends:")
    comm.append(f"- {away}: {trends.get(away)}")
    comm.append(f"- {home}: {trends.get(home)}")

    # Final lean based on spread (dummy logic)
    lean_line = f"🔎 *Lean: {away} +1.5 spread ✅*"
    comm.append(f"\n{lean_line}")
    comm.append("📌 Bet smart. Look for 🔒 low-risk run lines.")

    return "\n".join(comm)

def main():
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            send_telegram_message(f"🚨 OddsAPI Error: {response.status_code}\n{response.text}")
            return

        games = response.json()
        today_games = [g for g in games if g["commence_time"].startswith(today_str)]

        if not today_games:
            send_telegram_message("📭 No MLB bets available for today.")
            return

        for game in today_games:
            msg = format_game(game)
            if msg:
                send_telegram_message(msg)
                time.sleep(2)
    except Exception as e:
        send_telegram_message(f"🚨 Script error:\n{e}")

if __name__ == "__main__":
    main()
