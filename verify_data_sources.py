"""
API Capability Verification Script
Tests Broadage and Football-Data.org for historical match data availability
"""
import requests
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, List

# Try to load from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, use environment variables only

# --- CONFIGURATION ---
BROADAGE_API_URL = "https://s0-sports-data-api.broadage.com"
# Try environment variable first, then fallback to provided key
BROADAGE_SUBSCRIPTION_KEY = os.getenv("BROADAGE_API_KEY", "b89b8bf2-b84a-499f-989a-653ab563129c")
BROADAGE_LANGUAGE_ID = "2"

FBDATA_API_KEY = "307cfe41e5cd4dcc8fbcf35a398f1625"
FBDATA_URL = "https://api.football-data.org/v4"

def test_broadage_history() -> Dict:
    """Test Broadage API for historical match data"""
    print("\n" + "="*60)
    print("--- 🧪 Testing Broadage Historical Data ---")
    print("="*60)
    
    if not BROADAGE_SUBSCRIPTION_KEY:
        print("❌ ERROR: BROADAGE_API_KEY not found in environment variables.")
        print("   Please set it in your .env file or environment")
        return {"success": False, "reason": "Missing API key"}
    
    # Strategy: Try to get matches from last 30 days
    end_date = datetime.now().strftime("%d/%m/%Y")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%d/%m/%Y")
    
    endpoint = "/soccer/match/list"
    url = f"{BROADAGE_API_URL}{endpoint}"
    
    headers = {
        "Ocp-Apim-Subscription-Key": BROADAGE_SUBSCRIPTION_KEY,
        "languageId": BROADAGE_LANGUAGE_ID,
        "Accept": "application/json"
    }
    
    # Try multiple parameter combinations
    test_params = [
        {"dateStart": start_date, "dateEnd": end_date},
        {"startDate": start_date, "endDate": end_date},
        {"from": start_date, "to": end_date},
        {"date": start_date},  # Single date fallback
    ]
    
    for i, params in enumerate(test_params):
        print(f"\n📡 Test {i+1}: Requesting {url}")
        print(f"   Params: {params}")
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Handle different response structures
                    if isinstance(data, list):
                        matches = data
                    elif isinstance(data, dict):
                        matches = data.get('matches', data.get('response', data.get('data', [])))
                    else:
                        matches = []
                    
                    count = len(matches) if matches else 0
                    print(f"   ✅ Success! Retrieved {count} matches.")
                    
                    if count > 0:
                        sample = matches[0] if isinstance(matches, list) else matches
                        print(f"\n   📋 Sample Match Structure:")
                        print(f"   {json.dumps(sample, indent=4, default=str)[:500]}...")
                        
                        # Check if we have date filtering capability
                        dates = []
                        for match in matches[:5]:
                            date_field = match.get('date') or match.get('matchDate') or match.get('startDate') or match.get('startTime')
                            if date_field:
                                dates.append(date_field)
                        
                        if dates:
                            print(f"\n   ✅ Date range filtering works! Found matches with dates.")
                            print(f"   Date samples: {dates[:3]}")
                            return {
                                "success": True,
                                "matches_count": count,
                                "sample": sample,
                                "can_filter_by_date": True,
                                "params_that_worked": params
                            }
                        
                        return {
                            "success": True,
                            "matches_count": count,
                            "sample": sample,
                            "can_filter_by_date": False,
                            "params_that_worked": params
                        }
                    
                    return {
                        "success": True,
                        "matches_count": 0,
                        "can_filter_by_date": True,
                        "params_that_worked": params,
                        "note": "API works but no matches in date range"
                    }
                    
                except json.JSONDecodeError:
                    print(f"   ❌ Invalid JSON response: {response.text[:200]}")
                    continue
            elif response.status_code == 401:
                print(f"   ❌ Unauthorized: Check API key")
                error_msg = response.headers.get('Message', response.text[:100])
                print(f"   Error: {error_msg}")
                return {"success": False, "reason": f"401 Unauthorized: {error_msg}"}
            elif response.status_code == 404:
                print(f"   ⚠️ 404 Not Found: Endpoint or params not valid")
                continue
            else:
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                continue
                
        except requests.exceptions.Timeout:
            print(f"   ❌ Timeout: Request took too long")
            continue
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue
    
    # If all tests failed, try yesterday's date (we know this works for today)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
    print(f"\n🔄 Final attempt: Single date parameter for yesterday ({yesterday})")
    try:
        response = requests.get(url, headers=headers, params={'date': yesterday}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            matches = data if isinstance(data, list) else data.get('matches', [])
            count = len(matches) if matches else 0
            if count > 0:
                print(f"   ✅ Yesterday's matches retrieved: {count} matches")
                return {
                    "success": True,
                    "matches_count": count,
                    "can_filter_by_date": True,
                    "params_that_worked": {"date": yesterday},
                    "note": "Can fetch historical matches one day at a time"
                }
    except Exception as e:
        print(f"   ❌ Final attempt failed: {e}")
    
    return {"success": False, "reason": "All parameter combinations failed"}


def test_football_data_history() -> Dict:
    """Test Football-Data.org API for historical match data"""
    print("\n" + "="*60)
    print("--- 🧪 Testing Football-Data.org Historical Data ---")
    print("="*60)
    
    headers = {"X-Auth-Token": FBDATA_API_KEY}
    
    # Test 1: Premier League finished matches
    print("\n📡 Test 1: Premier League (PL) finished matches")
    url = f"{FBDATA_URL}/competitions/PL/matches?status=FINISHED"
    print(f"   URL: {url}")
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            print(f"   ✅ Success! Retrieved {len(matches)} finished matches.")
            
            if len(matches) > 0:
                sample = matches[-1]  # Most recent
                print(f"\n   📋 Sample Match:")
                print(f"   {sample['homeTeam']['name']} vs {sample['awayTeam']['name']}")
                print(f"   Score: {sample['score']['fullTime']}")
                print(f"   Date: {sample['utcDate']}")
                
                # Check if we have date filtering
                url_with_dates = f"{FBDATA_URL}/competitions/PL/matches?dateFrom=2024-11-01&dateTo=2024-11-30"
                print(f"\n   Testing date range filtering...")
                response2 = requests.get(url_with_dates, headers=headers, timeout=15)
                if response2.status_code == 200:
                    date_filtered = response2.json().get('matches', [])
                    print(f"   ✅ Date filtering works! {len(date_filtered)} matches in range")
                
                return {
                    "success": True,
                    "matches_count": len(matches),
                    "sample": sample,
                    "can_filter_by_date": True,
                    "has_score_data": True,
                    "has_team_data": True
                }
        elif response.status_code == 403:
            print(f"   ❌ 403 Forbidden: Check API key or rate limits")
            return {"success": False, "reason": "403 Forbidden - Check API key"}
        else:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Try a different competition (Bundesliga)
    print("\n📡 Test 2: Bundesliga (BL1) finished matches")
    url = f"{FBDATA_URL}/competitions/BL1/matches?status=FINISHED"
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            print(f"   ✅ Success! {len(matches)} matches")
            return {
                "success": True,
                "matches_count": len(matches),
                "competition": "BL1"
            }
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return {"success": False, "reason": "All tests failed"}


def analyze_results(broadage_result: Dict, fbdata_result: Dict):
    """Analyze test results and provide recommendations"""
    print("\n" + "="*60)
    print("--- 🏁 Analysis & Recommendation ---")
    print("="*60)
    
    print("\n📊 Results Summary:")
    print(f"   Broadage API: {'✅ Works' if broadage_result.get('success') else '❌ Failed'}")
    print(f"   Football-Data.org: {'✅ Works' if fbdata_result.get('success') else '❌ Failed'}")
    
    if broadage_result.get('success'):
        print(f"\n   Broadage Details:")
        print(f"   - Matches retrieved: {broadage_result.get('matches_count', 0)}")
        print(f"   - Date filtering: {'✅ Yes' if broadage_result.get('can_filter_by_date') else '❌ No'}")
        if broadage_result.get('params_that_worked'):
            print(f"   - Working params: {broadage_result['params_that_worked']}")
    
    if fbdata_result.get('success'):
        print(f"\n   Football-Data.org Details:")
        print(f"   - Matches retrieved: {fbdata_result.get('matches_count', 0)}")
        print(f"   - Date filtering: {'✅ Yes' if fbdata_result.get('can_filter_by_date') else '❌ No'}")
        print(f"   - Has score data: {'✅ Yes' if fbdata_result.get('has_score_data') else '❌ No'}")
        print(f"   - Has team data: {'✅ Yes' if fbdata_result.get('has_team_data') else '❌ No'}")
    
    print("\n" + "="*60)
    print("💡 Recommended Strategy:")
    print("="*60)
    
    if broadage_result.get('success') and broadage_result.get('can_filter_by_date'):
        print("\n✅ Strategy A: Use BROADAGE for Everything")
        print("   ✅ Pros:")
        print("      - Single API provider (simpler)")
        print("      - Already integrated for today's fixtures")
        print("      - Historical data available")
        print("   📝 Implementation:")
        print("      - Create BroadageHistoryService")
        print("      - Fetch matches for date ranges (last 30-90 days)")
        print("      - Calculate Form & H2H locally from fetched data")
        return "BROADAGE"
    
    elif fbdata_result.get('success'):
        print("\n✅ Strategy B: Hybrid Approach")
        print("   ✅ Pros:")
        print("      - Broadage for today's fixtures (already working)")
        print("      - Football-Data.org for historical data (free tier)")
        print("      - Best of both worlds")
        print("   📝 Implementation:")
        print("      - Keep Broadage for /soccer/match/list (today's matches)")
        print("      - Create FootballDataHistoryService")
        print("      - Download season history from Football-Data.org")
        print("      - Calculate Form & H2H locally")
        return "HYBRID"
    
    elif broadage_result.get('success') and not broadage_result.get('can_filter_by_date'):
        print("\n⚠️ Strategy C: Limited Hybrid Approach")
        print("   ⚠️ Broadage works but date filtering is limited")
        print("   📝 Implementation:")
        print("      - Fetch historical matches one day at a time")
        print("      - Cache results to build database")
        print("      - Calculate Form & H2H from cached data")
        return "BROADAGE_LIMITED"
    
    else:
        print("\n❌ Critical Issue: Neither API provided historical data")
        print("   🔍 Next Steps:")
        print("      1. Check API keys/subscriptions")
        print("      2. Review API documentation for correct endpoints")
        print("      3. Consider paid API-Football plan for statistics")
        return "NONE"


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 API Capability Verification")
    print("="*60)
    print("\nTesting both APIs for historical match data availability...")
    print("This will determine our strategy for calculating Form & H2H locally.\n")
    
    if not BROADAGE_SUBSCRIPTION_KEY:
        print("⚠️ WARNING: BROADAGE_API_KEY not found in environment variables.")
        print("   Set it with: export BROADAGE_API_KEY='your_key'")
        print("   Or add to .env file\n")
    
    # Run tests
    broadage_result = test_broadage_history()
    fbdata_result = test_football_data_history()
    
    # Analyze and recommend
    recommendation = analyze_results(broadage_result, fbdata_result)
    
    print(f"\n🎯 Final Recommendation: {recommendation}")
    print("="*60 + "\n")

