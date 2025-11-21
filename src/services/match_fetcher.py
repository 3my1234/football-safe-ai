"""
Match Fetcher
Fetches today's matches from API-Football
"""
from typing import List, Dict
import requests
import os
from datetime import datetime, timedelta
from typing import Optional


class MatchFetcher:
    """Fetches matches from API-Football"""
    
    def __init__(self):
        self.api_key = os.getenv("API_FOOTBALL_KEY", "")
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
    
    def get_today_matches(self, leagues: Optional[List[int]] = None) -> List[Dict]:
        """
        Fetch today's matches from API-Football
        
        Args:
            leagues: List of league IDs (e.g., [39 for EPL, 140 for LaLiga])
        
        Returns:
            List of match dictionaries
        """
        if not self.api_key:
            # Return sample data for testing
            return self._get_sample_matches()
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Default to top leagues if not specified
        if not leagues:
            leagues = [39, 140, 78, 135, 61, 88]  # EPL, LaLiga, Bundesliga, SerieA, Ligue1, Eredivisie
        
        all_matches = []
        
        for league_id in leagues:
            try:
                url = f"{self.base_url}/fixtures"
                params = {
                    "date": today,
                    "league": league_id,
                    "season": datetime.now().year
                }
                
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    fixtures = data.get("response", [])
                    
                    for fixture in fixtures:
                        match = self._parse_fixture(fixture)
                        if match:
                            all_matches.append(match)
                
            except Exception as e:
                print(f"Error fetching league {league_id}: {e}")
                continue
        
        return all_matches
    
    def _parse_fixture(self, fixture: Dict) -> Optional[Dict]:
        """Parse API-Football fixture to internal format"""
        try:
            teams = fixture.get("teams", {})
            home = teams.get("home", {})
            away = teams.get("away", {})
            league = fixture.get("league", {})
            fixture_data = fixture.get("fixture", {})
            
            # Get odds if available
            odds_data = fixture.get("odds", [])
            bookmaker_odds = {}
            
            if odds_data:
                for bookmaker in odds_data:
                    if bookmaker.get("bookmaker", {}).get("name") == "Bet365":
                        outcomes = bookmaker.get("bets", [])
                        for outcome in outcomes:
                            if outcome.get("name") == "Match Winner":
                                values = outcome.get("values", [])
                                for val in values:
                                    if val.get("value") == "Home":
                                        bookmaker_odds['home'] = float(val.get("odd", 2.0))
                                    elif val.get("value") == "Draw":
                                        bookmaker_odds['draw'] = float(val.get("odd", 3.0))
                                    elif val.get("value") == "Away":
                                        bookmaker_odds['away'] = float(val.get("odd", 2.5))
            
            match = {
                'id': str(fixture_data.get("id")),
                'home_team': home.get("name", ""),
                'away_team': away.get("name", ""),
                'league': league.get("name", ""),
                'league_tier': self._map_league_tier(league.get("id")),
                'match_date': datetime.fromisoformat(fixture_data.get("date", "")),
                'home_odds': bookmaker_odds.get('home', 2.0),
                'draw_odds': bookmaker_odds.get('draw', 3.0),
                'away_odds': bookmaker_odds.get('away', 2.5),
                
                # Default stats (in production, fetch detailed stats)
                'home_form': {
                    'goals_scored_5': 10,
                    'goals_conceded_5': 4,
                    'form_percentage': 0.7,
                    'shots_on_target_avg': 5.0
                },
                'away_form': {
                    'goals_scored_5': 8,
                    'goals_conceded_5': 5,
                    'form_percentage': 0.65,
                    'shots_on_target_avg': 4.5
                },
                'home_xg': 1.8,
                'away_xg': 1.5,
                'home_position': 8,
                'away_position': 12,
                'table_gap': 4,
                'pressure_index': 0.5,
                'is_derby': False,
                'is_must_win': False,
                'fixture_congestion': 7
            }
            
            return match
            
        except Exception as e:
            print(f"Error parsing fixture: {e}")
            return None
    
    def _map_league_tier(self, league_id: int) -> str:
        """Map API-Football league ID to league tier"""
        mapping = {
            39: "EPL",
            140: "LaLiga",
            78: "Bundesliga",
            135: "SerieA",
            61: "Ligue1",
            88: "Eredivisie"
        }
        return mapping.get(league_id, "other")
    
    def _get_sample_matches(self) -> List[Dict]:
        """Return sample matches for testing when API key not available"""
        from datetime import datetime, timedelta
        
        return [
            {
                'id': '1',
                'home_team': 'Arsenal',
                'away_team': 'Sheffield United',
                'league': 'Premier League',
                'league_tier': 'EPL',
                'match_date': datetime.now(),
                'home_odds': 1.20,
                'draw_odds': 6.00,
                'away_odds': 12.00,
                'home_form': {
                    'goals_scored_5': 12,
                    'goals_conceded_5': 3,
                    'form_percentage': 0.85,
                    'shots_on_target_avg': 6.0
                },
                'away_form': {
                    'goals_scored_5': 4,
                    'goals_conceded_5': 8,
                    'form_percentage': 0.3,
                    'shots_on_target_avg': 3.0
                },
                'home_xg': 2.1,
                'away_xg': 0.8,
                'home_position': 3,
                'away_position': 20,
                'table_gap': 17,
                'pressure_index': 0.6,
                'is_derby': False,
                'is_must_win': False,
                'fixture_congestion': 7
            },
            {
                'id': '2',
                'home_team': 'Manchester City',
                'away_team': 'Brighton',
                'league': 'Premier League',
                'league_tier': 'EPL',
                'match_date': datetime.now(),
                'home_odds': 1.35,
                'draw_odds': 5.00,
                'away_odds': 8.00,
                'home_form': {
                    'goals_scored_5': 15,
                    'goals_conceded_5': 2,
                    'form_percentage': 0.9,
                    'shots_on_target_avg': 7.0
                },
                'away_form': {
                    'goals_scored_5': 10,
                    'goals_conceded_5': 7,
                    'form_percentage': 0.6,
                    'shots_on_target_avg': 5.0
                },
                'home_xg': 2.5,
                'away_xg': 1.3,
                'home_position': 1,
                'away_position': 8,
                'table_gap': 7,
                'pressure_index': 0.4,
                'is_derby': False,
                'is_must_win': False,
                'fixture_congestion': 7
            }
        ]

