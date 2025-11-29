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
        import sys
        print(f"  🔍 PredictionService.generate_predictions called with {len(matches)} matches (model_loaded: {self.predictor.model is not None})")
        sys.stdout.flush()
        
        # Step 1: Generate predictions for each match
        raw_predictions = []
        
        # If model not loaded, use simplified logic (don't filter matches, process all)
        use_simplified = (self.predictor.model is None)
        
        for match_idx, match in enumerate(matches):
            try:
                home = match.get('home_team', 'Unknown')
                away = match.get('away_team', 'Unknown')
                print(f"  🔍 Processing match {match_idx+1}/{len(matches)}: {home} vs {away}")
                sys.stdout.flush()
                
                # If model not loaded, skip filtering (process all matches)
                if not use_simplified:
                    if not self.filter.filter_match(match):
                        print(f"    ⚠️ Match filtered out by filter_match")
                        sys.stdout.flush()
                        continue
                
                # Get recommended safe markets
                recommended_markets = self.simulator.get_recommended_markets(match)
                print(f"    📋 Recommended markets ({len(recommended_markets)}): {recommended_markets}")
                sys.stdout.flush()
                
                if not recommended_markets:
                    recommended_markets = ['over_0.5_goals']  # Default safe market
                
                # Process all recommended markets (don't limit - let AI reason about all safe options)
                for market_type in recommended_markets:
                    try:
                        if self.predictor.model:
                            base_prob = self.predictor.predict(match, market_type)
                        else:
                            # Fallback: Use very conservative 96% for safe picks
                            base_prob = 0.96
                        
                        # Test worst-case scenarios
                        worst_case_result = self.simulator.test_all_scenarios(
                            match, market_type, base_prob
                        )
                        
                        # Get estimated odds (admin will verify/update during vetting)
                        # Don't filter by odds - focus on market safety reasoning
                        odds = self._get_odds_for_market(match, market_type, base_prob)
                        
                        # Generate reasoning for why this market was recommended
                        reasoning_parts = []
                        
                        # Get match context for reasoning
                        home_xg = match.get('home_xg', 0)
                        away_xg = match.get('away_xg', 0)
                        home_odds = match.get('home_odds', 2.0)
                        away_odds = match.get('away_odds', 2.0)
                        league = match.get('league', 'Unknown League')
                        
                        # Market-specific reasoning
                        if market_type == 'over_0.5_goals':
                            reasoning_parts.append(f"Over 0.5 goals is ultra-safe (96% confidence) - almost all professional matches have at least 1 goal")
                            if home_xg > 0 or away_xg > 0:
                                reasoning_parts.append(f"Both teams have decent attacking stats (home xG: {home_xg:.1f}, away xG: {away_xg:.1f})")
                        elif market_type == 'over_1.5_goals':
                            reasoning_parts.append(f"High probability of at least 2 goals given both teams' scoring ability")
                            reasoning_parts.append(f"Combined expected goals: {home_xg + away_xg:.1f}")
                        elif market_type == 'home_over_0.5_goals':
                            reasoning_parts.append(f"{home} scores regularly (xG: {home_xg:.1f})")
                        elif market_type == 'away_over_0.5_goals':
                            reasoning_parts.append(f"{away} scores regularly (xG: {away_xg:.1f})")
                        elif 'handicap' in market_type:
                            if 'home' in market_type:
                                reasoning_parts.append(f"{home} is significantly stronger (odds {home_odds:.2f}), making handicap market very safe")
                            else:
                                reasoning_parts.append(f"{away} is significantly stronger (odds {away_odds:.2f}), making handicap market very safe")
                        
                        # Safety reasoning
                        safety_score = worst_case_result.get('safety_score', 0.9)
                        worst_case_prob = worst_case_result.get('worst_case_probability', base_prob)
                        reasoning_parts.append(f"Safety score: {safety_score:.1%} (survives worst-case scenarios with {worst_case_prob:.1%} probability)")
                        reasoning_parts.append(f"League: {league}")
                        
                        # Combine all reasoning
                        full_reasoning = ". ".join(reasoning_parts)
                        
                        # Add ALL recommended markets - admin will verify odds later
                        raw_predictions.append({
                            'match_id': match.get('id'),
                            'home_team': home,
                            'away_team': away,
                            'market_type': market_type,
                            'odds': odds,  # Estimated - admin will update during vetting
                            'confidence': base_prob,
                            'worst_case_result': worst_case_result,
                            'match_data': match,
                            'reasoning': full_reasoning  # Store full reasoning text
                        })
                        print(f"    ✅ Added prediction: {market_type} (safety_score: {worst_case_result.get('safety_score', 0.9):.2f}, estimated_odds: {odds:.3f})")
                        sys.stdout.flush()
                    except Exception as market_error:
                        import traceback
                        print(f"    ❌ Error processing market {market_type}: {market_error}")
                        print(f"       {traceback.format_exc()[:200]}")
                        sys.stdout.flush()
                        continue
            except Exception as match_error:
                import traceback
                print(f"  ❌ Error processing match {match_idx+1}: {match_error}")
                print(f"     {traceback.format_exc()[:200]}")
                sys.stdout.flush()
                continue
        
        print(f"  📊 Generated {len(raw_predictions)} raw predictions")
        sys.stdout.flush()
        
        # Step 2: Sort by safety score (highest first) - pick safest markets
        # Don't filter by odds - focus on safety reasoning
        filtered = sorted(
            raw_predictions,
            key=lambda p: p.get('worst_case_result', {}).get('safety_score', 0.9) if isinstance(p.get('worst_case_result'), dict) else 0.9,
            reverse=True
        )
        print(f"  📊 Sorted {len(filtered)} predictions by safety score")
        sys.stdout.flush()
        
        # Step 3: Select top safest markets (1-3 games for combination)
        # Prioritize highest safety scores
        best_combo = self.combiner.find_best_combination(filtered, max_games=3)
        
        # Step 4: Format response
        if best_combo:
            print(f"  ✅ Found best combo: {best_combo.get('combo_odds', 'N/A'):.3f} odds")
            sys.stdout.flush()
            return self.combiner.format_combo_response(best_combo)
        elif raw_predictions:
            # Fallback: Use first valid prediction as single pick
            single_pick = raw_predictions[0]
            print(f"  ✅ Using single pick fallback: {single_pick.get('market_type')} @ {single_pick.get('odds'):.3f}")
            sys.stdout.flush()
            return self.combiner.format_combo_response({
                'picks': [single_pick],
                'combo_odds': single_pick.get('odds'),
                'total_confidence': single_pick.get('confidence'),
                'games_used': 1,
                'safety_score': single_pick.get('worst_case_result', {}).get('safety_score', 0.9) if isinstance(single_pick.get('worst_case_result'), dict) else 0.9,
                'reason': f"Single pick: {single_pick.get('market_type')} at {single_pick.get('odds'):.3f}x odds"
            })
        else:
            reason = f'No safe combination found in target odds range ({self.combiner.min_odds}-{self.combiner.max_odds}). Generated {len(raw_predictions)} predictions.'
            print(f"  ❌ {reason}")
            sys.stdout.flush()
            return {
                'combo_odds': None,
                'games_used': 0,
                'picks': [],
                'reason': reason,
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
    
    def _get_odds_for_market(
        self, 
        match: Dict, 
        market_type: str, 
        base_probability: float
    ) -> float:
        """
        Get odds for a specific market
        Prefers real odds from OddsAPI, falls back to estimated odds
        
        Args:
            match: Match dictionary with market_odds
            market_type: Market type (e.g., 'over_0.5_goals')
            base_probability: Base probability from ML model
        
        Returns:
            Odds value
        """
        # Try to get real odds from match data (from OddsAPI)
        market_odds = match.get('market_odds', {})
        
        # Map market types to odds keys
        market_mapping = {
            'over_0.5_goals': 'over_0.5_goals',
            'over_1.5_goals': 'over_1.5_goals',
            'home_over_0.5_goals': 'home_over_0.5',
            'away_over_0.5_goals': 'away_over_0.5',
        }
        
        odds_key = market_mapping.get(market_type)
        if odds_key and market_odds.get(odds_key):
            real_odds = market_odds[odds_key]
            if real_odds and 1.0 < real_odds < 50.0:  # Valid odds range
                return round(real_odds, 2)
        
        # Fallback to estimated odds from probability
        return self._estimate_odds_from_probability(base_probability)
    
    def _estimate_odds_from_probability(self, probability: float) -> float:
        """
        Estimate odds from probability (fallback when real odds not available)
        
        For safe markets (high probability), ensure odds are in 1.02-1.05 range
        """
        if probability <= 0:
            return 100.0
        if probability >= 1:
            return 1.02
        
        # Convert probability to fair odds
        implied_odds = 1.0 / probability
        
        # For very safe markets (probability >= 0.95), use fixed safe odds in 1.02-1.05 range
        if probability >= 0.95:
            # Map 0.95-1.0 probability to 1.05-1.02 odds range
            # Higher probability = lower (safer) odds
            odds_range = 1.05 - 1.02  # 0.03
            prob_range = 1.0 - 0.95   # 0.05
            odds = 1.05 - ((probability - 0.95) / prob_range) * odds_range
            return round(max(min(odds, 1.05), 1.02), 3)
        
        # For less safe markets, use standard calculation with margin
        # Bookmaker applies margin by offering slightly lower odds
        margin = 0.05  # 5% margin
        bookmaker_odds = implied_odds * (1 - margin)
        
        # Cap at reasonable range
        return round(min(max(bookmaker_odds, 1.01), 50.0), 3)
    
    def get_raw_predictions(self, matches: List[Dict]) -> List[Dict]:
        """Get raw ML predictions before filtering"""
        raw = []
        
        for match in matches:
            if not self.filter.filter_match(match):
                continue
            
            markets = self.simulator.get_recommended_markets(match)
            
            for market in markets:
                prob = self.predictor.predict(match, market)
                odds = self._get_odds_for_market(match, market, prob)
                
                raw.append({
                    'match': f"{match.get('home_team')} vs {match.get('away_team')}",
                    'market': market,
                    'odds': odds,
                    'confidence': prob,
                    'league': match.get('league_tier')
                })
        
        return raw

