import os
import requests

BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"

def send_telegram_message(bet):
    message = (
        f"🔥 +EV Bet Alert 🔥\n\n"
        f"🏟 Match: {bet['match']}\n"
        f"📈 Market: {bet['market']}\n"
        f"💰 Odds: {bet['odds']}\n"
        f"✅ EV: {bet['ev'] * 100:.2f}%\n\n"
        f"🏦 Book: {bet['book']}"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram send error:", e)
