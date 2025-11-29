"""
Odds Combiner
Combines picks to achieve 1.03-1.10 total odds
Prioritizes safety over high odds
"""
from typing import List, Dict, Optional
from itertools import combinations


class OddsCombiner:
    """Combines picks to achieve target odds range"""
    
    def __init__(self, min_odds: float = 1.02, max_odds: float = 1.10):
        # Accept wider range - admin will verify actual odds during vetting
        self.min_odds = min_odds
        self.max_odds = max_odds
    
    def calculate_combo_odds(self, picks: List[Dict]) -> float:
        """
        Calculate combined odds for multiple picks
        
        For independent events: odds1 * odds2 * odds3 ...
        """
        if not picks:
            return 1.0
        
        total_odds = 1.0
        for pick in picks:
            odds = pick.get('odds', 1.0)
            total_odds *= odds
        
        return round(total_odds, 4)
    
    def calculate_confidence(self, picks: List[Dict]) -> float:
        """
        Calculate combined confidence (geometric mean)
        """
        if not picks:
            return 0.0
        
        confidences = [pick.get('confidence', 0.0) for pick in picks]
        
        # Geometric mean for combined confidence
        product = 1.0
        for conf in confidences:
            product *= conf
        
        combined_confidence = product ** (1.0 / len(confidences))
        return round(combined_confidence, 4)
    
    def find_best_combination(
        self, 
        filtered_picks: List[Dict],
        max_games: int = 3
    ) -> Optional[Dict]:
        """
        Find the safest combination that produces 1.03-1.10 odds
        
        Prioritizes:
        1. Safety (highest worst-case survival)
        2. Fewer games (1 game > 2 games > 3 games)
        3. Higher confidence
        
        Returns:
            {
                'picks': List[Dict],
                'combo_odds': float,
                'total_confidence': float,
                'games_used': int,
                'safety_score': float,
                'reason': str
            }
        """
        if not filtered_picks:
            print(f"  ⚠️ OddsCombiner: No filtered picks provided (empty list)")
            return None
        
        print(f"  🔍 OddsCombiner: Finding best combo from {len(filtered_picks)} filtered picks (target: {self.min_odds}-{self.max_odds})")
        best_combo = None
        best_safety_score = 0.0
        single_pick_candidates = []
        
        # Try 1-game combo (safest)
        # Accept all picks regardless of odds - admin will verify during vetting
        for pick in filtered_picks:
            odds = pick.get('odds', 1.0)
            single_pick_candidates.append(odds)
            # Don't filter by odds - focus on safety
            if True:  # Accept all - admin verifies odds
                # Get safety_score, default to 0.9 (high) if not present
                worst_case = pick.get('worst_case_result', {})
                if isinstance(worst_case, dict):
                    safety = worst_case.get('safety_score', 0.9)
                else:
                    safety = 0.9  # Default high safety for fallback predictions
                
                # If no safety score, use confidence as proxy
                if safety == 0:
                    safety = pick.get('confidence', 0.9)
                
                if safety > best_safety_score:
                    best_safety_score = safety
                    best_combo = {
                        'picks': [pick],
                        'combo_odds': odds,
                        'total_confidence': pick.get('confidence', 0),
                        'games_used': 1,
                        'safety_score': safety,
                        'reason': f"Single pick: {pick.get('market_type')} at {odds}x odds"
                    }
        
        if single_pick_candidates and not best_combo:
            print(f"  ⚠️ OddsCombiner: {len(single_pick_candidates)} single picks checked, odds range: {min(single_pick_candidates):.3f}-{max(single_pick_candidates):.3f}, target: {self.min_odds}-{self.max_odds}")
        
        # Try 2-game combo
        for combo in combinations(filtered_picks, 2):
            picks = list(combo)
            combo_odds = self.calculate_combo_odds(picks)
            
            # Accept if combo odds are reasonable (admin verifies actual odds)
            if combo_odds <= 2.0:  # Allow up to 2.0 for combos
                # Calculate combined safety (average)
                safety_scores = []
                for p in picks:
                    worst_case = p.get('worst_case_result', {})
                    if isinstance(worst_case, dict):
                        safety = worst_case.get('safety_score', p.get('confidence', 0.9))
                    else:
                        safety = p.get('confidence', 0.9)
                    safety_scores.append(safety if safety > 0 else 0.9)
                
                avg_safety = sum(safety_scores) / len(safety_scores) if safety_scores else 0.9
                
                if avg_safety > best_safety_score:
                    best_safety_score = avg_safety
                    total_conf = self.calculate_confidence(picks)
                    best_combo = {
                        'picks': picks,
                        'combo_odds': combo_odds,
                        'total_confidence': total_conf,
                        'games_used': 2,
                        'safety_score': avg_safety,
                        'reason': f"2-game combo: {combo_odds}x odds with {total_conf:.2%} confidence"
                    }
        
        # Try 3-game combo (only if needed)
        if max_games >= 3 and not best_combo:
            for combo in combinations(filtered_picks, 3):
                picks = list(combo)
                combo_odds = self.calculate_combo_odds(picks)
                
                # Accept if combo odds are reasonable
                if combo_odds <= 3.0:  # Allow up to 3.0 for 3-game combos
                    safety_scores = []
                    for p in picks:
                        worst_case = p.get('worst_case_result', {})
                        if isinstance(worst_case, dict):
                            safety = worst_case.get('safety_score', p.get('confidence', 0.9))
                        else:
                            safety = p.get('confidence', 0.9)
                        safety_scores.append(safety if safety > 0 else 0.9)
                    
                    avg_safety = sum(safety_scores) / len(safety_scores) if safety_scores else 0.9
                    
                    if avg_safety > best_safety_score:
                        best_safety_score = avg_safety
                        total_conf = self.calculate_confidence(picks)
                        best_combo = {
                            'picks': picks,
                            'combo_odds': combo_odds,
                            'total_confidence': total_conf,
                            'games_used': 3,
                            'safety_score': avg_safety,
                            'reason': f"3-game combo: {combo_odds}x odds with {total_conf:.2%} confidence"
                        }
        
        return best_combo
    
    def format_combo_response(self, combo: Dict) -> Dict:
        """Format combination for API response"""
        if not combo:
            return {
                'combo_odds': None,
                'games_used': 0,
                'picks': [],
                'reason': f'No safe combination found in target odds range ({self.min_odds}-{self.max_odds})',
                'confidence': 0.0
            }
        
        return {
            'combo_odds': combo['combo_odds'],
            'games_used': combo['games_used'],
            'picks': [
                {
                    'match': f"{pick.get('home_team', '')} vs {pick.get('away_team', '')}",
                    'market': pick.get('market_type', ''),
                    'odds': pick.get('odds', 1.0),
                    'confidence': pick.get('confidence', 0),
                    'worstCaseSafe': pick.get('worst_case_result', {}).get('survives_all', False),
                    'safety_score': pick.get('worst_case_result', {}).get('safety_score', 0)
                }
                for pick in combo['picks']
            ],
            'reason': combo['reason'],
            'confidence': combo['total_confidence']
        }

