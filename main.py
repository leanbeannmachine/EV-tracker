import requests
import logging
import numpy as np
from datetime import datetime, timezone, timedelta
import pytz
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# ===== SET UP LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger()

# ===== CONFIGURATION =====
THE_ODDS_API_KEY = "7b5d540e73c8790a95b84d3713e1a572"
TELEGRAM_BOT_TOKEN = "7607490683:AAH5LZ3hHnTimx35du-UQanEQBXpt6otjcI"
TELEGRAM_CHAT_ID = "964091254"
SPORT = "baseball_mlb"
TIMEZONE = "America/New_York"  # Change to your preferred timezone

# ===== ADVANCED EV CALCULATOR =====
class EVCalculator:
    def __init__(self):
        # Team strength ratings (0-100 scale)
        self.team_ratings = {
            "Los Angeles Dodgers": 94, "Atlanta Braves": 92, "Houston Astros": 90,
            "New York Yankees": 89, "New York Mets": 88, "Toronto Blue Jays": 87,
            "San Diego Padres": 86, "St. Louis Cardinals": 85, "Tampa Bay Rays": 84,
            "Philadelphia Phillies": 83, "Milwaukee Brewers": 82, "Seattle Mariners": 81,
            "Chicago White Sox": 80, "Minnesota Twins": 79, "San Francisco Giants": 78,
            "Boston Red Sox": 77, "Cleveland Guardians": 76, "Baltimore Orioles": 75,
            "Los Angeles Angels": 74, "Arizona Diamondbacks": 73, "Texas Rangers": 72,
            "Chicago Cubs": 71, "Miami Marlins": 70, "Detroit Tigers": 69,
            "Colorado Rockies": 68, "Kansas City Royals": 67, "Pittsburgh Pirates": 66,
            "Cincinnati Reds": 65, "Oakland Athletics": 64, "Washington Nationals": 63
        }
        # Home field advantage factor
        self.home_advantage = 1.04
        # Run scoring factors
        self.offensive_ratings = {
            "New York Yankees": 105, "Los Angeles Dodgers": 104, "Toronto Blue Jays": 103,
            "Atlanta Braves": 102, "Houston Astros": 101, "Boston Red Sox": 100,
            "Chicago White Sox": 99, "Minnesota Twins": 98, "St. Louis Cardinals": 97,
            "San Diego Padres": 96, "Philadelphia Phillies": 95, "Milwaukee Brewers": 94,
            "Seattle Mariners": 93, "San Francisco Giants": 92, "Cleveland Guardians": 91
        }
        self.pitching_ratings = {
            "Los Angeles Dodgers": 105, "New York Mets": 104, "Houston Astros": 103,
            "Tampa Bay Rays": 102, "Toronto Blue Jays": 101, "New York Yankees": 100,
            "Milwaukee Brewers": 99, "San Diego Padres": 98, "Cleveland Guardians": 97,
            "St. Louis Cardinals": 96, "Atlanta Braves": 95, "Philadelphia Phillies": 94,
            "San Francisco Giants": 93, "Seattle Mariners": 92, "Boston Red Sox": 91
        }
        self.initialize_models()
    
    def initialize_models(self):
        """Initialize prediction models for different bet types"""
        # Moneyline model
        self.ml_model = LogisticRegression()
        self.ml_scaler = StandardScaler()
        X_ml = np.array([[85, 80], [90, 75], [78, 82], [82, 78]])
        y_ml = np.array([1, 1, 0, 1])
        X_ml_scaled = self.ml_scaler.fit_transform(X_ml)
        self.ml_model.fit(X_ml_scaled, y_ml)
        
        # Totals model
        self.totals_model = LogisticRegression()
        self.totals_scaler = StandardScaler()
        X_tot = np.array([[85, 80, 8.5], [90, 75, 9.0], [78, 82, 7.5], [82, 78, 8.0]])
        y_tot = np.array([1, 0, 0, 1])  # 1 = over, 0 = under
        X_tot_scaled = self.totals_scaler.fit_transform(X_tot)
        self.totals_model.fit(X_tot_scaled, y_tot)
        
        # Run line model
        self.runline_model = LogisticRegression()
        self.runline_scaler = StandardScaler()
        X_rl = np.array([[85, 80, 1.5], [90, 75, -1.5], [78, 82, 1.5], [82, 78, -1.5]])
        y_rl = np.array([1, 1, 0, 0])  # 1 = favorite covers, 0 = underdog covers
        X_rl_scaled = self.runline_scaler.fit_transform(X_rl)
        self.runline_model.fit(X_rl_scaled, y_rl)
    
    def predict_moneyline(self, home_team, away_team):
        """Predict moneyline winner and probability"""
        home_rating = self.team_ratings.get(home_team, 75)
        away_rating = self.team_ratings.get(away_team, 75)
        adjusted_home = home_rating * self.home_advantage
        
        features = np.array([[adjusted_home, away_rating]])
        features_scaled = self.ml_scaler.transform(features)
        
        proba = self.ml_model.predict_proba(features_scaled)[0]
        home_win_prob = proba[1]
        
        if home_win_prob > 0.5:
            return home_team, home_win_prob
        return away_team, 1 - home_win_prob
    
    def predict_totals(self, home_team, away_team, point):
        """Predict over/under outcome and probability"""
        home_offense = self.offensive_ratings.get(home_team, 100)
        away_offense = self.offensive_ratings.get(away_team, 100)
        home_pitching = self.pitching_ratings.get(home_team, 100)
        away_pitching = self.pitching_ratings.get(away_team, 100)
        
        # Calculate scoring factors
        offense_factor = (home_offense + away_offense) / 200
        pitching_factor = (home_pitching + away_pitching) / 200
        total_factor = offense_factor / pitching_factor
        
        # Create features
        features = np.array([[home_offense, away_offense, point]])
        features_scaled = self.totals_scaler.transform(features)
        
        proba = self.totals_model.predict_proba(features_scaled)[0]
        over_prob = proba[1]
        
        if over_prob > 0.5:
            return "Over", over_prob, point
        return "Under", 1 - over_prob, point
    
    def predict_runline(self, home_team, away_team, spread):
        """Predict run line outcome and probability"""
        home_rating = self.team_ratings.get(home_team, 75)
        away_rating = self.team_ratings.get(away_team, 75)
        adjusted_home = home_rating * self.home_advantage
        
        # Determine favorite
        favorite = home_team if adjusted_home > away_rating else away_team
        
        features = np.array([[adjusted_home, away_rating, spread]])
        features_scaled = self.runline_scaler.transform(features)
        
        proba = self.runline_model.predict_proba(features_scaled)[0]
        cover_prob = proba[1]
        
        return favorite, cover_prob, spread
    
    def calculate_ev(self, true_prob, odds):
        """Calculate Expected Value"""
        if odds > 0:
            decimal_odds = odds / 100 + 1
        else:
            decimal_odds = 100 / abs(odds) + 1
        return (true_prob * decimal_odds) - 1
    
    def get_value_rating(self, ev):
        """Get descriptive value rating"""
        if ev > 0.15: return "STRONG VALUE 🔥"
        if ev > 0.10: return "Good Value 👍"
        if ev > 0.05: return "Mild Value ✅"
        if ev > 0: return "Neutral ⚖️"
        if ev > -0.05: return "Poor Value ❌"
        return "Bad Value 🚫"
    
    def get_ev_color(self, ev):
        """Get color for EV display"""
        if ev > 0.15: return "🟢"
        if ev > 0.10: return "🟩"
        if ev > 0.05: return "🟢"
        if ev > 0: return "🟨"
        if ev > -0.05: return "🟧"
        return "🟥"

