# bet_formatter.py

def format_bet_message(bet):
    """
    Format a single betting alert message with emojis, clarity, and data.
    Accepts a dictionary with keys:
    - league, teams, odds, win_prob, quality (green/yellow/red), reasoning, start_time
    """
    emoji_map = {
        'green': '✅ Top Value',
        'yellow': '⚠️ Decent Pick',
        'red': '❌ Risky Bet'
    }

    quality_tag = emoji_map.get(bet.get('quality', 'yellow'), '⚠️ Bet')

    message = (
        f"{quality_tag}\n"
        f"🏆 *{bet['league']}*\n"
        f"🆚 {bet['teams']}\n"
        f"🕒 *Start:* {bet['start_time']}\n"
        f"💰 *Odds:* {bet['odds']} ({bet['win_prob']}% win chance)\n"
        f"🧠 *Why:* {bet['reasoning']}"
    )
    return message
