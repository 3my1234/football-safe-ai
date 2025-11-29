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
        Get recommended safe markets for a match based on AI reasoning
        Prioritizes markets that survive worst-case scenarios
        
        Returns markets like:
        - handicap_2_home: Home team with 2-goal handicap (very safe if home is strong)
        - handicap_2_away: Away team with 2-goal handicap (very safe if away is strong)
        - over_0.5_goals: At least 1 goal scored (ultra-safe)
        - over_1.5_goals: At least 2 goals scored (safe)
        - under_3.5_goals: Maximum 3 goals (safe for low-scoring matches)
        """
        recommended = []
        home_team = match_data.get('home_team', '')
        away_team = match_data.get('away_team', '')
        
        # Get team strength indicators
        home_xg = match_data.get('home_xg', 1.5)
        away_xg = match_data.get('away_xg', 1.5)
        home_odds = match_data.get('home_odds', 2.0)
        away_odds = match_data.get('away_odds', 2.0)
        home_form = match_data.get('home_form', {})
        away_form = match_data.get('away_form', {})
        
        # REASONING: Handicap markets (safest when one team is clearly stronger)
        # If home team is much stronger (lower odds = stronger), handicap favors home
        if home_odds < 1.5 and (home_odds < away_odds - 0.3):
            recommended.append("handicap_2_home")
            print(f"    💡 Reasoning: {home_team} is strong (odds {home_odds:.2f}), handicap_2_home is very safe")
        
        # If away team is much stronger
        if away_odds < 1.5 and (away_odds < home_odds - 0.3):
            recommended.append("handicap_2_away")
            print(f"    💡 Reasoning: {away_team} is strong (odds {away_odds:.2f}), handicap_2_away is very safe")
        
        # REASONING: Over goals markets (safe when teams score regularly)
        # Always include over 0.5 goals (ultra-safe - almost always happens)
        recommended.append("over_0.5_goals")
        
        # Over 1.5 goals if both teams have decent xG
        if home_xg > 1.0 and away_xg > 1.0:
            recommended.append("over_1.5_goals")
            print(f"    💡 Reasoning: Both teams score regularly (home_xg={home_xg:.1f}, away_xg={away_xg:.1f})")
        
        # Over 2.5 goals if high-scoring teams
        if home_xg + away_xg > 3.0:
            recommended.append("over_2.5_goals")
            print(f"    💡 Reasoning: High-scoring match expected (combined xG={home_xg + away_xg:.1f})")
        
        # REASONING: Under goals markets (safe for defensive/low-scoring matches)
        # Under 3.5 goals if low-scoring teams
        if home_xg + away_xg < 2.5:
            recommended.append("under_3.5_goals")
            print(f"    💡 Reasoning: Low-scoring match expected (combined xG={home_xg + away_xg:.1f})")
        
        # REASONING: Team-specific over goals (safe when team scores regularly)
        if home_xg > 1.0:
            recommended.append("home_over_0.5_goals")
            print(f"    💡 Reasoning: {home_team} scores regularly (xG={home_xg:.1f})")
        
        if away_xg > 1.0:
            recommended.append("away_over_0.5_goals")
            print(f"    💡 Reasoning: {away_team} scores regularly (xG={away_xg:.1f})")
        
        # REASONING: Corners (safe when attacking teams)
        home_sot = home_form.get('shots_on_target_avg', 4)
        away_sot = away_form.get('shots_on_target_avg', 4)
        if home_sot + away_sot > 8:
            recommended.append("over_6.5_corners")
            print(f"    💡 Reasoning: Both teams attack frequently (combined SOT={home_sot + away_sot:.1f})")
        
        return list(set(recommended))  # Remove duplicates

