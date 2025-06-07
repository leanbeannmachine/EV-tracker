import requests
import logging
import numpy as np
from datetime import datetime, timezone
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

# ===== ENHANCED EV CALCULATOR =====
class EVCalculator:
    def __init__(self):
        # Team strength ratings (0-100 scale)
        self.team_ratings = {
            "Los Angeles Dodgers": 92, "Atlanta Braves": 90, "Houston Astros": 89,
            "New York Yankees": 88, "New York Mets": 87, "Toronto Blue Jays": 86,
            "San Diego Padres": 85, "St. Louis Cardinals": 84, "Tampa Bay Rays": 83,
            "Philadelphia Phillies": 82, "Milwaukee Brewers": 81, "Seattle Mariners": 80,
            "Chicago White Sox": 79, "Minnesota Twins": 78, "San Francisco Giants": 77,
            "Boston Red Sox": 76, "Cleveland Guardians": 75, "Baltimore Orioles": 74,
            "Los Angeles Angels": 73, "Arizona Diamondbacks": 72, "Texas Rangers": 71,
            "Chicago Cubs": 70, "Miami Marlins": 69, "Detroit Tigers": 68,
            "Colorado Rockies": 67, "Kansas City Royals": 66, "Pittsburgh Pirates": 65,
            "Cincinnati Reds": 64, "Oakland Athletics": 63, "Washington Nationals": 62
        }
        # Home field advantage factor
        self.home_advantage = 1.04  # 4% boost for home team
        self.initialize_model()

    def initialize_model(self):
        """Initialize a simple prediction model"""
        self.model = LogisticRegression()
        self.scaler = StandardScaler()
        
        # Dummy training data (in real implementation, use historical data)
        X = np.array([[85, 80], [90, 75], [78, 82], [82, 78]])
        y = np.array([1, 1, 0, 1])  # 1 = home win, 0 = away win
        
        # Scale features and train model
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
    
    def calculate_implied_probability(self, american_odds):
        """Convert American odds to implied probability"""
        if american_odds > 0:
            return 100 / (american_odds + 100)
        else:
            return abs(american_odds) / (abs(american_odds) + 100)
    
    def calculate_ev(self, true_prob, odds):
        """Calculate Expected Value"""
        decimal_odds = self.american_to_decimal(odds)
        return (true_prob * decimal_odds) - 1
    
    def american_to_decimal(self, odds):
        """Convert American odds to decimal format"""
        if odds > 0:
            return odds / 100 + 1
        return 100 / abs(odds) + 1
    
    def predict_winner(self, home_team, away_team):
        """Predict winner and win probability"""
        home_rating = self.team_ratings.get(home_team, 75)
        away_rating = self.team_ratings.get(away_team, 75)
        
        # Apply home field advantage
        adjusted_home = home_rating * self.home_advantage
        
        # Create feature vector and predict
        features = np.array([[adjusted_home, away_rating]])
        features_scaled = self.scaler.transform(features)
        
        # Get probabilities
        proba = self.model.predict_proba(features_scaled)[0]
        home_win_prob = proba[1]  # Probability of home win
        away_win_prob = 1 - home_win_prob
        
        # Determine projected winner
        if home_win_prob > away_win_prob:
            return home_team, home_win_prob
        else:
            return away_team, away_win_prob
    
    def analyze_moneyline(self, home_team, away_team, home_odds, away_odds):
        """Analyze moneyline EV and project winner"""
        # Predict winner and probability
        projected_winner, win_prob = self.predict_winner(home_team, away_team)
        
        # Determine which odds to use based on projected winner
        if projected_winner == home_team:
            odds = home_odds
            prob = win_prob
        else:
            odds = away_odds
            prob = 1 - win_prob
        
        # Calculate EV
        ev = self.calculate_ev(prob, odds)
        
        # Calculate value rating
        value_rating = self.get_value_rating(ev)
        
        return {
            "projected_winner": projected_winner,
            "win_prob": win_prob if projected_winner == home_team else 1 - win_prob,
            "odds": odds,
            "ev": ev,
            "value_rating": value_rating,
            "color": self.get_ev_color(ev)
        }
    
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
                    # Parse game time
                    game_time_str = game['gameDate']
                    if game_time_str.endswith('Z'):
                        game_time_str = game_time_str[:-1] + '+00:00'
                    
                    games.append({
                        'mlb_id': str(game['gamePk']),
                        'home': game['teams']['home']['team']['name'],
                        'away': game['teams']['away']['team']['name'],
                        'time': game_time_str,
                        'status': game['status']['detailedState']
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
            "markets": "h2h,totals",
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

# ===== FORMAT GAME TIME =====
def format_game_time(time_str):
    try:
        # Remove milliseconds if present
        if '.' in time_str:
            time_str = time_str.split('.')[0] + 'Z'
        # Ensure UTC timezone format
        if time_str.endswith('Z'):
            time_str = time_str[:-1] + '+00:00'
        elif '+' not in time_str:
            time_str += '+00:00'
            
        dt = datetime.fromisoformat(time_str)
        return dt.strftime("%I:%M %p UTC")
    except Exception as e:
        logger.warning(f"⚠️ Time format error: {str(e)}")
        return time_str

# ===== FORMAT ODDS WITH EV =====
def format_odds(odds_game, home_team, away_team):
    if not odds_game:
        return "⚠️ No odds data available", "⚠️ No odds data available", ""
    
    try:
        money_line = ""
        over_under = ""
        value_alert = ""
        
        # Find bookmaker (prioritize DraftKings or FanDuel)
        bookmaker = None
        for book in odds_game['bookmakers']:
            if book['key'] in ['draftkings', 'fanduel']:
                bookmaker = book
                break
        if not bookmaker and odds_game['bookmakers']:
            bookmaker = odds_game['bookmakers'][0]
        
        if not bookmaker:
            return "⚠️ No odds available", "⚠️ No odds available", ""
        
        # Extract moneyline odds
        home_odds = None
        away_odds = None
        for market in bookmaker['markets']:
            if market['key'] == 'h2h':
                for outcome in market['outcomes']:
                    if outcome['name'] == home_team:
                        home_odds = outcome['price']
                    elif outcome['name'] == away_team:
                        away_odds = outcome['price']
                # Exit after finding the market
                break
        
        # Analyze moneyline with EV model if odds are found
        if home_odds is not None and away_odds is not None:
            analysis = EV_MODEL.analyze_moneyline(
                home_team, away_team, home_odds, away_odds
            )
            
            # Format moneyline with projected winner
            money_line = (
                f"⭐ <b>Projected Winner</b>: {analysis['projected_winner']} "
                f"({analysis['win_prob']:.1%} confidence)\n\n"
                f"🏠 <b>{home_team}</b>: {home_odds}\n"
                f"✈️ <b>{away_team}</b>: {away_odds}\n\n"
                f"{analysis['color']} <b>{analysis['value_rating']}</b> "
                f"(EV: {analysis['ev']:+.2f})"
            )
            
            # Add value alert for significant EV
            if analysis['ev'] > 0.05:
                value_alert = f"💰 <b>+EV BET:</b> {analysis['projected_winner']} (EV: {analysis['ev']:+.2f})"
        else:
            money_line = "⚠️ Moneyline odds not available"
        
        # Extract over/under
        for market in bookmaker['markets']:
            if market['key'] == 'totals':
                over_odds = None
                under_odds = None
                point = market['outcomes'][0]['point']
                
                for outcome in market['outcomes']:
                    if outcome['name'] == 'Over':
                        over_odds = outcome['price']
                    elif outcome['name'] == 'Under':
                        under_odds = outcome['price']
                
                if over_odds is not None and under_odds is not None:
                    over_under = (
                        f"📊 <b>O/U {point}</b>\n"
                        f"⬆️ Over: {over_odds}\n"
                        f"⬇️ Under: {under_odds}"
                    )
                else:
                    over_under = "⚠️ Totals odds not available"
                # Exit after finding the market
                break
        
        return money_line, over_under, value_alert
        
    except Exception as e:
        logger.error(f"❌ Odds formatting error: {str(e)}")
        return "⚠️ Odds format error", "⚠️ Odds format error", ""

# ===== SEND TELEGRAM MESSAGE =====
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        if response.status_code == 200:
            logger.info("✅ Telegram message sent")
        else:
            logger.error(f"⚠️ Telegram error {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"❌ Telegram send error: {str(e)}")

# ===== MAIN FUNCTION =====
def main():
    logger.info("🚀 Starting MLB betting report generator")
    
    # Get today's games
    games = get_mlb_schedule()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    if not games:
        message = f"⚾ <b>MLB Betting Report - {today_str}</b>\n\nNo games scheduled today."
        send_telegram_message(message)
        return
    
    # Get odds data
    odds_data = get_odds_data()
    logger.info(f"📊 Retrieved odds for {len(odds_data)} games")
    
    # Prepare report
    report = f"⚾ <b>MLB Betting Report - {today_str}</b>\n\n"
    value_bets = []
    
    # Process each game
    for game in games:
        # Skip games not scheduled
        if game['status'] not in ['Scheduled', 'Pre-Game', 'Delayed']:
            logger.info(f"Skipping {game['home']} vs {game['away']} (status: {game['status']})")
            continue
            
        # Match game with odds
        odds_game = match_game_with_odds(game, odds_data)
        money_line, over_under, value_alert = format_odds(
            odds_game, game['home'], game['away']
        )
        
        # Add value bets to list
        if value_alert:
            value_bets.append(value_alert)
        
        # Format game time
        game_time = format_game_time(game['time'])
        
        # Add to report
        report += (
            f"<b>{game['away']} @ {game['home']}</b>\n"
            f"⏰ {game_time} | Status: {game['status']}\n\n"
            f"{money_line}\n\n"
            f"{over_under}\n\n"
            "--------------------------------\n\n"
        )
    
    # Add value bets section
    if value_bets:
        report += f"🔥 <b>TOP +EV BETS</b> 🔥\n\n"
        for bet in value_bets:
            report += f"• {bet}\n"
        report += "\n"
    
    # Send report
    logger.info(f"📝 Generated report: {len(games)} games")
    send_telegram_message(report)
    logger.info("✅ Report completed successfully")

# ===== ENTRY POINT =====
if __name__ == "__main__":
    main()
