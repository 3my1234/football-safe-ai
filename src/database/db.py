"""
Database connection and session management
PostgreSQL connection for Football Safe Odds AI
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from typing import Generator
import os
from pathlib import Path

# Database URL - Use PostgreSQL from environment or default to Rolley's database
# Can use same PostgreSQL server with different database name
DATABASE_URL = os.getenv(
    "FOOTBALL_AI_DATABASE_URL",  # Specific URL for Football AI
    os.getenv(
        "DATABASE_URL",  # Fallback to main Rolley database URL
        "postgresql://postgres:PHYSICS1234@localhost:5432/football_ai"
    )
)

# Remove schema parameter from connection string (psycopg2 doesn't support it)
# SQLAlchemy handles schema separately
if "?schema=" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("?schema=")[0]
elif "&schema=" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("&schema=")[0]

# If using same database server, append football_ai database name
# Format: postgresql://user:pass@host:port/database
if DATABASE_URL.startswith("postgresql://"):
    # Already PostgreSQL - use as is
    pass
elif DATABASE_URL.startswith("sqlite"):
    # Convert SQLite to PostgreSQL format (for migration)
    # Use default PostgreSQL connection
    DATABASE_URL = "postgresql://postgres:PHYSICS1234@localhost:5432/football_ai"
else:
    # Assume PostgreSQL format already
    pass

# Sync engine for initialization (PostgreSQL)
engine = create_engine(
    DATABASE_URL, 
    echo=False,
    pool_pre_ping=True,  # Reconnect on connection loss
    pool_size=5,
    max_overflow=10
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine for async operations
async_database_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
try:
    async_engine = create_async_engine(async_database_url, echo=False)
    AsyncSessionLocal = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
except Exception:
    # asyncpg not installed, skip async engine
    async_engine = None
    AsyncSessionLocal = None


def get_db() -> Generator[Session, None, None]:
    """Get database session (sync)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncSession:
    """Get async database session"""
    async with AsyncSessionLocal() as session:
        yield session

