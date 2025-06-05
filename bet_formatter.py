from datetime import datetime
import pytz

DISPLAY_TZ = pytz.timezone("US/Eastern")

def format_start_time(iso_str):
    try:
        dt_utc = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
        dt_local = dt_utc.astimezone(DISPLAY_TZ)
        return dt_local.strftime("%A, %B %-d – %-I:%M %p %Z")
    except Exception:
        return iso_str

def format_odds_line(key, value):
    # Format odds with + or - sign
    odds_str = f"{value}" if value < 0 else f"+{value}"
    return f"• {key}: {odds_str}"

def format_bet_message(bet):
    """
    Input: bet dict with keys:
    - league (str)
    - teams (str)
    - start_time (ISO str)
    - odds (dict: label -> odds int)
    - pick (str)
    - pick_odds (int)
    - win_prob (float)
    - value_label (str emoji + text)
    - reasoning (str)
    
    Returns: formatted string ready for Telegram
    """
    odds_lines = "\n".join(format_odds_line(k, v) for k, v in bet.get("odds", {}).items())

    msg = (
        f"{bet.get('value_label', '')} Bet Alert!\n\n"
        f"🏟️ Match: {bet.get('teams', 'Unknown')}\n"
        f"🕒 Start: {format_start_time(bet.get('start_time', ''))}\n"
        f"💵 Odds:\n{odds_lines}\n\n"
        f"✅ Pick: {bet.get('pick', 'N/A')}\n\n"
        f"📊 Why this bet?\n"
        f"• {bet.get('reasoning', 'No reasoning provided.')}\n"
        f"• Implied Win Rate: {bet.get('win_prob', 0):.1f}%\n"
    )
    return msg
