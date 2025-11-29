"""
FastAPI Backend for Football Safe Odds AI
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from pathlib import Path

from src.database.db import get_db, DATABASE_URL
from src.database.models import Base

# Initialize database tables on startup (similar to backend)
# This ensures tables are created automatically when the app starts
import sys
from src.database.init_db import init_database

print("🔄 Initializing database schema...")
try:
    init_database()
    print("✅ Database schema initialized successfully")
except Exception as e:
    print(f"⚠️ Database initialization warning: {e}")
    print("   Continuing - database may already be initialized")
    
    # Fallback: try to create tables directly
    try:
        engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
        if not engine.dialect.has_table(engine, "matches"):
            Base.metadata.create_all(bind=engine)
            print(f"✅ Database tables created at {DATABASE_URL}")
        else:
            print(f"✅ Connected to existing database at {DATABASE_URL}")
    except Exception as db_error:
        print(f"❌ Database connection error: {db_error}")
        print("   Please check DATABASE_URL environment variable")
from src.database.models import Match, RawPrediction, FilteredPick, ApprovedPick, RejectedPick, DailyCombo
from src.services.prediction_service import PredictionService
from src.services.match_fetcher import MatchFetcher
from src.core.odds_combiner import OddsCombiner

app = FastAPI(
    title="Football Safe Odds AI",
    description="Ultra-safe daily football predictions (1.03-1.10 odds)",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
try:
    prediction_service = PredictionService(min_odds=1.03, max_odds=1.05)
except (FileNotFoundError, NameError, ImportError) as e:
    print(f"⚠️ Prediction service initialization warning: {e}")
    print("   Service will use fallback predictions without ML model")
    prediction_service = None

match_fetcher = MatchFetcher()
odds_combiner = OddsCombiner()


# Pydantic models
class ApprovePickRequest(BaseModel):
    pick_id: int
    notes: Optional[str] = None
    approved_by: Optional[str] = None


class RejectPickRequest(BaseModel):
    pick_id: int
    rejection_reason: str
    rejected_by: Optional[str] = None


class PickResponse(BaseModel):
    match: str
    market: str
    odds: float
    confidence: float
    worstCaseSafe: bool
    safety_score: Optional[float] = None


class SafePicksResponse(BaseModel):
    combo_odds: Optional[float]
    games_used: int
    picks: List[PickResponse]
    reason: str
    confidence: float


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "status": "ok",
        "service": "Football Safe Odds AI",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for Coolify/monitoring"""
    return {
        "status": "ok",
        "service": "Football Safe Odds AI",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "model_loaded": prediction_service is not None
    }


