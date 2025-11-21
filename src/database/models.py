"""
Database models for Football Safe Odds AI
"""
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Match(Base):
    """Football matches being considered"""
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True)
    match_id = Column(String, unique=True, nullable=False)
    home_team = Column(String, nullable=False)
    away_team = Column(String, nullable=False)
    league = Column(String, nullable=False)
    league_tier = Column(String)  # EPL, LaLiga, etc.
    match_date = Column(DateTime, nullable=False)
    match_time = Column(String)
    home_odds = Column(Float)
    draw_odds = Column(Float)
    away_odds = Column(Float)
    
    # Team performance stats
    home_form = Column(JSON)  # Last 5 matches stats
    away_form = Column(JSON)
    home_xg = Column(Float)
    away_xg = Column(Float)
    home_position = Column(Integer)
    away_position = Column(Integer)
    table_gap = Column(Integer)
    
    # Context
    is_derby = Column(Boolean, default=False)
    is_must_win = Column(Boolean, default=False)
    pressure_index = Column(Float)  # 0-1 scale
    fixture_congestion = Column(Integer)  # Days since last match
    
    # Status
    status = Column(String, default="pending")  # pending, analyzed, filtered, approved, rejected
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class RawPrediction(Base):
    """Raw ML model predictions before filtering"""
    __tablename__ = "raw_predictions"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, nullable=False)  # FK to matches
    market_type = Column(String, nullable=False)  # over_0.5, home_win, etc.
    predicted_probability = Column(Float, nullable=False)  # 0-1
    confidence_score = Column(Float)  # 0-1
    odds = Column(Float)
    worst_case_safe = Column(Boolean, default=False)
    ml_features = Column(JSON)  # Features used by ML model
    created_at = Column(DateTime, default=func.now())


class FilteredPick(Base):
    """Picks that passed the safe odds filter"""
    __tablename__ = "filtered_picks"

    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, nullable=False)
    market_type = Column(String, nullable=False)
    odds = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    risk_score = Column(Float)  # Lower = safer
    worst_case_result = Column(JSON)  # Worst-case simulation results
    filter_reason = Column(Text)
    created_at = Column(DateTime, default=func.now())


class ApprovedPick(Base):
    """Admin-approved picks ready for combination"""
    __tablename__ = "approved_picks"

    id = Column(Integer, primary_key=True)
    filtered_pick_id = Column(Integer, nullable=False)  # FK to filtered_picks
    match_id = Column(Integer, nullable=False)
    market_type = Column(String, nullable=False)
    odds = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    admin_notes = Column(Text)
    approved_by = Column(String)
    approved_at = Column(DateTime, default=func.now())


class RejectedPick(Base):
    """Admin-rejected picks"""
    __tablename__ = "rejected_picks"

    id = Column(Integer, primary_key=True)
    filtered_pick_id = Column(Integer, nullable=False)
    match_id = Column(Integer, nullable=False)
    rejection_reason = Column(Text)
    rejected_by = Column(String)
    rejected_at = Column(DateTime, default=func.now())


class DailyCombo(Base):
    """Final daily safe odds combo"""
    __tablename__ = "daily_combos"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, unique=True)
    combo_odds = Column(Float, nullable=False)
    games_used = Column(Integer, nullable=False)
    picks = Column(JSON, nullable=False)  # List of pick IDs
    total_confidence = Column(Float)
    admin_approved = Column(Boolean, default=False)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())

