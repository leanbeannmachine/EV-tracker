def calculate_ev(probability, odds):
    return (probability * (odds - 1)) - (1 - probability)

def find_ev_bets(odds_list, threshold=0.05):
    ev_bets = []
    for bet in odds_list:
        ev = calculate_ev(bet["probability"], bet["odds"])
        if ev > threshold:
            bet["ev"] = round(ev, 4)
            ev_bets.append(bet)
    return ev_bets