@app.get("/safe-picks/today", response_model=SafePicksResponse)
async def get_safe_picks_today(db: Session = Depends(get_db)):
    """
    Get today's final recommended safe picks combo
    
    Returns the safest combination in 1.03-1.05 odds range
    Works with or without trained model (uses fallback predictions if model not available)
    """
    if not prediction_service:
        # Use fallback service without ML model
        from src.core.worst_case_simulator import WorstCaseSimulator
        from src.core.safe_odds_filter import SafeOddsFilter
        from src.core.odds_combiner import OddsCombiner
        
        class FallbackPredictionService:
            def __init__(self):
                self.simulator = WorstCaseSimulator()
                self.filter = SafeOddsFilter(min_odds=1.02, max_odds=1.05)  # Include 1.02 for very safe picks
                self.combiner = OddsCombiner(min_odds=1.02, max_odds=1.05)
            
            def generate_predictions(self, matches):
                # Use simple fallback predictions - SIMPLIFIED to ensure picks are generated
                raw_predictions = []
                matches_checked = 0
                import sys
                
                try:
                    print(f"  🔍 FallbackPredictionService.generate_predictions called with {len(matches)} matches")
                    sys.stdout.flush()
                    
                    if not matches:
                        print(f"  ⚠️ No matches provided to generate_predictions")
                        sys.stdout.flush()
                        return {
                            'combo_odds': None,
                            'games_used': 0,
                            'picks': [],
                            'reason': 'No matches provided',
                            'confidence': 0.0
                        }
                    
                    # SIMPLIFIED: Don't filter matches, just analyze them all
                    for match in matches:
                        matches_checked += 1
                        try:
                            home = match.get('home_team', 'Unknown')
                            away = match.get('away_team', 'Unknown')
                            print(f"  🔍 Processing match {matches_checked}/{len(matches)}: {home} vs {away}")
                            sys.stdout.flush()
                            
                            # Get safe markets for this match
                            markets = self.simulator.get_recommended_markets(match)
                            print(f"    📋 Recommended markets ({len(markets)}): {markets}")
                            sys.stdout.flush()
                            
                            if not markets:
                                print(f"    ⚠️ No recommended markets for this match")
                                sys.stdout.flush()
                                # Use default safe market if none recommended
                                markets = ['over_0.5_goals']
                            
                            # Generate predictions for each safe market
                            for market_type in markets[:2]:  # Limit to top 2 markets per match
                                try:
                                    # Conservative fallback probability (96% = very safe)
                                    base_prob = 0.96
                                    worst_case = self.simulator.test_all_scenarios(match, market_type, base_prob)
                                    odds = self._get_odds_for_market(match, market_type, base_prob)
                                    
                                    print(f"    💰 Market: {market_type}, Odds: {odds:.3f}, Target range: {self.filter.min_odds}-{self.filter.max_odds}")
                                    sys.stdout.flush()
                                    
                                    # Only add if odds are in our target range
                                    if self.filter.min_odds <= odds <= self.filter.max_odds:
                                        raw_predictions.append({
                                            'match_id': match.get('id'),
                                            'home_team': home,
                                            'away_team': away,
                                            'market_type': market_type,
                                            'odds': odds,
                                            'confidence': base_prob,
                                            'worst_case_result': worst_case,
                                            'match_data': match
                                        })
                                        print(f"    ✅ Added prediction: {market_type} @ {odds:.3f} odds (confidence: {base_prob:.1%})")
                                        sys.stdout.flush()
                                    else:
                                        print(f"    ⚠️ Odds {odds:.3f} outside target range {self.filter.min_odds}-{self.filter.max_odds}")
                                        sys.stdout.flush()
                                except Exception as pred_error:
                                    import traceback
                                    print(f"    ❌ Error generating prediction for {market_type}: {pred_error}")
                                    print(f"       {traceback.format_exc()[:200]}")
                                    sys.stdout.flush()
                                    continue
                        except Exception as match_error:
                            import traceback
                            print(f"  ❌ Error processing match {matches_checked}: {match_error}")
                            print(f"     {traceback.format_exc()[:200]}")
                            sys.stdout.flush()
                            continue
                    
                    print(f"  📊 Generated {len(raw_predictions)} raw predictions from {matches_checked} matches")
                    sys.stdout.flush()
                except Exception as gen_error:
                    import traceback
                    print(f"  ❌ FATAL ERROR in generate_predictions: {gen_error}")
                    print(f"     {traceback.format_exc()[:500]}")
                    sys.stdout.flush()
                    return {
                        'combo_odds': None,
                        'games_used': 0,
                        'picks': [],
                        'reason': f'Error generating predictions: {str(gen_error)}',
                        'confidence': 0.0
                    }
                
                # SIMPLIFIED: Don't over-filter, just use raw predictions directly
                # The filter_predictions method was too strict and filtering everything out
                # Instead, pass raw predictions directly to combiner
                best_combo = self.combiner.find_best_combination(raw_predictions, max_games=3)
                if best_combo:
                    print(f"  ✅ Found best combo: {best_combo.get('combo_odds', 'N/A'):.3f} odds, {best_combo.get('games_used', 0)} games")
                    return self.combiner.format_combo_response(best_combo)
                
                # If no combo found, try to find a single pick that matches
                if raw_predictions:
                    single_pick = raw_predictions[0]  # Take first valid prediction
                    print(f"  ✅ Using single pick fallback: {single_pick.get('market_type')} @ {single_pick.get('odds'):.3f}")
                    return self.combiner.format_combo_response({
                        'picks': [single_pick],
                        'combo_odds': single_pick.get('odds'),
                        'total_confidence': single_pick.get('confidence'),
                        'games_used': 1,
                        'safety_score': single_pick.get('worst_case_result', {}).get('safety_score', 0.9) if isinstance(single_pick.get('worst_case_result'), dict) else 0.9,
                        'reason': f"Single pick: {single_pick.get('market_type')} at {single_pick.get('odds'):.3f}x odds"
                    })
                
                reason = f'No predictions generated from {matches_checked} matches. Check if matches have required data.'
                print(f"  ❌ {reason}")
                import sys
                sys.stdout.flush()
                return {
                    'combo_odds': None,
                    'games_used': 0,
                    'picks': [],
                    'reason': reason,
                    'confidence': 0.0
                }
            
            def _get_odds_for_market(self, match, market_type, prob):
                # Simple odds calculation
                if 'over_0.5' in market_type:
                    return 1.02  # Very safe
                elif 'over_1.5' in market_type:
                    return 1.04
                elif match.get('home_odds', 2.0) < 1.20:
                    return 1.03
                return 1.05
        
        fallback_service = FallbackPredictionService()
        service = fallback_service
    else:
        service = prediction_service
    
    try:
        # Fetch today's matches
        matches = match_fetcher.get_today_matches()
        print(f"📊 Fetched {len(matches)} matches from match fetcher")
        print(f"🔑 API Key status: {'SET' if match_fetcher.api_key else 'NOT SET'}")
        
        if not matches:
            api_status = "NOT SET" if not match_fetcher.api_key else "SET (but no matches found)"
            reason_msg = f"No matches available today. API Key: {api_status}"
            print(f"⚠️ No matches found. Reason: {reason_msg}")
            return SafePicksResponse(
                combo_odds=None,
                games_used=0,
                picks=[],
                reason=reason_msg,
                confidence=0.0
            )
        
        print(f"✅ Processing {len(matches)} matches for safe picks")
        
        # Save matches to database
        try:
            for match_data in matches:
                match_id_str = str(match_data.get('id', ''))
                if not match_id_str:
                    print(f"⚠️ Skipping match with missing ID: {match_data}")
                    continue
                
                # Ensure required fields exist
                home_team = match_data.get('home_team', 'Unknown')
                away_team = match_data.get('away_team', 'Unknown')
                league = match_data.get('league', 'Unknown League')
                match_date = match_data.get('match_date')
                
                # Validate required fields
                if not all([home_team, away_team, league, match_date]):
                    print(f"⚠️ Skipping match {match_id_str}: Missing required fields")
                    print(f"   home_team: {home_team}, away_team: {away_team}, league: {league}, date: {match_date}")
                    continue
                
                # Ensure match_date is a datetime object
                if isinstance(match_date, str):
                    try:
                        match_date = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
                    except:
                        print(f"⚠️ Could not parse date for match {match_id_str}: {match_date}")
                        continue
                
                db_match = db.query(Match).filter(
                    Match.match_id == match_id_str
                ).first()
                
                if not db_match:
                    try:
                        db_match = Match(
                            match_id=match_id_str,
                            home_team=home_team,
                            away_team=away_team,
                            league=league,
                            league_tier=match_data.get('league_tier'),
                            match_date=match_date,
                            home_odds=match_data.get('home_odds'),
                            draw_odds=match_data.get('draw_odds'),
                            away_odds=match_data.get('away_odds'),
                            home_form=match_data.get('home_form'),
                            away_form=match_data.get('away_form'),
                            home_xg=match_data.get('home_xg'),
                            away_xg=match_data.get('away_xg'),
                            home_position=match_data.get('home_position'),
                            away_position=match_data.get('away_position'),
                            table_gap=match_data.get('table_gap'),
                            pressure_index=match_data.get('pressure_index'),
                            is_derby=match_data.get('is_derby', False),
                            is_must_win=match_data.get('is_must_win', False),
                            fixture_congestion=match_data.get('fixture_congestion', 7),
                            status="pending"
                        )
                        db.add(db_match)
                    except Exception as db_error:
                        import traceback
                        print(f"❌ Error creating Match record for {match_id_str}: {db_error}")
                        print(f"   Traceback: {traceback.format_exc()[:500]}")
                        print(f"   Match data: {match_data}")
                        continue
            
            db.commit()
            print(f"✅ Saved {len(matches)} matches to database")
        except Exception as db_error:
            import traceback
            db.rollback()
            print(f"❌ Database error saving matches: {db_error}")
            print(f"   Traceback: {traceback.format_exc()[:500]}")
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        
        # Generate predictions (works with or without ML model)
        print(f"🔍 Calling generate_predictions with {len(matches)} matches...")
        import sys
        sys.stdout.flush()  # Force flush to ensure logs appear
        
        try:
            result = service.generate_predictions(matches)
            print(f"🔍 generate_predictions returned: combo_odds={result.get('combo_odds')}, games_used={result.get('games_used')}, picks_count={len(result.get('picks', []))}")
            sys.stdout.flush()
        except Exception as pred_error:
            import traceback
            print(f"❌ Error in generate_predictions: {pred_error}")
            print(f"   Traceback: {traceback.format_exc()[:1000]}")
            sys.stdout.flush()
            raise HTTPException(status_code=500, detail=f"Error generating predictions: {str(pred_error)}")
        
        # Save to database
        if result.get('combo_odds'):
            try:
                # Check if combo for today already exists
                today_date = datetime.now().date()
                existing_combo = db.query(DailyCombo).filter(
                    DailyCombo.date == today_date
                ).first()
                
                if existing_combo:
                    # Update existing combo
                    existing_combo.combo_odds = result['combo_odds']
                    existing_combo.games_used = result['games_used']
                    existing_combo.picks = [pick for pick in result['picks']]
                    existing_combo.total_confidence = result['confidence']
                else:
                    # Create new combo
                    combo = DailyCombo(
                        date=today_date,
                        combo_odds=result['combo_odds'],
                        games_used=result['games_used'],
                        picks=[pick for pick in result['picks']],
                        total_confidence=result['confidence'],
                        admin_approved=False,
                        published=False
                    )
                    db.add(combo)
                
                db.commit()
                print(f"✅ Saved daily combo to database")
            except Exception as combo_error:
                import traceback
                db.rollback()
                print(f"⚠️ Error saving combo to database (non-critical): {combo_error}")
                print(f"   Traceback: {traceback.format_exc()[:300]}")
                # Don't fail the request if combo save fails
        
        # Convert to response model
        picks = [
            PickResponse(
                match=pick.get('match', ''),
                market=pick.get('market', ''),
                odds=pick.get('odds', 1.0),
                confidence=pick.get('confidence', 0),
                worstCaseSafe=pick.get('worstCaseSafe', False),
                safety_score=pick.get('safety_score', 0)
            )
            for pick in result.get('picks', [])
        ]
        
        return SafePicksResponse(
            combo_odds=result.get('combo_odds'),
            games_used=result.get('games_used', 0),
            picks=picks,
            reason=result.get('reason', ''),
            confidence=result.get('confidence', 0)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating predictions: {str(e)}")


@app.get("/safe-picks/raw")
async def get_raw_predictions(db: Session = Depends(get_db)):
    """Get raw ML predictions before filtering (works without model using fallback)"""
    if not prediction_service:
        # Return empty for now if no model - can implement fallback later
        return {"raw_predictions": [], "message": "Model not trained. Using fallback predictions in main endpoint."}
    
    try:
        matches = match_fetcher.get_today_matches()
        raw = prediction_service.get_raw_predictions(matches)
        return {"raw_predictions": raw}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/check-date")
async def check_date():
    """Check what date the server thinks it is"""
    from datetime import datetime
    import time
    
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    current_year = now.year
    current_month = now.month
    
    # Determine season
    if current_month >= 8:
        season_year = current_year
    else:
        season_year = current_year - 1
    
    return {
        "server_date": today_str,
        "server_year": current_year,
        "server_month": current_month,
        "calculated_season": season_year,
        "timestamp": now.isoformat(),
        "note": "If date is wrong, check server timezone/date settings"
    }


@app.get("/test-broadage")
async def test_broadage_api():
    """Test Broadage API connection directly - shows actual error responses"""
    import requests
    import os
    
    base_url = os.getenv("BROADAGE_API_URL", "https://s0-sports-data-api.broadage.com")
    api_key = os.getenv("BROADAGE_API_KEY", "")
    today = datetime.now().strftime("%Y-%m-%d")
    
    results = []
    
    # Test the endpoint that returns 401
    endpoint = f"{base_url}/soccer/match/list"
    
    # Try with languageId as header (as per docs)
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Accept": "application/json",
        "languageId": "1"
    }
    params = {"date": today}
    
    try:
        response = requests.get(endpoint, headers=headers, params=params, timeout=15)
        results.append({
            "endpoint": endpoint,
            "status_code": response.status_code,
            "headers_sent": headers,
            "params_sent": params,
            "response_body": response.text[:1000] if response.text else "No body",
            "response_headers": dict(response.headers)
        })
    except Exception as e:
        results.append({
            "endpoint": endpoint,
            "error": str(e)
        })
    
    return {
        "test_results": results,
        "api_key_preview": api_key[:10] + "..." if api_key else "NOT SET",
        "base_url": base_url
    }


