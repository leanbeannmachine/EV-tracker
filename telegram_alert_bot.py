import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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