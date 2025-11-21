# 🗄️ Create Football AI Database Guide

Since you don't have `psql` locally, here are options based on where your PostgreSQL is:

## Option 1: PostgreSQL on Coolify/Railway (Remote)

**If your PostgreSQL is on Coolify or Railway:**

1. **Get connection details** from your deployment dashboard
2. **Use any PostgreSQL client:**
   - **pgAdmin** (Windows GUI): https://www.pgadmin.org/download/
   - **DBeaver** (Cross-platform): https://dbeaver.io/download/
   - **TablePlus** (Mac/Windows): https://tableplus.com/
   - **VS Code Extension**: "PostgreSQL" by Chris Kolkman

3. **Connect and create database:**
   ```sql
   CREATE DATABASE football_ai;
   ```

4. **Set environment variable:**
   ```env
   FOOTBALL_AI_DATABASE_URL=postgresql://user:password@your-remote-host:5432/football_ai?schema=public
   ```

## Option 2: PostgreSQL in Docker

**If PostgreSQL is running in Docker locally:**

```powershell
# Find PostgreSQL container
docker ps -a | findstr postgres

# Create database (replace <container-name> with actual name)
docker exec -it <postgres-container-name> psql -U postgres -c "CREATE DATABASE football_ai;"

# Example if container is named "rolley-postgres":
docker exec -it rolley-postgres psql -U postgres -c "CREATE DATABASE football_ai;"
```

## Option 3: Use Same Database as Rolley (Easiest)

**Skip creating new database - use existing Rolley database:**

Just use the same connection string but different schema or same schema:

```env
# Option A: Same database, same schema (tables will have different names)
FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/rolley?schema=public

# Option B: Same database, different schema (recommended)
# First create schema:
# Then use:
FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/rolley?schema=football_ai
```

## Option 4: Use Backend to Create Database

**If your backend can access PostgreSQL, create it via backend:**

1. **Connect to your backend's PostgreSQL**
2. **Use your backend's Prisma or SQL tools** to run:
   ```sql
   CREATE DATABASE football_ai;
   ```

## Option 5: Initialize Database on First Run

**The Football AI service will try to create tables automatically:**

1. **Just set the connection string** pointing to your existing PostgreSQL
2. **The `init_db.py` script will create tables** (but NOT the database itself)
3. **Database must exist first**, then tables are created automatically

## Quick Check: Where is Your PostgreSQL?

Run this to check:

```powershell
# Check for local PostgreSQL
netstat -an | findstr "5432"

# Check Docker containers
docker ps | findstr postgres

# Check if it's a service
Get-Service | findstr postgres
```

## Recommended Setup

**For Rolley integration, I recommend:**

1. **Use the same PostgreSQL server** (your existing one)
2. **Create a separate database** called `football_ai`
3. **Use connection string:**
   ```env
   FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/football_ai?schema=public
   ```

**If PostgreSQL is on Coolify/Railway:**
- Get the connection string from your dashboard
- Create database via their admin panel or pgAdmin
- Use that connection string in `.env`

## After Creating Database

Once database exists, initialize tables:

```powershell
cd football-safe-ai
python -m src.database.init_db
```

Or the Football AI service will auto-create tables on first run.