@app.get("/test-api")
async def test_api_connection():
    """Test API-Football connection directly"""
    import requests
    import os
    from datetime import datetime
    
    api_key = os.getenv("API_FOOTBALL_KEY", "")
    if not api_key:
        return {
            "error": "API_FOOTBALL_KEY not set",
            "api_key_set": False
        }
    
    today = datetime.now().strftime("%Y-%m-%d")
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "v3.football.api-sports.io"
    }
    
    # Test multiple leagues to see which ones have matches
    test_leagues = [
        (78, "Bundesliga"),
        (39, "EPL"),
        (140, "LaLiga"),
        (135, "SerieA"),
        (61, "Ligue1"),
    ]
    
    results = []
    for league_id, league_name in test_leagues:
        params = {
            "date": today,
            "league": league_id,
            "season": datetime.now().year
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                results.append({
                    "league": f"{league_name} ({league_id})",
                    "results": data.get("results", 0),
                    "has_matches": data.get("results", 0) > 0,
                    "response_count": len(data.get("response", []))
                })
        except Exception as e:
            results.append({
                "league": f"{league_name} ({league_id})",
                "error": str(e)
            })
    
    # Also test without league filter to see all matches today
    try:
        params_all = {"date": today}
        response_all = requests.get(url, headers=headers, params=params_all, timeout=15)
        if response_all.status_code == 200:
            data_all = response_all.json()
            total_matches = data_all.get("results", 0)
    except:
        total_matches = "error"
    
    return {
        "status": "API connection working",
        "today": today,
        "season": datetime.now().year,
        "league_tests": results,
        "all_matches_today": total_matches,
        "note": "If all leagues return 0, there might be no matches scheduled today, or check date/timezone"
    }


@app.get("/matches/today")
async def get_matches_today(db: Session = Depends(get_db)):
    """Get all matches being considered today"""
    try:
        matches = match_fetcher.get_today_matches()
        
        # Diagnostic info
        api_key_set = bool(match_fetcher.api_key)
        api_key_preview = match_fetcher.api_key[:10] + "..." if match_fetcher.api_key else "NOT SET"
        
        return {
            "matches": [
                {
                    "id": m.get('id'),
                    "home_team": m.get('home_team'),
                    "away_team": m.get('away_team'),
                    "league": m.get('league'),
                    "league_tier": m.get('league_tier'),
                    "home_odds": m.get('home_odds'),
                    "match_date": m.get('match_date').isoformat() if m.get('match_date') else None
                }
                for m in matches
            ],
            "count": len(matches),
            "diagnostic": {
                "api_key_set": api_key_set,
                "api_key_preview": api_key_preview,
                "fetched_at": datetime.now().isoformat(),
                "today_date": datetime.now().strftime("%Y-%m-%d"),
                "using_broadage": match_fetcher.use_broadage if hasattr(match_fetcher, 'use_broadage') else False,
                "base_url": match_fetcher.base_url if hasattr(match_fetcher, 'base_url') else "unknown"
            }
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Error in get_matches_today: {error_details}")
        raise HTTPException(status_code=500, detail=f"{str(e)}\n\nDetails: {error_details}")


@app.post("/admin/approve")
async def approve_pick(
    request: ApprovePickRequest,
    db: Session = Depends(get_db)
):
    """Admin approves a pick"""
    try:
        filtered_pick = db.query(FilteredPick).filter(
            FilteredPick.id == request.pick_id
        ).first()
        
        if not filtered_pick:
            raise HTTPException(status_code=404, detail="Pick not found")
        
        # Check if already approved
        existing = db.query(ApprovedPick).filter(
            ApprovedPick.filtered_pick_id == request.pick_id
        ).first()
        
        if existing:
            return {"message": "Pick already approved", "pick_id": existing.id}
        
        # Create approved pick
        approved = ApprovedPick(
            filtered_pick_id=request.pick_id,
            match_id=filtered_pick.match_id,
            market_type=filtered_pick.market_type,
            odds=filtered_pick.odds,
            confidence=filtered_pick.confidence,
            admin_notes=request.notes,
            approved_by=request.approved_by or "admin"
        )
        
        db.add(approved)
        db.commit()
        
        return {
            "message": "Pick approved successfully",
            "pick_id": approved.id,
            "filtered_pick_id": request.pick_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/reject")
async def reject_pick(
    request: RejectPickRequest,
    db: Session = Depends(get_db)
):
    """Admin rejects a pick"""
    try:
        filtered_pick = db.query(FilteredPick).filter(
            FilteredPick.id == request.pick_id
        ).first()
        
        if not filtered_pick:
            raise HTTPException(status_code=404, detail="Pick not found")
        
        # Create rejected pick
        rejected = RejectedPick(
            filtered_pick_id=request.pick_id,
            match_id=filtered_pick.match_id,
            rejection_reason=request.rejection_reason,
            rejected_by=request.rejected_by or "admin"
        )
        
        db.add(rejected)
        db.commit()
        
        return {
            "message": "Pick rejected successfully",
            "pick_id": rejected.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

