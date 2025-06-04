def american_to_implied_prob(odds):
    """Convert American odds to implied probability."""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return -odds / (-odds + 100)

def find_high_probability_bets(scraped_bets, min_prob=0.65):
    """Filter bets where at least one side has high implied probability."""
    high_prob_bets = []

    for bet in scraped_bets:
        try:
            odds1 = int(bet['odds'][0].replace('−', '-').replace('+', ''))
            odds2 = int(bet['odds'][1].replace('−', '-').replace('+', ''))
        except:
            continue  # Skip malformed odds

        prob1 = american_to_implied_prob(odds1)
        prob2 = american_to_implied_prob(odds2)

        if prob1 >= min_prob:
            high_prob_bets.append({
                'matchup': bet['matchup'],
                'team': bet['matchup'].split(" vs ")[0],
                'odds': odds1,
                'implied_prob': round(prob1 * 100, 2)
            })

        if prob2 >= min_prob:
            high_prob_bets.append({
                'matchup': bet['matchup'],
                'team': bet['matchup'].split(" vs ")[1],
                'odds': odds2,
                'implied_prob': round(prob2 * 100, 2)
            })

    return high_prob_bets
