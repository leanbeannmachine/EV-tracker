import requests
import os

BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
CHAT_ID = "964091254"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("✅ Message sent.")
    except Exception as e:
        print(f"❌ Telegram error: {e}")

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("✅ Message sent.")
    except Exception as e:
        print(f"❌ Telegram error: {e}")
