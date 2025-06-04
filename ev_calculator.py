def convert_american_to_decimal(american):
    if american.startswith('+'):
        return 1 + (int(american[1:]) / 100)
    else:
        return 1 + (100 / abs(int(american)))

def estimate_prob(decimal_odds):
    return round(1 / decimal_odds, 2)

def calculate_ev(decimal_odds, win_prob):
    return round((decimal_odds * win_prob - 1) * 100, 2)

def find_ev_bets(bets):
    ev_bets = []
    for bet in bets:
        try:
            dec_odds = convert_american_to_decimal(bet['price'])
            win_prob = estimate_prob(dec_odds)  # Placeholder, replace with your model later
            ev = calculate_ev(dec_odds, win_prob)
            if ev > 0.02:  # Filter only good EV bets
                bet['decimal'] = dec_odds
                bet['ev'] = ev
                bet['win_prob'] = win_prob
                ev_bets.append(bet)
        except:
            continue
    return ev_bets
