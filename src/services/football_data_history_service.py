"""
Football-Data.org History Service
Fetches historical match data and calculates Form & H2H locally
Production-ready with caching, rate limiting, and error handling
"""
import requests
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from functools import lru_cache
import os

logger = logging.getLogger(__name__)


class FootballDataHistoryService:
    """
    Professional service for fetching and processing historical match data
    from Football-Data.org API.
    
    Features:
    - Rate limiting (respects API limits)
    - Caching (reduces API calls)
    - Error handling with fallbacks
    - Team name matching (fuzzy + manual mapping)
    - Local Form & H2H calculations
    """
    
    # API Configuration
    BASE_URL = "https://api.football-data.org/v4"
    API_KEY = "307cfe41e5cd4dcc8fbcf35a398f1625"  # Free tier
    RATE_LIMIT_REQUESTS = 10  # Free tier: 10 requests per minute
    RATE_LIMIT_WINDOW = 60  # 60 seconds
    
    # League mapping: Our league IDs -> Football-Data.org competition codes
    LEAGUE_MAPPING = {
        39: "PL",      # Premier League (England)
        140: "PD",     # Primera Division (Spain)
        78: "BL1",     # Bundesliga (Germany)
        135: "SA",     # Serie A (Italy)
        61: "FL1",     # Ligue 1 (France)
        88: "DED",     # Eredivisie (Netherlands)
        203: "TC",     # Super Lig (Turkey) - need to verify code
        235: "RPL",    # Premier League (Russia) - need to verify code
        179: "PDM",    # Liga MX (Mexico) - need to verify code
        262: "MLS",    # MLS (USA)
        128: "PPL",    # Primeira Liga (Portugal)
        71: "BSA",     # Serie A (Brazil)
        40: "ELC",     # Championship (England)
        41: "EL1",     # League 1 (England)
        48: "SD",      # Segunda Division (Spain)
        79: "BL2",     # 2. Bundesliga (Germany)
        137: "SB",     # Serie B (Italy)
        63: "FL2",     # Ligue 2 (France)
    }
    
    # League name to code mapping (fallback for when we only have league name)
    LEAGUE_NAME_MAPPING = {
        "premier league": "PL",
        "primera division": "PD",
        "la liga": "PD",
        "bundesliga": "BL1",
        "2. bundesliga": "BL2",
        "2 bundesliga": "BL2",
        "zweite bundesliga": "BL2",
        "serie a": "SA",
        "ligue 1": "FL1",
        "eredivisie": "DED",
        "championship": "ELC",
        "3. liga": "BL3",  # May not exist in Football-Data.org
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "X-Auth-Token": self.API_KEY,
            "Accept": "application/json"
        })
        
        # Rate limiting tracking
        self.request_times: List[float] = []
        
        # In-memory cache for API responses (production should use Redis)
        self._match_cache: Dict[str, List[Dict]] = {}
        self._team_cache: Dict[str, Dict] = {}
        self._cache_ttl = 3600  # 1 hour cache TTL
        
        logger.info("FootballDataHistoryService initialized")
    
    def _rate_limit(self):
        """Enforce rate limiting: 10 requests per minute"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < self.RATE_LIMIT_WINDOW]
        
        # If we've hit the limit, wait
        if len(self.request_times) >= self.RATE_LIMIT_REQUESTS:
            sleep_time = self.RATE_LIMIT_WINDOW - (now - self.request_times[0]) + 0.5
            if sleep_time > 0:
                logger.warning(f"Rate limit reached. Sleeping for {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
                # Clean up again after sleep
                self.request_times = [t for t in self.request_times if now - t < self.RATE_LIMIT_WINDOW]
        
        self.request_times.append(time.time())
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make API request with rate limiting and error handling
        """
        self._rate_limit()
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                logger.error(f"Forbidden (403): Check API key or rate limits. URL: {url}")
                return None
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded. Waiting...")
                time.sleep(60)  # Wait 1 minute
                return self._make_request(endpoint, params)  # Retry once
            else:
                logger.error(f"API error {response.status_code}: {response.text[:200]}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None
    
    def get_competition_code(self, league_id: Optional[int] = None, league_name: Optional[str] = None) -> Optional[str]:
        """
        Map league ID or name to Football-Data.org competition code
        """
        if league_id and league_id in self.LEAGUE_MAPPING:
            return self.LEAGUE_MAPPING[league_id]
        
        if league_name:
            league_lower = league_name.lower()
            for name, code in self.LEAGUE_NAME_MAPPING.items():
                if name in league_lower:
                    return code
        
        return None
    
    def fetch_finished_matches(
        self,
        competition_code: str,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Fetch finished matches for a competition
        
        Args:
            competition_code: Competition code (e.g., "PL", "BL1")
            date_from: Start date (YYYY-MM-DD format)
            date_to: End date (YYYY-MM-DD format)
            limit: Maximum number of matches to return
        
        Returns:
            List of match dictionaries with scores and team info
        """
        cache_key = f"{competition_code}_{date_from}_{date_to}"
        
        # Check cache
        if cache_key in self._match_cache:
            logger.debug(f"Cache hit for {cache_key}")
            return self._match_cache[cache_key]
        
        params = {"status": "FINISHED"}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        
        endpoint = f"/competitions/{competition_code}/matches"
        data = self._make_request(endpoint, params)
        
        if not data:
            logger.warning(f"Failed to fetch matches for {competition_code}")
            return []
        
        matches = data.get("matches", [])
        
        # Limit results
        if limit and len(matches) > limit:
            matches = matches[:limit]
        
        # Cache results
        self._match_cache[cache_key] = matches
        
        logger.info(f"Fetched {len(matches)} finished matches for {competition_code}")
        return matches
    
    def _match_team_name(self, team_name: str, team_list: List[Dict]) -> Optional[Dict]:
        """
        Match team name using fuzzy matching and manual rules
        """
        team_name_lower = team_name.lower().strip()
        
        # Try exact match first
        for team in team_list:
            if team_name_lower == team.get("name", "").lower():
                return team
        
        # Try partial match (team name contains or is contained)
        for team in team_list:
            team_api_name = team.get("name", "").lower()
            if team_name_lower in team_api_name or team_api_name in team_name_lower:
                return team
        
        # Try fuzzy matching (remove special characters, extra words)
        # Normalize team names: remove "FC", "SV", numbers, special chars for comparison
        def normalize_name(name: str) -> str:
            # Remove common prefixes/suffixes
            name = name.lower().replace("fc", "").replace("sv", "").replace("sg", "")
            # Remove extra whitespace and special chars except spaces
            name = "".join(c if c.isalnum() or c.isspace() else "" for c in name)
            return " ".join(name.split())  # Normalize spaces
        
        normalized_search = normalize_name(team_name_lower)
        for team in team_list:
            team_api_normalized = normalize_name(team.get("name", ""))
            if normalized_search in team_api_normalized or team_api_normalized in normalized_search:
                logger.info(f"Matched '{team_name}' to '{team.get('name')}' using normalized matching")
                return team
        
        # Manual mapping for common differences
        # Include German team name variations
        manual_mappings = {
            "tottenham": "tottenham hotspur",
            "spurs": "tottenham hotspur",
            "manchester united": "manchester united fc",
            "manchester city": "manchester city fc",
            "arsenal": "arsenal fc",
            "chelsea": "chelsea fc",
            "liverpool": "liverpool fc",
            # German teams (2. Bundesliga, 3. Liga)
            "preussen munster": "preußen münster",
            "preussen münster": "preußen münster",
            "preussen": "preußen münster",
            "arminia bielefeld": "arminia bielefeld",
            "dynamo dresden": "sg dynamo dresden",
            "fortuna dusseldorf": "fortuna düsseldorf",
            "fortuna düsseldorf": "fortuna düsseldorf",
            "sv darmstadt": "sv darmstadt 98",
            "darmstadt 98": "sv darmstadt 98",
            "elversberg": "sv elversberg",
            "sv elversberg": "sv elversberg",
        }
        
        for key, value in manual_mappings.items():
            if key in team_name_lower:
                for team in team_list:
                    if value in team.get("name", "").lower():
                        return team
        
        logger.warning(f"Could not match team name: {team_name}")
        return None
    
    def get_team_id_from_matches(self, team_name: str, competition_code: str) -> Optional[int]:
        """
        Get team ID by fetching matches and matching team name
        """
        cache_key = f"team_id_{team_name}_{competition_code}"
        if cache_key in self._team_cache:
            return self._team_cache[cache_key].get("id")
        
        # Fetch recent matches to find team
        matches = self.fetch_finished_matches(competition_code, limit=50)
        
        for match in matches:
            home_team = match.get("homeTeam", {})
            away_team = match.get("awayTeam", {})
            
            if self._match_team_name(team_name, [home_team]):
                self._team_cache[cache_key] = home_team
                return home_team.get("id")
            if self._match_team_name(team_name, [away_team]):
                self._team_cache[cache_key] = away_team
                return away_team.get("id")
        
        return None
    
    def calculate_team_form(
        self,
        team_name: str,
        competition_code: str,
        before_date: datetime,
        matches_needed: int = 5
    ) -> Dict:
        """
        Calculate team form from last N finished matches
        
        Returns:
            {
                'goals_scored_5': int,
                'goals_conceded_5': int,
                'wins': int,
                'draws': int,
                'losses': int,
                'form_percentage': float,
                'form_string': str,  # e.g., "WWLDD"
                'points_5': int,
                'clean_sheets': int
            }
        """
        # Fetch matches up to before_date
        date_to = before_date.strftime("%Y-%m-%d")
        date_from = (before_date - timedelta(days=90)).strftime("%Y-%m-%d")
        
        all_matches = self.fetch_finished_matches(
            competition_code,
            date_from=date_from,
            date_to=date_to,
            limit=200  # Fetch more to ensure we have enough team matches
        )
        
        # Filter matches for this team and sort by date (newest first)
        team_matches = []
        team_id = self.get_team_id_from_matches(team_name, competition_code)
        
        for match in all_matches:
            match_date_str = match.get("utcDate", "")
            if not match_date_str:
                continue
            
            try:
                match_date = datetime.fromisoformat(match_date_str.replace("Z", "+00:00"))
                if match_date >= before_date:
                    continue  # Skip future matches
            except:
                continue
            
            home_team = match.get("homeTeam", {})
            away_team = match.get("awayTeam", {})
            
            # Check if team is in this match
            is_home = self._match_team_name(team_name, [home_team])
            is_away = self._match_team_name(team_name, [away_team])
            
            if is_home or is_away:
                score = match.get("score", {}).get("fullTime", {})
                home_score = score.get("home")
                away_score = score.get("away")
                
                if home_score is None or away_score is None:
                    continue  # Skip matches without scores
                
                team_matches.append({
                    "date": match_date,
                    "is_home": is_home,
                    "home_score": home_score,
                    "away_score": away_score,
                    "team_score": home_score if is_home else away_score,
                    "opponent_score": away_score if is_home else home_score,
                })
        
        # Sort by date (newest first) and take last N
        team_matches.sort(key=lambda x: x["date"], reverse=True)
        team_matches = team_matches[:matches_needed]
        
        if len(team_matches) < 3:  # Need at least 3 matches for meaningful form
            logger.warning(f"Insufficient matches for {team_name} (found {len(team_matches)})")
            return self._default_form()  # Return safe defaults
        
        # Calculate statistics
        goals_scored = sum(m["team_score"] for m in team_matches)
        goals_conceded = sum(m["opponent_score"] for m in team_matches)
        wins = sum(1 for m in team_matches if m["team_score"] > m["opponent_score"])
        draws = sum(1 for m in team_matches if m["team_score"] == m["opponent_score"])
        losses = sum(1 for m in team_matches if m["team_score"] < m["opponent_score"])
        clean_sheets = sum(1 for m in team_matches if m["opponent_score"] == 0)
        
        points = wins * 3 + draws
        form_percentage = wins / len(team_matches) if team_matches else 0.0
        
        # Build form string (W=Win, D=Draw, L=Loss)
        form_string = ""
        for m in team_matches:
            if m["team_score"] > m["opponent_score"]:
                form_string += "W"
            elif m["team_score"] == m["opponent_score"]:
                form_string += "D"
            else:
                form_string += "L"
        
        return {
            "goals_scored_5": goals_scored,
            "goals_conceded_5": goals_conceded,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "form_percentage": form_percentage,
            "form_string": form_string,
            "points_5": points,
            "clean_sheets": clean_sheets,
            "matches_count": len(team_matches),
            "avg_goals_scored": goals_scored / len(team_matches) if team_matches else 0.0,
            "avg_goals_conceded": goals_conceded / len(team_matches) if team_matches else 0.0,
        }
    
    def calculate_h2h(
        self,
        team1_name: str,
        team2_name: str,
        competition_code: str,
        before_date: datetime,
        matches_needed: int = 5
    ) -> Dict:
        """
        Calculate head-to-head history between two teams
        
        Returns:
            {
                'team1_wins': int,
                'team2_wins': int,
                'draws': int,
                'total_matches': int,
                'avg_goals_team1': float,
                'avg_goals_team2': float,
                'recent_trend': str,  # "team1_favored", "team2_favored", "balanced"
            }
        """
        date_to = before_date.strftime("%Y-%m-%d")
        date_from = (before_date - timedelta(days=365)).strftime("%Y-%m-%d")  # Last year
        
        all_matches = self.fetch_finished_matches(
            competition_code,
            date_from=date_from,
            date_to=date_to,
            limit=500  # Fetch more to find H2H matches
        )
        
        # Find matches between these two teams
        h2h_matches = []
        team1_id = self.get_team_id_from_matches(team1_name, competition_code)
        team2_id = self.get_team_id_from_matches(team2_name, competition_code)
        
        for match in all_matches:
            match_date_str = match.get("utcDate", "")
            if not match_date_str:
                continue
            
            try:
                match_date = datetime.fromisoformat(match_date_str.replace("Z", "+00:00"))
                if match_date >= before_date:
                    continue
            except:
                continue
            
            home_team = match.get("homeTeam", {})
            away_team = match.get("awayTeam", {})
            
            # Check if both teams are in this match
            home_is_team1 = self._match_team_name(team1_name, [home_team])
            away_is_team1 = self._match_team_name(team1_name, [away_team])
            home_is_team2 = self._match_team_name(team2_name, [home_team])
            away_is_team2 = self._match_team_name(team2_name, [away_team])
            
            if (home_is_team1 and away_is_team2) or (home_is_team2 and away_is_team1):
                score = match.get("score", {}).get("fullTime", {})
                home_score = score.get("home")
                away_score = score.get("away")
                
                if home_score is None or away_score is None:
                    continue
                
                # Determine which team is team1
                team1_is_home = home_is_team1
                team1_score = home_score if team1_is_home else away_score
                team2_score = away_score if team1_is_home else home_score
                
                h2h_matches.append({
                    "date": match_date,
                    "team1_score": team1_score,
                    "team2_score": team2_score,
                })
        
        # Sort by date (newest first) and take last N
        h2h_matches.sort(key=lambda x: x["date"], reverse=True)
        h2h_matches = h2h_matches[:matches_needed]
        
        if len(h2h_matches) == 0:
            logger.warning(f"No H2H history found between {team1_name} and {team2_name}")
            return self._default_h2h()
        
        # Calculate statistics
        team1_wins = sum(1 for m in h2h_matches if m["team1_score"] > m["team2_score"])
        team2_wins = sum(1 for m in h2h_matches if m["team2_score"] > m["team1_score"])
        draws = sum(1 for m in h2h_matches if m["team1_score"] == m["team2_score"])
        
        team1_goals = sum(m["team1_score"] for m in h2h_matches)
        team2_goals = sum(m["team2_score"] for m in h2h_matches)
        
        avg_goals_team1 = team1_goals / len(h2h_matches) if h2h_matches else 0.0
        avg_goals_team2 = team2_goals / len(h2h_matches) if h2h_matches else 0.0
        
        # Determine recent trend
        if team1_wins > team2_wins + 1:
            recent_trend = "team1_favored"
        elif team2_wins > team1_wins + 1:
            recent_trend = "team2_favored"
        else:
            recent_trend = "balanced"
        
        return {
            "team1_wins": team1_wins,
            "team2_wins": team2_wins,
            "draws": draws,
            "total_matches": len(h2h_matches),
            "avg_goals_team1": avg_goals_team1,
            "avg_goals_team2": avg_goals_team2,
            "recent_trend": recent_trend,
            "total_goals": team1_goals + team2_goals,
            "avg_total_goals": (team1_goals + team2_goals) / len(h2h_matches) if h2h_matches else 0.0,
        }
    
    def _default_form(self) -> Dict:
        """Return safe default form data when insufficient matches"""
        return {
            "goals_scored_5": 0,
            "goals_conceded_5": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "form_percentage": 0.5,
            "form_string": "",
            "points_5": 0,
            "clean_sheets": 0,
            "matches_count": 0,
            "avg_goals_scored": 0.0,
            "avg_goals_conceded": 0.0,
        }
    
    def _default_h2h(self) -> Dict:
        """Return safe default H2H data when no history found"""
        return {
            "team1_wins": 0,
            "team2_wins": 0,
            "draws": 0,
            "total_matches": 0,
            "avg_goals_team1": 0.0,
            "avg_goals_team2": 0.0,
            "recent_trend": "unknown",
            "total_goals": 0,
            "avg_total_goals": 0.0,
        }
    
    def calculate_xg_from_form(self, form_data: Dict, is_home: bool = True) -> float:
        """
        Estimate xG (expected goals) from form data
        
        This is a simplified calculation. In production, you'd use
        actual xG data from API-Football or Opta if available.
        """
        if form_data.get("matches_count", 0) < 3:
            return 1.5  # Default safe value
        
        avg_goals_scored = form_data.get("avg_goals_scored", 0.0)
        form_percentage = form_data.get("form_percentage", 0.5)
        
        # Base xG from average goals
        base_xg = avg_goals_scored
        
        # Adjust for form (teams in better form score more)
        form_factor = 0.8 + (form_percentage * 0.4)  # Range: 0.8 to 1.2
        
        # Home advantage (typically +0.2 to +0.3 xG)
        home_advantage = 0.25 if is_home else 0.0
        
        estimated_xg = base_xg * form_factor + home_advantage
        
        # Ensure reasonable bounds (0.5 to 3.0)
        return max(0.5, min(3.0, estimated_xg))

