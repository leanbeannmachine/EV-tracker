import requests
from bs4 import BeautifulSoup

def get_bovada_odds():
    print("🟡 Scraping Bovada MLB page...")
    url = "https://www.bovada.lv/sports/baseball/mlb"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; EVTracker/1.0)"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        script_tags = soup.find_all('script')
        for tag in script_tags:
            if '__INITIAL_STATE__' in tag.text:
                json_str = tag.text.split('__INITIAL_STATE__ = ')[1].split(';</script>')[0]
                print("✅ Found embedded JSON data (truncated)")
                # (Optional: Parse JSON to extract bets here)
                return []  # Return dummy value for now

        print("⚠️ Could not find embedded betting data.")
        return []

    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP request failed: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

    return []
