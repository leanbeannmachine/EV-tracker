import requests

def get_bovada_odds():
    url = "https://www.bovada.lv/services/sports/event/v2/events/soccer"

    try:
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"Error fetching Bovada data: Status code {resp.status_code}")
            return []

        print("Bovada response preview (first 300 chars):")
        print(resp.text[:300])  # Optional: Remove after debugging

        data = resp.json()[0]['events']
        return data

    except requests.exceptions.RequestException as req_err:
        print("Request failed:", req_err)
        return []

    except ValueError as json_err:
        print("JSON decoding failed:", json_err)
        return []
