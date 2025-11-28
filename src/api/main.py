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
                self.filter = SafeOddsFilter(min_odds=1.03, max_odds=1.05)
                self.combiner = OddsCombiner(min_odds=1.03, max_odds=1.05)
            
            def generate_predictions(self, matches):
                # Use simple fallback predictions
                raw_predictions = []
                for match in matches:
                    if not self.filter.filter_match(match):
                        continue
                    markets = self.simulator.get_recommended_markets(match)
                    for market_type in markets:
                        # Conservative fallback probability
                        base_prob = 0.96  # 96% confidence for safe picks
                        worst_case = self.simulator.test_all_scenarios(match, market_type, base_prob)
                        odds = self._get_odds_for_market(match, market_type, base_prob)
                        if 1.03 <= odds <= 1.05:
                            raw_predictions.append({
                                'match_id': match.get('id'),
                                'home_team': match.get('home_team'),
                                'away_team': match.get('away_team'),
                                'market_type': market_type,
                                'odds': odds,
                                'confidence': base_prob,
                                'worst_case_result': worst_case,
                                'match_data': match
                            })
                
                filtered = self.filter.filter_predictions(matches, raw_predictions)
                best_combo = self.combiner.find_best_combination(filtered, max_games=3)
                if best_combo:
                    return self.combiner.format_combo_response(best_combo)
                return {
                    'combo_odds': None,
                    'games_used': 0,
                    'picks': [],
                    'reason': 'No safe combination found in target odds range (1.03-1.05)',
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
        
        if not matches:
            print("⚠️ No matches found. Returning empty response.")
            return SafePicksResponse(
                combo_odds=None,
                games_used=0,
                picks=[],
                reason="No matches available today",
                confidence=0.0
            )
        
        print(f"✅ Processing {len(matches)} matches for safe picks")
        
        # Save matches to database
        for match_data in matches:
            db_match = db.query(Match).filter(
                Match.match_id == match_data.get('id')
            ).first()
            
            if not db_match:
                db_match = Match(
                    match_id=match_data.get('id'),
                    home_team=match_data.get('home_team'),
                    away_team=match_data.get('away_team'),
                    league=match_data.get('league'),
                    league_tier=match_data.get('league_tier'),
                    match_date=match_data.get('match_date'),
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
        
        db.commit()
        
        # Generate predictions (works with or without ML model)
        result = service.generate_predictions(matches)
        
        # Save to database
        if result.get('combo_odds'):
            combo = DailyCombo(
                date=datetime.now().date(),
                combo_odds=result['combo_odds'],
                games_used=result['games_used'],
                picks=[pick for pick in result['picks']],
                total_confidence=result['confidence'],
                admin_approved=False,
                published=False
            )
            db.add(combo)
            db.commit()
        
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


@app.get("/matches/today")
async def get_matches_today(db: Session = Depends(get_db)):
    """Get all matches being considered today"""
    try:
        matches = match_fetcher.get_today_matches()
        return {
            "matches": [
                {
                    "id": m.get('id'),
                    "home_team": m.get('home_team'),
                    "away_team": m.get('away_team'),
                    "league": m.get('league'),
                    "match_date": m.get('match_date').isoformat() if m.get('match_date') else None
                }
                for m in matches
            ],
            "count": len(matches)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

