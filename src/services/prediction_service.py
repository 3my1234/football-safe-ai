"""
Prediction Service
Orchestrates ML model, worst-case simulator, filter, and combiner
"""
from typing import List, Dict, Optional
from src.models.train import FootballPredictor
from src.core.worst_case_simulator import WorstCaseSimulator
from src.core.safe_odds_filter import SafeOddsFilter
from src.core.odds_combiner import OddsCombiner


class PredictionService:
    """Main service for generating safe odds predictions"""
    
    def __init__(self, min_odds: float = 1.03, max_odds: float = 1.10):
        self.predictor = FootballPredictor()
        try:
            self.predictor.load()  # Load trained model
        except FileNotFoundError:
            print("⚠️ Model not found. Using default predictions. Train model first.")
            self.predictor.model = None  # Will use fallback
        self.simulator = WorstCaseSimulator()
        self.filter = SafeOddsFilter(min_odds, max_odds)
        self.combiner = OddsCombiner(min_odds, max_odds)
    
    def generate_predictions(
        self, 
        matches: List[Dict]
    ) -> Dict:
        """
        Generate safe odds predictions for today's matches
        
        Returns:
            {
                'combo_odds': float,
                'games_used': int,
                'picks': List[Dict],
                'reason': str,
                'confidence': float
            }
        """
        # Step 1: Generate ML predictions for each match
        raw_predictions = []
        
        for match in matches:
            # Filter match first
            if not self.filter.filter_match(match):
                continue
            
            # Get recommended safe markets
            recommended_markets = self.simulator.get_recommended_markets(match)
            
            # Predict probability for each market
            for market_type in recommended_markets:
                if self.predictor.model:
                    base_prob = self.predictor.predict(match, market_type)
                else:
                    # Fallback: Use conservative estimate based on stats
                    base_prob = self._fallback_prediction(match, market_type)
                
                # Test worst-case scenarios
                worst_case_result = self.simulator.test_all_scenarios(
                    match, market_type, base_prob
                )
                
                # Get odds (simplified - in production, fetch from odds API)
                odds = self._estimate_odds_from_probability(base_prob)
                
                raw_predictions.append({
                    'match_id': match.get('id'),
                    'home_team': match.get('home_team'),
                    'away_team': match.get('away_team'),
                    'market_type': market_type,
                    'odds': odds,
                    'confidence': base_prob,
                    'worst_case_result': worst_case_result,
                    'match_data': match
                })
        
        # Step 2: Filter predictions
        filtered = self.filter.filter_predictions(matches, raw_predictions)
        
        # Step 3: Find best combination
        best_combo = self.combiner.find_best_combination(filtered, max_games=3)
        
        # Step 4: Format response
        if best_combo:
            return self.combiner.format_combo_response(best_combo)
        else:
            return {
                'combo_odds': None,
                'games_used': 0,
                'picks': [],
                'reason': 'No safe combination found in target odds range (1.03-1.10)',
                'confidence': 0.0
            }
    
    def _fallback_prediction(self, match: Dict, market_type: str) -> float:
        """Fallback prediction when model not available"""
        # Conservative estimates based on stats
        if market_type == "over_0.5_goals":
            home_xg = match.get('home_xg', 1.5)
            away_xg = match.get('away_xg', 1.5)
            # Probability that at least 0.5 goals: very high if xG > 1.0
            return min(0.98, 0.85 + (home_xg + away_xg - 1.0) * 0.05)
        elif "over_0.5" in market_type:
            xg = match.get('home_xg' if 'home' in market_type else 'away_xg', 1.5)
            return min(0.95, 0.80 + (xg - 0.5) * 0.15)
        else:
            return 0.75  # Conservative default
    
    def _estimate_odds_from_probability(self, probability: float) -> float:
        """
        Estimate odds from probability
        In production, fetch real odds from API
        
        Formula: odds ≈ 1 / probability
        But add margin for bookmaker profit
        """
        if probability <= 0:
            return 100.0
        if probability >= 1:
            return 1.01
        
        # Convert probability to odds with 5% margin
        implied_odds = 1.0 / probability
        bookmaker_odds = implied_odds * 0.95
        
        # Cap at reasonable range
        return round(min(max(bookmaker_odds, 1.01), 50.0), 2)
    
    def get_raw_predictions(self, matches: List[Dict]) -> List[Dict]:
        """Get raw ML predictions before filtering"""
        raw = []
        
        for match in matches:
            if not self.filter.filter_match(match):
                continue
            
            markets = self.simulator.get_recommended_markets(match)
            
            for market in markets:
                prob = self.predictor.predict(match, market)
                odds = self._estimate_odds_from_probability(prob)
                
                raw.append({
                    'match': f"{match.get('home_team')} vs {match.get('away_team')}",
                    'market': market,
                    'odds': odds,
                    'confidence': prob,
                    'league': match.get('league_tier')
                })
        
        return raw

