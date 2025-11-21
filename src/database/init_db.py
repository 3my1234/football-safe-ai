"""
Initialize database and create tables
PostgreSQL database initialization for Football Safe Odds AI
"""
from sqlalchemy import create_engine, text
from src.database.models import Base
from src.database.db import DATABASE_URL
import os
from pathlib import Path

def init_database():
    """Create all database tables in PostgreSQL"""
    # Parse database URL to get database name
    # Format: postgresql://user:pass@host:port/dbname
    
    # Check if database exists, create if not
    # Parse connection string
    if "postgresql://" in DATABASE_URL:
        # Extract database name from URL
        db_parts = DATABASE_URL.split("/")
        if len(db_parts) > 3:
            db_name = db_parts[-1].split("?")[0]  # Remove query params
            
            # Connect to postgres database to create new database if needed
            admin_url = DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
            admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
            
            try:
                # Check if database exists
                with admin_engine.connect() as conn:
                    result = conn.execute(
                        text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
                    )
                    exists = result.fetchone()
                    
                    if not exists:
                        # Create database
                        conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                        print(f"✅ Created database: {db_name}")
                    else:
                        print(f"✅ Database already exists: {db_name}")
            except Exception as e:
                print(f"⚠️ Could not check/create database (may already exist): {e}")
            finally:
                admin_engine.dispose()
    
    # Create tables in the database
    engine = create_engine(DATABASE_URL, echo=True)
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database tables initialized at: {DATABASE_URL}")


if __name__ == "__main__":
    init_database()

