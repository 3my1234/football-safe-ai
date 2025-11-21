"""
Worst-case scenario simulator for football matches
Tests predictions against dangerous scenarios
"""
from typing import Dict, List, Tuple
import random


class WorstCaseSimulator:
    """Simulates worst-case scenarios for match predictions"""
    
    DANGEROUS_SCENARIOS = [
        "early_red_card",
        "key_player_injury",
        "defensive_errors",
        "opponent_parking_bus",
        "bad_weather",
        "var_frustration",
        "fixture_congestion",
        "low_motivation",
    ]
    
    SAFE_MARKETS = [
        "over_0.5_goals",
        "home_over_0.5_goals",
        "away_over_0.5_goals",
        "over_6.5_corners",
        "under_5.5_goals",
        "double_chance_1x",  # Home or Draw
        "double_chance_x2",  # Draw or Away
        "home_to_score",
        "away_to_score",
    ]
    
    def simulate_scenario(
        self, 
        match_data: Dict, 
        market_type: str, 
        base_probability: float,
        scenario: str
    ) -> Tuple[float, bool]:
        """
        Simulate a worst-case scenario and check if market survives
        
        Returns:
            (adjusted_probability, survives)
        """
        adjusted_prob = base_probability
        
        if scenario == "early_red_card":
            # Red card reduces scoring probability by ~20%
            adjusted_prob *= 0.8
            # But safe markets like "over_0.5" still survive
            if market_type in ["over_0.5_goals", "home_over_0.5_goals", "away_over_0.5_goals"]:
                adjusted_prob *= 1.1  # Still likely to see at least 0.5 goals
            
        elif scenario == "key_player_injury":
            # Missing star player reduces attack by ~15%
            adjusted_prob *= 0.85
            
        elif scenario == "defensive_errors":
            # Defensive errors actually HELP safe markets (more goals)
            if "over" in market_type.lower():
                adjusted_prob *= 1.05
            else:
                adjusted_prob *= 0.9
                
        elif scenario == "opponent_parking_bus":
            # Very defensive play reduces goals
            if "over" in market_type.lower():
                adjusted_prob *= 0.7
                # But "over_0.5" still has high chance
                if market_type == "over_0.5_goals":
                    adjusted_prob = max(adjusted_prob, 0.75)
            else:
                adjusted_prob *= 1.1  # Under markets benefit
                
        elif scenario == "bad_weather":
            # Weather can reduce goals
            adjusted_prob *= 0.85
            if market_type == "over_0.5_goals":
                adjusted_prob = max(adjusted_prob, 0.70)  # Still likely
                
        elif scenario == "var_frustration":
            # VAR doesn't affect goal count much, just delays
            adjusted_prob *= 0.95
            
        elif scenario == "fixture_congestion":
            # Tired teams = fewer goals
            congestion_days = match_data.get('fixture_congestion', 7)
            if congestion_days < 3:
                adjusted_prob *= 0.85  # Very tired
            else:
                adjusted_prob *= 0.95  # Normal rest
                
        elif scenario == "low_motivation":
            # Mid-table teams with nothing to play for
            pressure = match_data.get('pressure_index', 0.5)
            if pressure < 0.3:
                adjusted_prob *= 0.8  # Low motivation
            else:
                adjusted_prob *= 1.0  # Normal motivation
        
        # Market survives if probability still > 0.60 (60% confidence)
        survives = adjusted_prob >= 0.60
        
        return adjusted_prob, survives
    
    def test_all_scenarios(
        self, 
        match_data: Dict, 
        market_type: str, 
        base_probability: float
    ) -> Dict:
        """
        Test market against all worst-case scenarios
        
        Returns:
            {
                'worst_case_probability': float,
                'survives_all': bool,
                'failed_scenarios': List[str],
                'safety_score': float  # 0-1, higher = safer
            }
        """
        results = {}
        worst_prob = base_probability
        failed_scenarios = []
        
        for scenario in self.DANGEROUS_SCENARIOS:
            adj_prob, survives = self.simulate_scenario(
                match_data, market_type, base_probability, scenario
            )
            
            results[scenario] = {
                'adjusted_probability': adj_prob,
                'survives': survives
            }
            
            if adj_prob < worst_prob:
                worst_prob = adj_prob
            
            if not survives:
                failed_scenarios.append(scenario)
        
        # Calculate safety score (higher = safer)
        survival_rate = 1.0 - (len(failed_scenarios) / len(self.DANGEROUS_SCENARIOS))
        worst_case_safe = worst_prob >= 0.60
        safety_score = (worst_prob * 0.5) + (survival_rate * 0.5)
        
        return {
            'worst_case_probability': worst_prob,
            'survives_all': worst_case_safe,
            'failed_scenarios': failed_scenarios,
            'safety_score': safety_score,
            'scenario_results': results,
        }
    
    def is_safe_market(self, market_type: str) -> bool:
        """Check if market type is in safe markets list"""
        return market_type in self.SAFE_MARKETS
    
    def get_recommended_markets(self, match_data: Dict) -> List[str]:
        """
        Get recommended safe markets for a match
        Prioritizes markets that survive worst-case scenarios
        """
        recommended = []
        
        # Always include ultra-safe markets
        if match_data.get('home_xg', 0) > 0.8:
            recommended.append("home_over_0.5_goals")
        
        if match_data.get('away_xg', 0) > 0.8:
            recommended.append("away_over_0.5_goals")
        
        # Over 0.5 goals is almost always safe
        recommended.append("over_0.5_goals")
        
        # Corners if teams are attacking
        home_sot = match_data.get('home_form', {}).get('shots_on_target_avg', 4)
        away_sot = match_data.get('away_form', {}).get('shots_on_target_avg', 4)
        if home_sot + away_sot > 8:
            recommended.append("over_6.5_corners")
        
        return list(set(recommended))  # Remove duplicates

