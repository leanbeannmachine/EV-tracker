import requests

def get_bovada_odds():
    print("Fetching Bovada odds

Got it — if it **didn't find any games**, but **no errors occurred**, then:

---

### 🔎 Possibility 1: Bovada Has No Live MLB Odds Right Now

This happens if:
- All games are already started and locked
- Or games are not yet posted for later

You can **check manually** by visiting:  
🔗 [https://www.bovada.lv/baseball/mlb](https://www.bovada.lv/baseball/mlb)

If you see "No events available" — that confirms it's just bad timing.

---

### 🧪 Possibility 2: API Endpoint Changed Slightly

Sometimes Bovada moves league data under slightly different structures. To **dynamically detect all sports**, we can scan all categories and filter for MLB.

Let’s try that next.

---

### ✅ Try This Universal Scraper Instead

This will **scan all categories**, filter for `mlb` events, and avoid broken hardcoded links.

Replace your `bovada_scraper.py` code with this:

```python
import requests

def get_bovada_odds():
    print("🟡 Connecting to Bovada...")
    url = "https://www.bovada.lv/services/sports/event/v2/us/en"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        mlb_games = []

        for category in data:
            for event in category.get("events", []):
                sport_name = event.get("sport", {}).get("description", "").lower()
                league_name = event.get("league", {}).get("description", "").lower()

                if "mlb" in league_name or "major league baseball" in league_name:
                    mlb_games.append(event)

        print(f"✅ Scraped {len(mlb_games)} MLB games.")
        return mlb_games

    except Exception as e:
        print(f"❌ Failed to fetch Bovada odds: {e}")
        return []