# Initialize EV calculator
EV_MODEL = EVCalculator()

# ===== API ENDPOINTS =====
ODDS_URL = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule"

# ===== TIME UTILITIES =====
def convert_to_local_time(utc_time_str):
    """Convert UTC time string to local timezone"""
    try:
        # Handle various datetime formats
        if utc_time_str.endswith('Z'):
            utc_time_str = utc_time_str[:-1] + '+00:00'
        
        # Parse datetime
        dt_utc = datetime.fromisoformat(utc_time_str.replace('Z', '+00:00'))
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        
        # Convert to local timezone
        local_tz = pytz.timezone(TIMEZONE)
        local_time = dt_utc.astimezone(local_tz)
        
        # Format with AM/PM
        return local_time.strftime("%I:%M %p %Z")
    except Exception as e:
        logger.error(f"❌ Time conversion error: {str(e)}")
        return utc_time_str

# ===== FETCH MLB SCHEDULE =====
def get_mlb_schedule():
    try:
        today_utc = datetime.now(timezone.utc).date()
        params = {"date": today_utc, "sportId": 1}
        
        logger.info("📅 Fetching MLB schedule...")
        response = requests.get(SCHEDULE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        games = []
        
        for date in data.get('dates', []):
            for game in date.get('games', []):
                try:
                    # Convert game time to local timezone
                    game_time_local = convert_to_local_time(game['gameDate'])
                    
                    games.append({
                        'mlb_id': str(game['gamePk']),
                        'home': game['teams']['home']['team']['name'],
                        'away': game['teams']['away']['team']['name'],
                        'time': game_time_local,
                        'status': game['status']['detailedState'],
                        'venue': game['venue']['name']
                    })
                except (KeyError, ValueError) as e:
                    logger.warning(f"⚠️ Game parsing error: {str(e)}")
                    continue
        
        logger.info(f"📊 Found {len(games)} MLB games for today")
        return games
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Network error fetching schedule: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Unexpected schedule error: {str(e)}")
    return []

# ===== FETCH ODDS DATA =====
def get_odds_data():
    try:
        logger.info("🎲 Fetching odds from The Odds API...")
        params = {
            "apiKey": THE_ODDS_API_KEY,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
            "dateFormat": "iso"
        }
        response = requests.get(ODDS_URL, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"❌ Odds API error: {str(e)}")
    return []

# ===== MATCH GAMES WITH ODDS =====
def match_game_with_odds(game, odds_data):
    try:
        # Find matching game in odds data
        for odds_game in odds_data:
            home_team = odds_game['home_team']
            away_team = odds_game['away_team']
            
            # Check if teams match (case-insensitive)
            if (game['home'].lower() in home_team.lower() and 
                game['away'].lower() in away_team.lower()):
                return odds_game
    except Exception as e:
        logger.error(f"❌ Error matching odds: {str(e)}")
    return None

# ===== EXTRACT ODDS FOR SPECIFIC MARKET =====
def extract_odds(bookmaker, market_key, outcomes):
    for market in bookmaker['markets']:
        if market['key'] == market_key:
            result = {}
            for outcome in market['outcomes']:
                if outcome['name'] in outcomes:
                    result[outcome['name']] = outcome['price']
                elif 'point' in outcome:
                    result['point'] = outcome['point']
            return result
    return None

# ===== FORMAT ODDS WITH PROJECTIONS =====
def format_odds(odds_game, home_team, away_team):
    if not odds_game:
        return "", "", "", []
    
    try:
        # Find bookmaker (prioritize DraftKings or FanDuel)
        bookmaker = None
        for book in odds_game['bookmakers']:
            if book['key'] in ['draftkings', 'fanduel']:
                bookmaker = book
                break
        if not bookmaker and odds_game['bookmakers']:
            bookmaker = odds_game['bookmakers'][0]
        
        if not bookmaker:
            return "", "", "", []
        
        # Initialize variables
        money_line_section = ""
        runline_section = ""
        totals_section = ""
        value_bets = []
        
        # Process Moneyline
        ml_odds = extract_odds(bookmaker, 'h2h', [home_team, away_team])
        if ml_odds and home_team in ml_odds and away_team in ml_odds:
            winner, win_prob = EV_MODEL.predict_moneyline(home_team, away_team)
            odds = ml_odds[home_team] if winner == home_team else ml_odds[away_team]
            ev = EV_MODEL.calculate_ev(win_prob, odds)
            rating = EV_MODEL.get_value_rating(ev)
            color = EV_MODEL.get_ev_color(ev)
            
            money_line_section = (
                f"⭐ <b>Moneyline Projection</b>: {winner} ({win_prob:.1%} confidence)\n"
                f"🏠 {home_team}: {ml_odds[home_team]}\n"
                f"✈️ {away_team}: {ml_odds[away_team]}\n"
                f"{color} <b>{rating}</b> (EV: {ev:+.2f})\n\n"
            )
            
            if ev > 0.05:
                value_bets.append(f"💰 +EV ML: {winner} {ml_odds[winner]} (EV: {ev:+.2f})")
        
        # Process Run Line (Spread)
        spread_odds = extract_odds(bookmaker, 'spreads', [home_team, away_team])
        if spread_odds and home_team in spread_odds and away_team in spread_odds and 'point' in spread_odds:
            favorite, cover_prob, spread = EV_MODEL.predict_runline(home_team, away_team, spread_odds['point'])
            odds = spread_odds[favorite]
            ev = EV_MODEL.calculate_ev(cover_prob, odds)
            rating = EV_MODEL.get_value_rating(ev)
            color = EV_MODEL.get_ev_color(ev)
            
            underdog = away_team if favorite == home_team else home_team
            runline_section = (
                f"⭐ <b>Run Line Projection</b>: {favorite} covers {spread} ({cover_prob:.1%} confidence)\n"
                f"📏 {home_team} {spread_odds['point']}: {spread_odds[home_team]}\n"
                f"📏 {away_team} {spread_odds['point']}: {spread_odds[away_team]}\n"
                f"{color} <b>{rating}</b> (EV: {ev:+.2f})\n\n"
            )
            
            if ev > 0.05:
                value_bets.append(f"💰 +EV RL: {favorite} covers {spread} (EV: {ev:+.2f})")
        
        # Process Totals (Over/Under)
        totals_odds = extract_odds(bookmaker, 'totals', ['Over', 'Under'])
        if totals_odds and 'Over' in totals_odds and 'Under' in totals_odds and 'point' in totals_odds:
            winner, win_prob, point = EV_MODEL.predict_totals(home_team, away_team, totals_odds['point'])
            odds = totals_odds[winner]
            ev = EV_MODEL.calculate_ev(win_prob, odds)
            rating = EV_MODEL.get_value_rating(ev)
            color = EV_MODEL.get_ev_color(ev)
            
            totals_section = (
                f"⭐ <b>Over/Under Projection</b>: {winner} {point} ({win_prob:.1%} confidence)\n"
                f"⬆️ Over {point}: {totals_odds['Over']}\n"
                f"⬇️ Under {point}: {totals_odds['Under']}\n"
                f"{color} <b>{rating}</b> (EV: {ev:+.2f})\n\n"
            )
            
            if ev > 0.05:
                value_bets.append(f"💰 +EV O/U: {winner} {point} (EV: {ev:+.2f})")
        
        return money_line_section, runline_section, totals_section, value_bets
        
    except Exception as e:
        logger.error(f"❌ Odds formatting error: {str(e)}")
        return "", "", "", []

# ===== SEND TELEGRAM MESSAGE =====
def send_telegram_message(message):
    """Send message to Telegram, splitting if too long"""
    MAX_MSG_LEN = 4000  # Define it locally to fix the NameError
    
    def send_single_message(chunk):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                logger.info("✅ Telegram message sent")
            else:
                logger.error(f"⚠️ Telegram error {response.status_code}: {response.text}")
        except Exception as e:
            logger.error(f"❌ Telegram send error: {str(e)}")
    
    # Split message if it's too long
    if len(message) <= MAX_MSG_LEN:
        send_single_message(message)
        return
    
    # Split the message into chunks
    logger.warning("⚠️ Message too long, splitting into chunks")
    chunks = []
    while message:
        # Find a safe split point (preferably at game separator)
        split_index = message.rfind("────────────────────────", 0, MAX_MSG_LEN)
        if split_index == -1:
            split_index = MAX_MSG_LEN
        
        chunk = message[:split_index]
        chunks.append(chunk)
        message = message[split_index:].lstrip()
    
    # Send all chunks
    for i, chunk in enumerate(chunks):
        send_single_message(f"⚾ Part {i+1}/{len(chunks)}\n{chunk}")

# ===== FORMAT ODDS WITH PROJECTIONS (SIMPLIFIED) =====
def format_odds(odds_game, home_team, away_team):
    """Format odds with EV projections - simplified version"""
    value_bets = []
    output = ""
    
    # Moneyline
    ml_data = None
    for bookmaker in odds_game.get('bookmakers', []):
        if ml_data: break
        ml_data = extract_odds(bookmaker, "h2h", ["home", "away"])
    
    if ml_data:
        home_ml, away_ml = ml_data
        home_prob = EV_MODEL.calculate_ev(home_ml, market="ml", is_home=True)
        away_prob = EV_MODEL.calculate_ev(away_ml, market="ml", is_home=False)
        
        # Determine value bets
        if home_prob > 0.52:  # +EV threshold
            value_bets.append(f"✅ {home_team} ML: {home_ml} (EV: {home_prob:.2f})")
        if away_prob > 0.52:
            value_bets.append(f"✅ {away_team} ML: {away_ml} (EV: {away_prob:.2f})")
            
        output += f"💰 <b>Moneyline</b>\n🏠 {home_team}: {home_ml}\n✈️ {away_team}: {away_ml}\n\n"

    # Run Line
    rl_data = None
    for bookmaker in odds_game.get('bookmakers', []):
        if rl_data: break
        rl_data = extract_odds(bookmaker, "spreads", ["home", "away"])
    
    if rl_data:
        home_rl, away_rl = rl_data
        home_prob = EV_MODEL.calculate_ev(home_rl, market="rl", is_home=True)
        away_prob = EV_MODEL.calculate_ev(away_rl, market="rl", is_home=False)
        
        # Determine value bets
        if home_prob > 0.52:
            value_bets.append(f"✅ {home_team} RL: {home_rl} (EV: {home_prob:.2f})")
        if away_prob > 0.52:
            value_bets.append(f"✅ {away_team} RL: {away_rl} (EV: {away_prob:.2f})")
            
        output += f"📏 <b>Run Line</b>\n🏠 {home_team}: {home_rl}\n✈️ {away_team}: {away_rl}\n\n"

    # Totals
    totals_data = None
    for bookmaker in odds_game.get('bookmakers', []):
        if totals_data: break
        totals_data = extract_odds(bookmaker, "totals", ["over", "under"])
    
    if totals_data:
        over_odds, under_odds = totals_data
        over_prob = EV_MODEL.calculate_ev(over_odds, market="total", is_over=True)
        under_prob = EV_MODEL.calculate_ev(under_odds, market="total", is_over=False)
        
        # Determine value bets
        if over_prob > 0.52:
            value_bets.append(f"✅ Over: {over_odds} (EV: {over_prob:.2f})")
        if under_prob > 0.52:
            value_bets.append(f"✅ Under: {under_odds} (EV: {under_prob:.2f})")
            
        output += f"📊 <b>Totals</b>\n⬆️ Over: {over_odds}\n⬇️ Under: {under_odds}\n\n"
    
    # Add value bets footer
    if value_bets:
        output += "🔥 <b>Value Bets</b>\n" + "\n".join(value_bets) + "\n"
    
    output += "────────────────────────\n"
    return output, value_bets

# ===== MAIN FUNCTION (UPDATED HEADER) =====
def main():
    logger.info("🚀 Starting MLB betting report generator")
    
    # Get today's games
    games = get_mlb_schedule()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    local_time_str = datetime.now(pytz.timezone(TIMEZONE)).strftime("%I:%M %p %Z")
    
    if not games:
        message = (
            f"⚾ <b>MLB Report - {today_str}</b>\n\n"
            f"No games scheduled today.\n\n"
            f"<i>Generated {local_time_str}</i>"
        )
        send_telegram_message(message)
        return
    
    # Get odds data
    odds_data = get_odds_data()
    logger.info(f"📊 Retrieved odds for {len(odds_data)} games")
    
    # Prepare simplified report header
    report = (
        f"⚾ <b>MLB Value Bets - {today_str}</b>\n\n"
        f"🕒 <i>Generated {local_time_str}</i>\n"
        f"🔢 {len(games)} games • {len(odds_data)} with odds\n\n"
        "────────────────────────\n\n"
    )
    
    all_value_bets = []
    games_with_odds = 0
    
    # Process each game
    for game in games:
        # Match game with odds
        odds_game = match_game_with_odds(game, odds_data)
        if not odds_game:
            continue
            
        games_with_odds += 1
        game_header = (
            f"<b>{game['away']} @ {game['home']}</b>\n"
            f"⏰ {game['time']} • {game['status']}\n\n"
        )
        
        # Format odds with projections (simplified)
        odds_section, value_bets = format_odds(
            odds_game, game['home'], game['away']
        )
        
        # Add to report
        report += game_header + odds_section
        all_value_bets.extend(value_bets)
    
    # Add top value bets section if any
    if all_value_bets:
        report += (
            "🔥 <b>TOP VALUE BETS</b>\n\n" +
            "\n".join(all_value_bets) + "\n\n"
        )
    else:
        report += "⚠️ <b>No value bets found today</b>\n\n"
    
    # Add footer
    report += (
        f"<i>Analyzed {games_with_odds}/{len(games)} games</i>\n"
        "⚠️ <i>Gamble responsibly</i>"
    )
    
    # Send report
    logger.info(f"📝 Generated report for {len(games)} games")
    send_telegram_message(report)
    logger.info("✅ Report completed successfully")

# ... [Keep the rest of your existing code unchanged] ...
# ===== MAIN FUNCTION =====
def main():
    logger.info("🚀 Starting MLB betting report generator")
    
    # Get today's games
    games = get_mlb_schedule()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    local_time_str = datetime.now(pytz.timezone(TIMEZONE)).strftime("%I:%M %p %Z")
    
    if not games:
        message = (
            f"⚾ <b>MLB Betting Report - {today_str}</b>\n\n"
            f"No games scheduled today.\n\n"
            f"<i>Generated at {local_time_str}</i>"
        )
        send_telegram_message(message)
        return
    
    # Get odds data
    odds_data = get_odds_data()
    logger.info(f"📊 Retrieved odds for {len(odds_data)} games")
    
    # Prepare report header
    report = (
        f"⚾ <b>MLB BETTING REPORT - {today_str}</b>\n\n"
        f"🕒 <i>Generated at {local_time_str}</i>\n\n"
        f"🔍 <i>{len(games)} games • {len(odds_data)} with odds</i>\n\n"
        "────────────────────────\n\n"
    )
    
    all_value_bets = []
    games_with_odds = 0
    
    # Process each game
    for game in games:
        # Match game with odds
        odds_game = match_game_with_odds(game, odds_data)
        if not odds_game:
            continue
            
        games_with_odds += 1
        game_header = (
            f"<b>{game['away']} @ {game['home']}</b>\n"
            f"🏟️ {game['venue']}\n"
            f"🕒 {game['time']} • {game['status']}\n\n"
        )
        
        # Format odds with projections
        ml_section, rl_section, totals_section, value_bets = format_odds(
            odds_game, game['home'], game['away']
        )
        
        # Build game report
        game_report = game_header
        if ml_section:
            game_report += ml_section
        if rl_section:
            game_report += rl_section
        if totals_section:
            game_report += totals_section
        
        game_report += "────────────────────────\n\n"
        
        # Add to main report
        report += game_report
        all_value_bets.extend(value_bets)
    
    # Add value bets section
    if all_value_bets:
        report += (
            "🔥 <b>TOP +EV BETTING OPPORTUNITIES</b> 🔥\n\n"
            "Maximize your edge with these value plays:\n"
        )
        for bet in all_value_bets:
            report += f"• {bet}\n"
        report += "\n"
    else:
        report += "⚠️ <b>No significant +EV opportunities found today</b>\n\n"
    
    # Add footer
    report += (
        f"<i>Successfully analyzed {games_with_odds} of {len(games)} games</i>\n\n"
        "⚠️ <i>Gamble responsibly • EV projections based on proprietary models</i>"
    )
    
    # Send report
    logger.info(f"📝 Generated report for {len(games)} games")
    send_telegram_message(report)
    logger.info("✅ Report completed successfully")

# ===== ENTRY POINT =====
if __name__ == "__main__":
    main()
