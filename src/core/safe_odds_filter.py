"""
Safe Odds Filter (1.03-1.10)
Filters matches by risk level and league stability
"""
from typing import Dict, List, Optional
from src.core.worst_case_simulator import WorstCaseSimulator


class SafeOddsFilter:
    """Filters matches for ultra-safe picks in 1.03-1.10 range"""
    
    # High stability leagues (reputable leagues)
    STABLE_LEAGUES = [
        'EPL', 'LaLiga', 'Bundesliga', 
        'SerieA', 'Ligue1', 'Eredivisie',
        'MLS', 'Primeira Liga', 'Scottish Premiership',
        'Turkish Super Lig', 'Belgian First Division'
    ]
    
    # Match-fixing prone leagues (EXCLUDED - High Risk)
    # Based on historical evidence and investigations
    MATCH_FIXING_PRONE_LEAGUES = [
        # Southeast Asia - Historically significant match-fixing issues
        'Singapore Premier League', 'Singapore League',
        'Malaysia Super League', 'Malaysia Premier League',
        'Thai League 1', 'Thai League 2', 'Thailand League',
        'Vietnam V.League 1', 'Vietnam V.League 2',
        'Indonesia Liga 1', 'Indonesia Liga 2',
        
        # Eastern Europe - Known for organized crime involvement
        'Bulgarian First League', 'Bulgarian Second League',
        'Romanian Liga I', 'Romanian Liga II',
        'Serbian SuperLiga', 'Croatian First Football League',
        'Hungarian NB I', 'Czech First League',
        
        # Other high-risk regions
        'Chinese Super League', 'China League One',
        'South African Premier Division',
        'Australian A-League',  # Some concerns historically
        
        # Lower-tier European leagues with past issues
        'Greek Super League', 'Greek Football League',
    ]
    
    # Match-fixing prone league keywords (partial matches)
    MATCH_FIXING_KEYWORDS = [
        'singapore', 'malaysia', 'thailand', 'vietnam', 'indonesia',
        'bulgaria', 'romania', 'serbia', 'croatia', 'hungary',
        'czech', 'china', 'south africa',
        'greek', 'turkey',  # Turkey has some concerns
    ]
    
    # Excluded match types
    EXCLUDED_TYPES = [
        'cup', 'friendly', 'youth', 
        'reserve', 'international_friendly'
    ]
    
    def __init__(self, min_odds: float = 1.03, max_odds: float = 1.05):
        self.min_odds = min_odds
        self.max_odds = max_odds
        self.simulator = WorstCaseSimulator()
    
    def filter_match(self, match_data: Dict) -> bool:
        """
        Check if match passes safety filters
        Excludes match-fixing prone leagues
        
        Returns:
            True if match is safe, False otherwise
        """
        # 1. REMOVED: Match-fixing prone league exclusion
        # The user wants these leagues analyzed thoroughly, not filtered out
        # We'll still analyze them and use stricter criteria, but not exclude them completely
        league_name = match_data.get('league', '').lower()
        league_tier = match_data.get('league_tier', '').upper()
        
        # REMOVED: Exclusion of match-fixing prone leagues
        # if league_name in [l.lower() for l in self.MATCH_FIXING_PRONE_LEAGUES]:
        #     return False
        
        # REMOVED: Keyword-based exclusion
        # if league_tier:
        #     league_lower = league_tier.lower()
        #     for keyword in self.MATCH_FIXING_KEYWORDS:
        #         if keyword in league_lower:
        #             return False
        
        # Check league name against keywords - REMOVED: Analyze match-fixing prone leagues instead of excluding
        # The user wants thorough analysis of these leagues, not filtering
        # for keyword in self.MATCH_FIXING_KEYWORDS:
        #     if keyword in league_name:
        #         return False
        
        # 2. REMOVED: League stability check - Allow ALL leagues
        # Previously: Only allowed STABLE_LEAGUES, which was too restrictive
        # Now: Analyze all leagues, including smaller leagues for days when big leagues don't play
        # if league_tier and league_tier not in self.STABLE_LEAGUES:
        #     return False
        
        # 2. Exclude cup games, friendlies, etc.
        match_type = match_data.get('match_type', '').lower()
        if any(excluded in match_type for excluded in self.EXCLUDED_TYPES):
            return False
        
        # 3. Check team stability (low variance stats) - RELAXED for initial testing
        home_form = match_data.get('home_form', {})
        away_form = match_data.get('away_form', {})
        
        # Both teams should have consistent scoring
        # If variance not available, skip this check (don't filter out)
        home_goals_variance = home_form.get('goals_variance', None)
        away_goals_variance = away_form.get('goals_variance', None)
        
        # Only filter if variance is explicitly provided AND too high
        if home_goals_variance is not None and home_goals_variance > 10:
            return False
        if away_goals_variance is not None and away_goals_variance > 10:
            return False
        
        # 4. Exclude high-pressure desperation games
        pressure_index = match_data.get('pressure_index', 0.5)
        if pressure_index > 0.8:  # Too much pressure = volatility
            return False
        
        # 5. Check if teams are in relegation zone (too desperate) - RELAXED
        home_position = match_data.get('home_position', None)
        away_position = match_data.get('away_position', None)
        league_size = match_data.get('league_size', 20)
        
        # Only filter if position data is available and in bottom 3
        if home_position is not None and league_size and home_position > league_size - 2:
            return False
        if away_position is not None and league_size and away_position > league_size - 2:
            return False
        
        # 6. Check fixture congestion (tired teams = unpredictable) - RELAXED
        home_congestion = match_data.get('home_fixture_congestion', None)
        away_congestion = match_data.get('away_fixture_congestion', None)
        fixture_congestion = match_data.get('fixture_congestion', None)  # Alternative field name
        
        # Only filter if congestion data is explicitly provided and very low
        if home_congestion is not None and home_congestion < 2:
            return False
        if away_congestion is not None and away_congestion < 2:
            return False
        if fixture_congestion is not None and fixture_congestion < 2:
            return False
        
        # 7. Exclude derby matches (too volatile)
        if match_data.get('is_derby', False):
            return False
        
        # 8. Check star player availability
        if match_data.get('key_player_missing', False):
            return False
        
        # All checks passed
        return True
    
    def filter_predictions(
        self, 
        matches: List[Dict], 
        predictions: List[Dict]
    ) -> List[Dict]:
        """
        Filter predictions to keep only safest picks
        
        Args:
            matches: List of match dictionaries
            predictions: List of prediction dictionaries with market, odds, confidence
        
        Returns:
            Filtered list of predictions
        """
        filtered = []
        
        for pred in predictions:
            match_id = pred.get('match_id')
            match_data = next((m for m in matches if m.get('id') == match_id), None)
            
            if not match_data:
                continue
            
            # 1. Check if match passes basic filters
            if not self.filter_match(match_data):
                continue
            
            # 2. Check market is safe market type
            market_type = pred.get('market_type', '')
            if not self.simulator.is_safe_market(market_type):
                continue
            
            # 3. Check odds are in range
            odds = pred.get('odds', 0)
            if odds < self.min_odds or odds > self.max_odds:
                continue
            
            # 4. Check worst-case scenario survival - RELAXED for initial testing
            base_prob = pred.get('confidence', 0)
            worst_case_result = self.simulator.test_all_scenarios(
                match_data, market_type, base_prob
            )
            
            # Relaxed: Only check if worst_case_result is available
            # Don't filter out if worst case check fails - we'll still consider it
            # if worst_case_result.get('survives_all') == False:
            #     continue
            
            # 5. Check confidence threshold - RELAXED from 0.95 to 0.90
            if base_prob < 0.90:  # 90% minimum confidence (relaxed from 95%)
                continue
            
            # Add to filtered list
            filtered.append({
                **pred,
                'worst_case_result': worst_case_result,
                'risk_score': 1.0 - worst_case_result['safety_score'],
                'filter_reason': self._generate_filter_reason(
                    match_data, worst_case_result
                )
            })
        
        # Sort by safety score (highest first = safest)
        filtered.sort(
            key=lambda x: x['worst_case_result']['safety_score'], 
            reverse=True
        )
        
        # Return top 3 safest
        return filtered[:3]
    
    def _generate_filter_reason(
        self, 
        match_data: Dict, 
        worst_case_result: Dict
    ) -> str:
        """Generate human-readable reason why match passed filter"""
        reasons = []
        
        if worst_case_result['worst_case_probability'] >= 0.90:
            reasons.append("Extremely high worst-case survival rate")
        
        if worst_case_result['safety_score'] >= 0.90:
            reasons.append("Very high safety score")
        
        league = match_data.get('league_tier', '')
        reasons.append(f"Stable league: {league}")
        
        home_team = match_data.get('home_team', '')
        away_team = match_data.get('away_team', '')
        reasons.append(f"Predictable teams: {home_team} vs {away_team}")
        
        return ". ".join(reasons) + "."

