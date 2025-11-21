"""
Create Football AI database in PostgreSQL
Works without psql command line tool
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
import sys

def create_database():
    """Create football_ai database in PostgreSQL"""
    
    # Get connection details from environment or use defaults
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "PHYSICS1234")
    db_name = os.getenv("FOOTBALL_AI_DB_NAME", "football_ai")
    
    print(f"Connecting to PostgreSQL at {db_host}:{db_port}...")
    
    try:
        # Connect to PostgreSQL server (default 'postgres' database)
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database="postgres"  # Connect to default database first
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        exists = cursor.fetchone()
        
        if exists:
            print(f"✅ Database '{db_name}' already exists")
        else:
            # Create database
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"✅ Created database: {db_name}")
        
        cursor.close()
        conn.close()
        
        # Verify connection to new database
        test_conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )
        test_conn.close()
        print(f"✅ Successfully connected to database: {db_name}")
        
        print(f"\n📝 Database URL for .env file:")
        print(f"FOOTBALL_AI_DATABASE_URL=postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?schema=public")
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check your database credentials")
        print("3. If using Docker, use: docker exec -it <postgres_container> psql -U postgres")
        print("4. If using remote server (Coolify/Railway), use your deployment's connection string")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_database()


