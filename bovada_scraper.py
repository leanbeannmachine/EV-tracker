import requests

def get_bovada_odds():
    print("Fetching Bovada odds...")

    url = "https://www.bovada.lv/services/sports/event/v2/events/A/description"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"❌ Request to Bovada failed: {e}")
        return []

    try:
        sports_data = resp.json()
    except Exception as e:
        print("❌ Failed to parse Bovada data as JSON.")
        print(f"Bovada response preview (first 300 chars):\n{resp.text[:300]}")
        print(f"Error: {e}")
        return []

    if not sports_data:
        print("⚠️ Bovada returned an empty data set.")
        return []

    print("✅ Successfully fetched Bovada odds.")
    events = []
    for group in sports_data:
        for event in group.get('events', []):
            events.append(event)

    return events
