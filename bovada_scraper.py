import requests

def get_bovada_odds():
    print("Fetching Bovada odds...")

    url = "https://www.bovada.lv/services/sports/event/v2/events/A/description"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.bovada.lv/",
        "Origin": "https://www.bovada.lv",
        "Connection": "keep-alive",
        "Accept-Language": "en-US,en;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        if response.status_code != 200:
            print(f"❌ Bovada returned status code {response.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"❌ Request to Bovada failed: {e}")
        return []

    try:
        json_data = response.json()
        print("✅ Bovada response parsed successfully.")
    except Exception as e:
        print(f"❌ Failed to parse Bovada data. Preview:\n{response.text[:300]}")
        print(f"Error: {e}")
        return []

    # Extract events from all groups
    events = []
    for sport in json_data:
        events.extend(sport.get('events', []))

    return events
