"""
Match Fetcher
Fetches today's matches from API-Football/Broadage and enriches with real statistics
"""
from typing import List, Dict
import requests
import os
from datetime import datetime, timedelta
from typing import Optional
import logging

# OddsAPI client (optional - fallback if not available)
try:
    from src.services.odds_api_client import OddsAPIClient
except ImportError:
    OddsAPIClient = None

# Football-Data.org history service for real statistics
try:
    from src.services.football_data_history_service import FootballDataHistoryService
except ImportError:
    FootballDataHistoryService = None

logger = logging.getLogger(__name__)


class MatchFetcher:
    """Fetches matches from API-Football or Broadage API"""
    
    def __init__(self):
        # Check which API to use - Broadage or API-Football
        self.use_broadage = os.getenv("USE_BROADAGE_API", "false").lower() == "true"
        
        if self.use_broadage:
            self.api_key = os.getenv("BROADAGE_API_KEY", "")
            # Broadage API base URL - from user's dashboard: https://s0-sports-data-api.broadage.com
            self.base_url = os.getenv("BROADAGE_API_URL", "https://s0-sports-data-api.broadage.com")
            # Default to 2 (working for trial subscription), can override with env var
            self.language_id = int(os.getenv("BROADAGE_LANGUAGE_ID", "2"))  # Default: 2 (works for trial)
            
            # Headers: Ocp-Apim-Subscription-Key is standard for Azure API Management
            # languageId might need to be in headers OR params - trying headers first
            self.headers = {
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Accept": "application/json"
            }
            # languageId as header (if not working, we'll try as param)
            self.language_id_header = str(self.language_id)
            
            print("🌐 Using Broadage API")
            print(f"   Base URL (full): {self.base_url}")
            print(f"   Base URL length: {len(self.base_url)} chars")
            print(f"   Expected: https://s0-sports-data-api.broadage.com")
            print(f"   Language ID: {self.language_id}")
            if "s0-sports-data-api.broadage.com" not in self.base_url:
                print(f"   ⚠️  WARNING: Base URL doesn't match expected format!")
                print(f"   ⚠️  Check BROADAGE_API_URL environment variable in Coolify")
        else:
            self.api_key = os.getenv("API_FOOTBALL_KEY", "")
            self.base_url = "https://v3.football.api-sports.io"
            self.headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": "v3.football.api-sports.io"
            }
            print("🌐 Using API-Football")
        # Initialize OddsAPI client (optional)
        self.odds_client = OddsAPIClient() if OddsAPIClient else None
        # Cache odds for today's matches
        self._odds_cache = {}
        self._odds_fetched = False
        
        # Initialize Football-Data.org history service for real statistics
        self.history_service = FootballDataHistoryService() if FootballDataHistoryService else None
        if self.history_service:
            logger.info("✅ Football-Data.org history service initialized - real statistics enabled")
        else:
            logger.warning("⚠️ Football-Data.org history service not available - using defaults")
    
    def get_today_matches(self, leagues: Optional[List[int]] = None) -> List[Dict]:
        """
        Fetch today's matches from API-Football/Broadage and enrich with real statistics
        
        Args:
            leagues: List of league IDs (e.g., [39 for EPL, 140 for LaLiga])
        
        Returns:
            List of match dictionaries enriched with:
            - Real team form (last 5 matches)
            - Real H2H history
            - Real xG calculated from historical data
            - Real odds (if available)
        """
        if not self.api_key:
            api_key_name = "BROADAGE_API_KEY" if self.use_broadage else "API_FOOTBALL_KEY"
            print(f"⚠️ {api_key_name} not set! Cannot fetch real matches.")
            print(f"   Please set {api_key_name} environment variable in Coolify")
            return []
        
        # Get current date - check system time
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        current_year = now.year
        current_month = now.month
        
        print(f"📅 System date: {today} (Year: {current_year}, Month: {current_month})")
        
        # Determine current season - European leagues run Aug-May
        # If month is Aug-Dec, season = current year; if Jan-Jul, season = previous year
        if current_month >= 8:  # Aug-Dec
            season_year = current_year
        else:  # Jan-Jul
            season_year = current_year - 1
        
        # API-Football free plan limitation: Only supports seasons 2021-2023
        # If we need a newer season, we'll get an error and can handle it
        print(f"🔍 Fetching matches for {today} from API-Football (season: {season_year})...")
        print(f"   ⚠️ Note: Free plan only supports seasons 2021-2023")
        print(f"   💡 If season {season_year} fails, you need a paid API-Football plan")
        
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
        
        # Fetch matches from selected API
        if self.use_broadage:
            basic_matches = self._fetch_from_broadage(today, leagues)
        else:
            basic_matches = self._fetch_from_api_football(today, season_year, leagues)
        
        # Enrich matches with real statistics from Football-Data.org
        if basic_matches and self.history_service:
            logger.info(f"Enriching {len(basic_matches)} matches with real statistics...")
            enriched_matches = []
            for match in basic_matches:
                enriched = self._enrich_match_with_statistics(match)
                enriched_matches.append(enriched)
            return enriched_matches
        
        return basic_matches
    
    def _fetch_from_broadage(self, today: str, leagues: List[int]) -> List[Dict]:
        """Fetch matches from Broadage API"""
        api_errors = []
        all_matches = []
        
        # Broadage API endpoints - based on their documentation structure
        # Documentation shows: GET {{host}}/global/sport/list
        # Soccer/Football sport ID is 1 (from their docs)
        # Try multiple endpoint patterns and authentication methods
        
        print(f"📡 Fetching matches from Broadage API for {today}...")
        
        # Based on Broadage Soccer API docs:
        # - Endpoints may be case-sensitive (TournamentFixture shows capital F)
        # - Try different "Match List" endpoint variations
        # - Headers: languageId (INT, Required), Ocp-Apim-Subscription-Key (Required)
        
        matches_data = []
        api_errors = []
        
        # Try exact endpoint paths from Broadage docs (case-sensitive)
        # Based on error: /soccer/match/list exists but returns "Language is invalid"
        # Try the exact paths from documentation
        # Priority: Scheduled first (to get all matches for today), then Live, then All
        possible_endpoints = [
            f"{self.base_url}/soccer/MatchList/Scheduled",  # For scheduled matches (PRIORITY - gets all today's matches)
            f"{self.base_url}/soccer/match/list",  # Lowercase version (exists but language issue)
            f"{self.base_url}/soccer/MatchList/All",  # Exact case from docs
            f"{self.base_url}/soccer/MatchList/Live",  # Live matches (only currently playing)
        ]
        
        # Try date parameter variations (Broadage might use different date formats)
        date_formats = [
            today,  # YYYY-MM-DD
            today.replace("-", "/"),  # YYYY/MM/DD
            datetime.strptime(today, "%Y-%m-%d").strftime("%d/%m/%Y"),  # DD/MM/YYYY
        ]
        
        # Based on error: "Language is invalid" for languageId=1 and 0
        # "Language Id is mandatory" - must include it
        # Solution: Try languageId values 2, 3, 4, etc. until we find a valid one
        # Trial subscriptions often only allow specific language IDs (not 1 or 0)
        today_dd_mm_yyyy = datetime.strptime(today, "%Y-%m-%d").strftime("%d/%m/%Y")
        
        # Start with the configured languageId (default 2, which works for trial)
        # If that fails, try other values
        primary_lang_id = str(self.language_id)
        fallback_language_ids = [str(i) for i in range(2, 12) if i != self.language_id]
        
        # Try with date parameter first, then without date (to get more matches)
        auth_configs = [
            {
                "name": f"languageId={primary_lang_id} (configured/default) + date DD/MM/YYYY",
                "headers": {
                    "Ocp-Apim-Subscription-Key": self.api_key.strip(),
                    "Accept": "application/json",
                    "languageId": primary_lang_id
                },
                "params": {"date": today_dd_mm_yyyy}
            },
            {
                "name": f"languageId={primary_lang_id} (configured/default) - NO DATE (get all)",
                "headers": {
                    "Ocp-Apim-Subscription-Key": self.api_key.strip(),
                    "Accept": "application/json",
                    "languageId": primary_lang_id
                },
                "params": {}  # No date - might return more matches, we'll filter client-side
            }
        ]
        
        # Add fallback language IDs only if primary fails
        for lang_id in fallback_language_ids[:3]:  # Limit to 3 fallbacks
            auth_configs.append({
                "name": f"languageId={lang_id} (fallback) + date DD/MM/YYYY",
                "headers": {
                    "Ocp-Apim-Subscription-Key": self.api_key.strip(),
                    "Accept": "application/json",
                    "languageId": lang_id
                },
                "params": {"date": today_dd_mm_yyyy}
            })
        
        # Try each endpoint with authentication configs
        # Stop immediately when we find a working languageId
        for endpoint in possible_endpoints:
            for config in auth_configs:
                try:
                    print(f"  📡 Calling: {endpoint}")
                    print(f"     Config: {config['name']}")
                    print(f"     Headers: Ocp-Apim-Subscription-Key={self.api_key[:10]}..., languageId={self.language_id}")
                    print(f"     Params: {config['params']}")
                    
                    response = requests.get(
                        endpoint, 
                        headers=config['headers'], 
                        params=config['params'], 
                        timeout=15
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"  ✅ Success! Endpoint: {endpoint}")
                        print(f"  ✅ Config that worked: {config['name']}")
                        print(f"  🔍 Response structure: {list(data.keys())[:5] if isinstance(data, dict) else 'Array'}...")
                        
                        # Parse Broadage response based on their API structure
                        # Response could be array of matches or wrapped in object
                        matches_data = []
                        if isinstance(data, list):
                            matches_data = data
                        elif isinstance(data, dict):
                            # Try common response formats
                            matches_data = (
                                data.get("data", []) or 
                                data.get("matches", []) or 
                                data.get("results", []) or
                                data.get("response", []) or
                                data.get("list", []) or
                                []
                            )
                        
                        # Filter by date if matches returned
                        # NOTE: Broadage might already filter by date parameter, so we're getting limited results
                        # If we want more matches, we might need to remove date filter or fetch multiple days
                        if matches_data:
                            filtered_matches = []
                            for match in matches_data:
                                match_date = match.get("date") or match.get("matchDate") or match.get("startDate") or match.get("utcDate")
                                if match_date:
                                    # Parse date format and check if it's today
                                    try:
                                        # Broadage date format: "10/08/2018 19:00:00" or ISO format
                                        if "/" in str(match_date):
                                            # Format: DD/MM/YYYY HH:MM:SS
                                            date_part = str(match_date).split()[0]
                                            parsed_date = datetime.strptime(date_part, "%d/%m/%Y")
                                        else:
                                            parsed_date = datetime.fromisoformat(str(match_date).replace("Z", "+00:00"))
                                        
                                        if parsed_date.date() == datetime.strptime(today, "%Y-%m-%d").date():
                                            filtered_matches.append(match)
                                    except Exception as e:
                                        # If date parsing fails, include the match (might be today)
                                        # This helps get more matches if date field is missing or different format
                                        filtered_matches.append(match)
                            # Only filter if we found matches with valid dates
                            # Otherwise keep all matches (date filtering might have removed all)
                            if filtered_matches:
                                matches_data = filtered_matches
                            # If no filtered matches but we have data, it might be that dates don't match format
                            # In that case, keep all matches (they might all be for today)
                            print(f"  📊 After date filtering: {len(matches_data)} matches")
                        
                        print(f"  ✅ Found {len(matches_data)} matches from Broadage for {today}")
                        print(f"  🎉 Working languageId: {config['headers'].get('languageId')}")
                        print(f"  📊 Config used: {config['name']}")
                        
                        # Store best result
                        if not best_matches or len(matches_data) > len(best_matches):
                            best_matches = matches_data.copy()
                            best_config_used = config
                            best_endpoint_used = endpoint
                        
                        # If we got good number of matches, use this
                        if len(matches_data) >= 10:
                            print(f"  ✅ Got {len(matches_data)} matches - using this config!")
                            break  # Got enough matches, use this config
                        else:
                            print(f"  ⚠️ Only {len(matches_data)} matches - will try other configs for more...")
                            # Continue to try other configs to get more matches
                            continue
                        
                    elif response.status_code == 401:
                        error_body = ""
                        try:
                            # Try JSON first
                            try:
                                error_json = response.json()
                                error_body = str(error_json)
                            except:
                                error_body = response.text[:1000] if response.text else "No response body"
                        except:
                            error_body = "Could not read response body"
                        
                        # Check response headers for error details
                        response_headers = dict(response.headers)
                        error_message = response_headers.get('Message', '')
                        error_code = response_headers.get('MessageCode', '')
                        
                        error_msg = f"401 Unauthorized - {config['name']}"
                        api_errors.append(error_msg)
                        print(f"  ❌ {error_msg}")
                        print(f"     Response body: {error_body}")
                        print(f"     Response headers: {response_headers}")
                        if error_message:
                            print(f"     ⚠️ API Error Message: {error_message} (Code: {error_code})")
                            if "Language is invalid" in error_message:
                                print(f"     💡 languageId={config['headers'].get('languageId', 'NOT SET')} is not valid for your subscription")
                                print(f"     💡 Check Broadage dashboard for available language IDs")
                        print(f"     Request headers sent: {config['headers']}")
                        print(f"     API key preview: {self.api_key[:15]}... (length: {len(self.api_key)})")
                        
                        # Check for specific error indicators
                        error_lower = (error_body + error_message).lower()
                        if "subscription" in error_lower or "key" in error_lower:
                            print(f"     ⚠️ API key authentication issue detected")
                        if "language" in error_lower or "Language is invalid" in error_message:
                            print(f"     ⚠️ languageId value issue - try different language ID or check dashboard")
                        if "ip" in error_lower or "whitelist" in error_lower:
                            print(f"     ⚠️ IP whitelist issue detected")
                        if not error_body or error_body == "No response body":
                            print(f"     ⚠️ Empty response body but error in headers")
                        
                        continue
                        
                    elif response.status_code == 404:
                        print(f"  ⚠️ 404 Not Found - {config['name']}")
                        print(f"     This endpoint might not exist or requires different parameters")
                        continue
                        
                    elif response.status_code == 403:
                        error_body = ""
                        try:
                            error_body = response.text[:500] if response.text else "No response body"
                        except:
                            error_body = "Could not read response body"
                        
                        error_msg = "403 Forbidden - IP not whitelisted"
                        api_errors.append(error_msg)
                        print(f"  ❌ {error_msg}")
                        print(f"     Response: {error_body}")
                        print(f"     💡 Add your server IP (84.54.23.80) to Broadage whitelist")
                        break  # IP issue
                        
                    else:
                        error_body = ""
                        try:
                            error_body = response.text[:500] if response.text else "No response body"
                        except:
                            error_body = "Could not read response body"
                        
                        print(f"  ⚠️ HTTP {response.status_code} - {config['name']}")
                        print(f"     Response: {error_body}")
                        continue
                        
                except Exception as e:
                    import traceback
                    print(f"  ❌ Error with {endpoint} ({config['name']}): {e}")
                    print(f"     Traceback: {traceback.format_exc()[:200]}")
                    continue
            
            # If we found matches with this endpoint, check if we should continue
            if matches_data and len(matches_data) >= 10:
                break  # Got enough matches, stop trying
        
        # Use best matches if we found any
        if best_matches:
            matches_data = best_matches
            print(f"\n📊 Using best result: {len(matches_data)} matches from {best_endpoint_used}")
            print(f"   Config: {best_config_used['name'] if best_config_used else 'N/A'}")
        elif matches_data:
            # Fallback to last successful matches_data
            print(f"\n📊 Using last result: {len(matches_data)} matches")
        
        # Parse matches if found
        if matches_data:
            for match_data in matches_data:
                # Filter by leagues if specified and if league info is available
                match_league_id = match_data.get("league", {}).get("id") or match_data.get("leagueId") or match_data.get("league_id")
                if leagues and match_league_id and match_league_id not in leagues:
                    continue
                
                match = self._parse_broadage_fixture(match_data)
                if match:
                    all_matches.append(match)
        
        if api_errors:
            print(f"\n⚠️ Broadage API Errors: {len(api_errors)} errors")
            for err in api_errors[:5]:
                print(f"  - {err}")
        
        print(f"📊 Total matches fetched from Broadage: {len(all_matches)}")
        return all_matches
    
    def _fetch_from_api_football(self, today: str, season_year: int, leagues: List[int]) -> List[Dict]:
        """Fetch matches from API-Football"""
        all_matches = []
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
                    if "errors" in data and data["errors"]:
                        error_msgs = data.get("errors", {})
                        error_text = str(error_msgs)
                        print(f"  🔍 Full error response: {error_msgs}")
                        
                        # If error mentions free plan limitation, check what we can do
                        if isinstance(error_msgs, dict) and 'plan' in str(error_msgs):
                            error_text = str(error_msgs.get('plan', ''))
                            if 'Free plans' in error_text and '2021 to 2023' in error_text:
                                print(f"  ⚠️ League {league_id}: Free plan limitation detected")
                                print(f"     Trying with season 2024 (current season)...")
                                # Retry with 2024 season (current season)
                                params_2024 = {
                                    "date": today,
                                    "league": league_id,
                                    "season": 2024
                                }
                                try:
                                    response_2024 = requests.get(url, headers=self.headers, params=params_2024, timeout=15)
                                    if response_2024.status_code == 200:
                                        data_2024 = response_2024.json()
                                        if not (data_2024.get("errors") and data_2024["errors"]):
                                            data = data_2024
                                            print(f"  ✅ League {league_id}: Successfully fetched with season 2024!")
                                        else:
                                            api_errors.append(f"League {league_id}: Free plan - no access to current season")
                                            print(f"  ❌ League {league_id}: Free plan cannot access current season data")
                                            continue
                                    else:
                                        api_errors.append(f"League {league_id}: HTTP {response_2024.status_code}")
                                        continue
                                except:
                                    pass
                        
                        if "errors" in data and data["errors"]:
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
    
    def _parse_broadage_fixture(self, fixture_data: Dict) -> Optional[Dict]:
        """Parse Broadage API fixture to internal format"""
        try:
            # Broadage API response format - teams come as dicts with 'name' field
            # Extract team names properly
            home_team_obj = fixture_data.get("homeTeam") or fixture_data.get("home_team") or fixture_data.get("home")
            away_team_obj = fixture_data.get("awayTeam") or fixture_data.get("away_team") or fixture_data.get("away")
            
            # Extract name if it's a dict, otherwise use as string
            if isinstance(home_team_obj, dict):
                home_team = home_team_obj.get("name", "") or home_team_obj.get("shortName", "") or home_team_obj.get("mediumName", "")
            else:
                home_team = str(home_team_obj) if home_team_obj else ""
            
            if isinstance(away_team_obj, dict):
                away_team = away_team_obj.get("name", "") or away_team_obj.get("shortName", "") or away_team_obj.get("mediumName", "")
            else:
                away_team = str(away_team_obj) if away_team_obj else ""
            
            # Ensure we have team names
            if not home_team or not away_team:
                print(f"⚠️ Missing team names in fixture: home={home_team_obj}, away={away_team_obj}")
                return None
            
            # Extract league info - could be dict or string
            league_info = fixture_data.get("league") or fixture_data.get("tournament")
            if isinstance(league_info, dict):
                league_name = league_info.get("name", "") or league_info.get("shortName", "")
                league_id = league_info.get("id")
            else:
                league_name = str(league_info) if league_info else ""
                league_id = fixture_data.get("leagueId") or fixture_data.get("league_id") or fixture_data.get("tournamentId")
            
            # Parse date - try multiple formats
            date_str = (
                fixture_data.get("date", "") or
                fixture_data.get("startTime", "") or
                fixture_data.get("matchDate", "") or
                fixture_data.get("kickoff", "")
            )
            
            try:
                if date_str:
                    # Try multiple date formats
                    if 'T' in str(date_str) or 'Z' in str(date_str):
                        # ISO format: "2025-11-28T19:00:00Z" or "2025-11-28T19:00:00+00:00"
                        match_date = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
                    elif '/' in str(date_str):
                        # DD/MM/YYYY format: "28/11/2025 19:00:00"
                        date_part = str(date_str).split()[0] if ' ' in str(date_str) else str(date_str)
                        match_date = datetime.strptime(date_part, "%d/%m/%Y")
                    else:
                        # Try standard format
                        match_date = datetime.fromisoformat(str(date_str))
                else:
                    match_date = datetime.now()
            except Exception as date_error:
                print(f"⚠️ Could not parse date '{date_str}': {date_error}, using current time")
                match_date = datetime.now()
            
            # Get odds - try multiple formats
            odds_data = fixture_data.get("odds", {})
            if not isinstance(odds_data, dict):
                odds_data = {}
            
            match = {
                'id': str(fixture_data.get("id", fixture_data.get("matchId", ""))),
                'home_team': home_team,
                'away_team': away_team,
                'league': league_name or "Unknown League",
                'league_tier': self._map_league_tier(league_id) if league_id else "other",
                'match_date': match_date,
                'home_odds': float(odds_data.get("home", odds_data.get("1", 2.0))) if odds_data else 2.0,
                'draw_odds': float(odds_data.get("draw", odds_data.get("X", 3.0))) if odds_data else 3.0,
                'away_odds': float(odds_data.get("away", odds_data.get("2", 2.5))) if odds_data else 2.5,
                
                # Default stats - Broadage might provide more detailed stats
                'home_form': {
                    'goals_scored_5': 10,
                    'goals_conceded_5': 4,
                    'form_percentage': 0.7,
                    'shots_on_target_avg': 5.0,
                    'goals_variance': 5.0
                },
                'away_form': {
                    'goals_scored_5': 8,
                    'goals_conceded_5': 5,
                    'form_percentage': 0.65,
                    'shots_on_target_avg': 4.5,
                    'goals_variance': 6.0
                },
                'home_xg': 1.8,
                'away_xg': 1.5,
                'home_position': 8,
                'away_position': 12,
                'league_size': 20,
                'table_gap': 4,
                'pressure_index': 0.5,
                'is_derby': False,
                'is_must_win': False,
                'key_player_missing': False,
                'fixture_congestion': 7,
                'home_fixture_congestion': 7,
                'away_fixture_congestion': 7
            }
            
            return match
            
        except Exception as e:
            print(f"Error parsing Broadage fixture: {e}")
            return None
    
    def _enrich_match_with_statistics(self, match: Dict) -> Dict:
        """
        Enrich match with real statistics from Football-Data.org
        
        Adds:
        - Real team form (last 5 matches)
        - Real H2H history
        - Real xG calculated from historical data
        
        Falls back to defaults if enrichment fails
        """
        if not self.history_service:
            logger.debug("History service not available, using defaults")
            return match
        
        try:
            home_team = match.get('home_team', '')
            away_team = match.get('away_team', '')
            league_name = match.get('league', '')
            league_id = match.get('league_id')  # May not be set
            match_date = match.get('match_date', datetime.now())
            
            if not home_team or not away_team:
                logger.warning(f"Missing team names, skipping enrichment: {home_team} vs {away_team}")
                return match
            
            # Get competition code for Football-Data.org
            competition_code = self.history_service.get_competition_code(
                league_id=league_id,
                league_name=league_name
            )
            
            if not competition_code:
                logger.warning(f"⚠️ Could not map league '{league_name}' (ID: {league_id}) to Football-Data.org code, using defaults")
                logger.warning(f"   Available mappings: {list(self.history_service.LEAGUE_MAPPING.keys())}")
                return match
            
            logger.info(f"✅ Mapped league '{league_name}' (ID: {league_id}) to competition code: {competition_code}")
            
            logger.info(f"Enriching {home_team} vs {away_team} ({competition_code})")
            
            # Fetch real team form
            try:
                home_form = self.history_service.calculate_team_form(
                    team_name=home_team,
                    competition_code=competition_code,
                    before_date=match_date,
                    matches_needed=5
                )
                away_form = self.history_service.calculate_team_form(
                    team_name=away_team,
                    competition_code=competition_code,
                    before_date=match_date,
                    matches_needed=5
                )
                
                # Calculate real xG from form
                home_xg = self.history_service.calculate_xg_from_form(home_form, is_home=True)
                away_xg = self.history_service.calculate_xg_from_form(away_form, is_home=False)
                
                # Fetch H2H history
                h2h = self.history_service.calculate_h2h(
                    team1_name=home_team,
                    team2_name=away_team,
                    competition_code=competition_code,
                    before_date=match_date,
                    matches_needed=5
                )
                
                # Update match with real data
                match['home_form'] = {
                    'goals_scored_5': home_form.get('goals_scored_5', 0),
                    'goals_conceded_5': home_form.get('goals_conceded_5', 0),
                    'form_percentage': home_form.get('form_percentage', 0.5),
                    'wins': home_form.get('wins', 0),
                    'draws': home_form.get('draws', 0),
                    'losses': home_form.get('losses', 0),
                    'form_string': home_form.get('form_string', ''),
                    'points_5': home_form.get('points_5', 0),
                    'clean_sheets': home_form.get('clean_sheets', 0),
                    'matches_count': home_form.get('matches_count', 0),
                    'avg_goals_scored': home_form.get('avg_goals_scored', 0.0),
                    'avg_goals_conceded': home_form.get('avg_goals_conceded', 0.0),
                    'shots_on_target_avg': home_form.get('avg_goals_scored', 0.0) * 2.5,  # Estimate SOT from goals
                    'goals_variance': abs(home_form.get('avg_goals_scored', 1.5) - 1.5) * 2  # Estimate variance
                }
                
                match['away_form'] = {
                    'goals_scored_5': away_form.get('goals_scored_5', 0),
                    'goals_conceded_5': away_form.get('goals_conceded_5', 0),
                    'form_percentage': away_form.get('form_percentage', 0.5),
                    'wins': away_form.get('wins', 0),
                    'draws': away_form.get('draws', 0),
                    'losses': away_form.get('losses', 0),
                    'form_string': away_form.get('form_string', ''),
                    'points_5': away_form.get('points_5', 0),
                    'clean_sheets': away_form.get('clean_sheets', 0),
                    'matches_count': away_form.get('matches_count', 0),
                    'avg_goals_scored': away_form.get('avg_goals_scored', 0.0),
                    'avg_goals_conceded': away_form.get('avg_goals_conceded', 0.0),
                    'shots_on_target_avg': away_form.get('avg_goals_scored', 0.0) * 2.5,
                    'goals_variance': abs(away_form.get('avg_goals_scored', 1.5) - 1.5) * 2
                }
                
                match['home_xg'] = round(home_xg, 2)
                match['away_xg'] = round(away_xg, 2)
                
                # Add H2H data
                match['h2h'] = {
                    'home_wins': h2h.get('team1_wins', 0),
                    'away_wins': h2h.get('team2_wins', 0),
                    'draws': h2h.get('draws', 0),
                    'total_matches': h2h.get('total_matches', 0),
                    'avg_goals_home': h2h.get('avg_goals_team1', 0.0),
                    'avg_goals_away': h2h.get('avg_goals_team2', 0.0),
                    'recent_trend': h2h.get('recent_trend', 'unknown'),
                    'avg_total_goals': h2h.get('avg_total_goals', 0.0)
                }
                
                # Mark as enriched with real data
                match['_stats_source'] = 'football_data_org'
                match['_enrichment_status'] = 'success'
                
                logger.info(f"✅ Enriched {home_team} vs {away_team}: Form={home_form.get('form_string', 'N/A')}, H2H={h2h.get('total_matches', 0)} matches")
                
            except Exception as form_error:
                logger.warning(f"Failed to fetch form/H2H for {home_team} vs {away_team}: {form_error}")
                match['_enrichment_status'] = 'partial_failure'
                # Keep defaults, but mark that we tried
                return match
                
        except Exception as e:
            logger.error(f"Error enriching match statistics: {e}")
            match['_enrichment_status'] = 'failed'
            # Return match with defaults
            return match
        
        return match
    
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

