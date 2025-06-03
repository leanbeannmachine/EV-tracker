import requests

def get_bovada_odds():
    url = "https://www.bovada.lv/services/sports/event/v2/en/lines"
    resp = requests.get(url)
    data = resp.json()[0]['events']
    
    odds = []
    for event in data:
        try:
            sport = event['sport']
            teams = event['competitors']
            markets = event['displayGroups'][0]['markets']
            for market in markets:
                for outcome in market['outcomes']:
                    odds.append({
                        "sport": sport,
                        "match": f"{teams[0]['name']} vs {teams[1]['name']}",
                        "bet": outcome['description'],
                        "price": outcome['price']['american']
                    })
        except Exception:
            continue
    return odds
