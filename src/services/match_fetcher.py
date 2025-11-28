"""
Match Fetcher
Fetches today's matches from API-Football and odds from OddsAPI
"""
from typing import List, Dict
import requests
import os
from datetime import datetime, timedelta
from typing import Optional
# OddsAPI client (optional - fallback if not available)
try:
    from src.services.odds_api_client import OddsAPIClient
except ImportError:
    OddsAPIClient = None


class MatchFetcher:
    """Fetches matches from API-Football"""
    
    def __init__(self):
        self.api_key = os.getenv("API_FOOTBALL_KEY", "")
        self.base_url = "https://v3.football.api-sports.io"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "v3.football.api-sports.io"
        }
        # Initialize OddsAPI client (optional)
        self.odds_client = OddsAPIClient() if OddsAPIClient else None
        # Cache odds for today's matches
        self._odds_cache = {}
        self._odds_fetched = False
    
    def get_today_matches(self, leagues: Optional[List[int]] = None) -> List[Dict]:
        """
        Fetch today's matches from API-Football and enrich with real odds from OddsAPI
        
        Args:
            leagues: List of league IDs (e.g., [39 for EPL, 140 for LaLiga])
        
        Returns:
            List of match dictionaries with real odds
        """
        if not self.api_key:
            print("⚠️ API_FOOTBALL_KEY not set! Cannot fetch real matches.")
            print("   Please set API_FOOTBALL_KEY environment variable in Coolify")
            # Don't return sample matches - return empty so user knows there's a problem
            return []
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Determine current season - European leagues run Aug-May, so Nov 2024 = 2024-2025 season = season 2024
        # But also check: free plans only support 2021-2023, so we need to use 2023 for free plans
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # For European leagues: if month is Aug-Dec, season = current year; if Jan-Jul, season = previous year
        # But API free plan limitation: only 2021-2023 available
        # Use 2023 as the latest available season for free plans
        if current_month >= 8:  # Aug-Dec
            season_year = current_year
        else:  # Jan-Jul
            season_year = current_year - 1
        
        # Free plan limitation: only 2021-2023
        if season_year > 2023:
            season_year = 2023
            print(f"⚠️ Free plan detected: Using season 2023 (latest available for free plans)")
            print(f"   Current date: {today}, Would use season: {season_year}")
        
        print(f"🔍 Fetching matches for {today} from API-Football (season: {season_year})...")
        
        # Default to top leagues if not specified, PLUS more leagues for days when big leagues don't play
        if not leagues:
            # Top tier leagues
            leagues = [
                39,   # EPL (England)
                140,  # LaLiga (Spain)
                78,   # Bundesliga (Germany)
                135,  # SerieA (Italy)
                61,   # Ligue1 (France)
                88,   # Eredivisie (Netherlands)
                # Add more leagues to ensure matches available daily
                203,  # Super Lig (Turkey)
                235,  # Premier League (Russia)
                179,  # Liga MX (Mexico)
                262,  # MLS (USA)
                128,  # Primeira Liga (Portugal)
                71,   # Serie A (Brazil)
                40,   # Championship (England) - level 2
                41,   # League 1 (England) - level 3
                48,   # La Liga 2 (Spain)
                79,   # 2. Bundesliga (Germany)
                137,  # Serie B (Italy)
                63,   # Ligue 2 (France)
                # Smaller European leagues
                40,   # League Two (England)
                299,  # J1 League (Japan)
                307,  # K League 1 (South Korea)
                106,  # Brasileirão (Brazil)
                144,  # Jupiler Pro League (Belgium)
                89,   # Ekstraklasa (Poland)
                103,  # Superliga (Denmark)
                113,  # Eliteserien (Norway)
                119,  # Allsvenskan (Sweden)
                94,   # Super League (Greece)
                253,  # Mls Cup (if different)
                207,  # Serie A (Argentina)
            ]
        
        all_matches = []
        
        # Fetch matches from API-Football
        api_errors = []
        for league_id in leagues:
            try:
                url = f"{self.base_url}/fixtures"
                params = {
                    "date": today,
                    "league": league_id,
                    "season": season_year
                }
                
                print(f"  📡 Fetching league {league_id} (date: {today})...")
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check API response structure
                    if "errors" in data:
                        error_msgs = data.get("errors", [])
                        api_errors.append(f"League {league_id}: API errors - {error_msgs}")
                        print(f"  ⚠️ League {league_id}: API returned errors: {error_msgs}")
                        continue
                    
                    # Check if API rate limit info
                    api_rate_limit = data.get("results", 0)
                    if isinstance(data.get("response"), list):
                        fixtures = data.get("response", [])
                    else:
                        fixtures = []
                    
                    print(f"  ✅ League {league_id}: Found {len(fixtures)} fixtures (API results: {api_rate_limit})")
                    
                    for fixture in fixtures:
                        match = self._parse_fixture(fixture)
                        if match:
                            all_matches.append(match)
                        else:
                            print(f"    ⚠️ Failed to parse fixture: {fixture.get('fixture', {}).get('id')}")
                elif response.status_code == 403:
                    error_msg = f"League {league_id}: 403 Forbidden - API key might be invalid or expired"
                    api_errors.append(error_msg)
                    print(f"  ❌ {error_msg}")
                    print(f"    Response: {response.text[:200]}")
                elif response.status_code == 429:
                    error_msg = f"League {league_id}: 429 Too Many Requests - Rate limited"
                    api_errors.append(error_msg)
                    print(f"  ⚠️ {error_msg}")
                else:
                    error_msg = f"League {league_id}: HTTP {response.status_code}"
                    api_errors.append(f"{error_msg} - {response.text[:100]}")
                    print(f"  ⚠️ {error_msg} - {response.text[:200]}")
                
            except requests.exceptions.Timeout:
                error_msg = f"League {league_id}: Request timeout"
                api_errors.append(error_msg)
                print(f"  ❌ {error_msg}")
            except Exception as e:
                import traceback
                error_msg = f"League {league_id}: {str(e)}"
                api_errors.append(error_msg)
                print(f"  ❌ Error fetching league {league_id}: {e}")
                print(f"    Traceback: {traceback.format_exc()}")
                continue
        
        if api_errors:
            print(f"\n⚠️ API Errors encountered: {len(api_errors)} errors")
            for err in api_errors[:5]:  # Show first 5 errors
                print(f"  - {err}")
        
        print(f"📊 Total matches fetched: {len(all_matches)}")
        if len(all_matches) == 0 and api_errors:
            print(f"⚠️ No matches found. Check API errors above. Possible issues:")
            print(f"   - API rate limit exceeded")
            print(f"   - Invalid API key")
            print(f"   - No matches scheduled for {today}")
            print(f"   - Wrong date format or timezone")
        
        # If no matches found, log the issue
        if not all_matches:
            print("⚠️ No matches found from API-Football!")
            print("   Possible reasons:")
            print("   1. API_FOOTBALL_KEY not set or invalid")
            print("   2. No matches scheduled today")
            print("   3. API rate limit exceeded")
            print("   4. League IDs not valid")
            # Don't return sample matches - return empty so it's clear there's an issue
        
        # Enrich with real odds from OddsAPI
        if all_matches and not self._odds_fetched:
            self._fetch_odds_for_matches(all_matches)
            self._odds_fetched = True
        
        # Merge odds into matches
        for match in all_matches:
            home_team = match.get('home_team', '')
            away_team = match.get('away_team', '')
            league_tier = match.get('league_tier', '')
            
            # Get cached odds for this match
            match_key = f"{home_team}_{away_team}"
            odds = self._odds_cache.get(match_key, {})
            
            # Update match with real odds (prefer OddsAPI, fallback to API-Football)
            if odds.get('home_odds'):
                match['home_odds'] = odds['home_odds']
            if odds.get('draw_odds'):
                match['draw_odds'] = odds['draw_odds']
            if odds.get('away_odds'):
                match['away_odds'] = odds['away_odds']
            
            # Add market-specific odds
            match['market_odds'] = {
                'over_0.5_goals': odds.get('over_0.5_goals'),
                'over_1.5_goals': odds.get('over_1.5_goals'),
                'home_over_0.5': odds.get('home_over_0.5'),
                'away_over_0.5': odds.get('away_over_0.5'),
            }
        
        return all_matches
    
    def _fetch_odds_for_matches(self, matches: List[Dict]):
        """Fetch odds from OddsAPI for all matches"""
        if not self.odds_client:
            print("⚠️ OddsAPI client not available. Using API-Football odds only.")
            return
        if not self.odds_client.api_key:
            print("⚠️ OddsAPI key not set. Using API-Football odds only.")
            return
        
        # Group matches by league tier
        matches_by_league = {}
        for match in matches:
            league_tier = match.get('league_tier', '')
            if league_tier not in matches_by_league:
                matches_by_league[league_tier] = []
            matches_by_league[league_tier].append(match)
        
        # Fetch odds for each league
        for league_tier, league_matches in matches_by_league.items():
            try:
                print(f"📊 Fetching odds from OddsAPI for {league_tier}...")
                odds_data = self.odds_client.get_odds_for_league(league_tier)
                
                if not odds_data:
                    print(f"⚠️ No odds data from OddsAPI for {league_tier}")
                    continue
                
                # Extract odds for each match
                for match in league_matches:
                    home_team = match.get('home_team', '')
                    away_team = match.get('away_team', '')
                    match_key = f"{home_team}_{away_team}"
                    
                    odds = self.odds_client.extract_odds_for_match(
                        odds_data, home_team, away_team
                    )
                    
                    if odds.get('home_odds') or odds.get('over_0.5_goals'):
                        self._odds_cache[match_key] = odds
                        print(f"✅ Found odds for {home_team} vs {away_team}")
                
            except Exception as e:
                print(f"⚠️ Error fetching odds for {league_tier}: {e}")
                continue
    
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
                    'goals_scored_5': 12,
                    'goals_conceded_5': 3,
                    'form_percentage': 0.85,
                    'shots_on_target_avg': 6.0,
                    'goals_variance': 5.0  # Low variance = predictable
                },
                'away_form': {
                    'goals_scored_5': 4,
                    'goals_conceded_5': 8,
                    'form_percentage': 0.3,
                    'shots_on_target_avg': 3.0,
                    'goals_variance': 6.0  # Low variance
                },
                'home_xg': 2.1,
                'away_xg': 0.8,
                'home_position': 3,
                'away_position': 20,
                'league_size': 20,
                'table_gap': 17,
                'pressure_index': 0.4,  # Low pressure
                'is_derby': False,
                'is_must_win': False,
                'key_player_missing': False,
                'fixture_congestion': 7,
                'home_fixture_congestion': 7,
                'away_fixture_congestion': 7
            }
            
            return match
            
        except Exception as e:
            print(f"Error parsing fixture: {e}")
            return None
    
    def _map_league_tier(self, league_id: int) -> str:
        """Map API-Football league ID to league tier"""
        mapping = {
            # Top tier
            39: "EPL",
            140: "LaLiga",
            78: "Bundesliga",
            135: "SerieA",
            61: "Ligue1",
            88: "Eredivisie",
            # More leagues
            203: "SuperLig",
            235: "PremierLeague_RU",
            179: "LigaMX",
            262: "MLS",
            128: "PrimeiraLiga",
            71: "SerieA_BR",
            299: "J1League",
            307: "KLeague1",
            106: "Brasileirao",
            144: "JupilerPro",
            89: "Ekstraklasa",
            103: "Superliga",
            113: "Eliteserien",
            119: "Allsvenskan",
            94: "SuperLeague",
            207: "SerieA_AR",
        }
        return mapping.get(league_id, f"league_{league_id}")  # Return league ID if not mapped, don't exclude
    
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
                    'shots_on_target_avg': 6.0,
                    'goals_variance': 5.0
                },
                'away_form': {
                    'goals_scored_5': 4,
                    'goals_conceded_5': 8,
                    'form_percentage': 0.3,
                    'shots_on_target_avg': 3.0,
                    'goals_variance': 6.0
                },
                'home_xg': 2.1,
                'away_xg': 0.8,
                'home_position': 3,
                'away_position': 20,
                'league_size': 20,
                'table_gap': 17,
                'pressure_index': 0.4,
                'is_derby': False,
                'is_must_win': False,
                'key_player_missing': False,
                'fixture_congestion': 7,
                'home_fixture_congestion': 7,
                'away_fixture_congestion': 7
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
                    'shots_on_target_avg': 7.0,
                    'goals_variance': 4.0
                },
                'away_form': {
                    'goals_scored_5': 10,
                    'goals_conceded_5': 7,
                    'form_percentage': 0.6,
                    'shots_on_target_avg': 5.0,
                    'goals_variance': 5.5
                },
                'home_xg': 2.5,
                'away_xg': 1.3,
                'home_position': 1,
                'away_position': 8,
                'league_size': 20,
                'table_gap': 7,
                'pressure_index': 0.4,
                'is_derby': False,
                'is_must_win': False,
                'key_player_missing': False,
                'fixture_congestion': 7,
                'home_fixture_congestion': 7,
                'away_fixture_congestion': 7
            }
        ]

