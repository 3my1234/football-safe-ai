# Football Safe Odds AI - Coolify Deployment Guide

## Overview
This guide covers deploying the Football Safe Odds AI service to Coolify.

## Port Configuration
- **Service Port**: 8000 (inside container)
- **Public Port**: Coolify will assign automatically
- **No Conflicts**: Port 8000 is different from friend's services (3000, 3001, 3002)

## Database Setup

The Football AI uses its own database on the same PostgreSQL server.

### Database Details
- **Database Name**: `football_ai` (already created in your PostgreSQL instance)
- **Database Host**: `ao0coggok8g8ccko4wscccwg` (same as Rolley backend)
- **Database Port**: 5432
- **Username**: `postgres`
- **Password**: `PHYSICS1234`

### Database Connection String
```
postgresql://postgres:PHYSICS1234@ao0coggok8g8ccko4wscccwg:5432/football_ai
```

## Deployment Steps

### 1. Git Setup (If not already done)

The Football AI needs to be in a Git repository for Coolify deployment.

**Option A: Create new GitHub repository**
```bash
cd football-safe-ai
git init
git add .
git commit -m "Initial commit - Football Safe Odds AI"
git branch -M main
# Create repository on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/football-safe-ai.git
git push -u origin main
```

**Option B: Add to existing monorepo**
```bash
# If you have a monorepo, add this directory to it
```

### 2. Create Application in Coolify

1. Go to **Rolley (testing phase)** project in Coolify
2. Click **Resources** → **+ New** → **Application**
3. Select **Git Repository**
4. Enter repository URL: `https://github.com/YOUR_USERNAME/football-safe-ai.git`
5. Select branch: `main`
6. Build Pack: **Dockerfile**
7. Port: `8000`

### 3. Environment Variables

Add these environment variables in Coolify:

#### Required:
- **FOOTBALL_AI_DATABASE_URL**: `postgresql://postgres:PHYSICS1234@ao0coggok8g8ccko4wscccwg:5432/football_ai`
- **API_FOOTBALL_KEY**: Your API-Football API key

#### Optional:
- **MIN_ODDS**: `1.03` (default)
- **MAX_ODDS**: `1.10` (default)
- **MODEL_PATH**: `./models/football_model.pkl` (default)

### 4. Database Initialization

The database tables will be created automatically on startup (similar to the backend).

The `init_database()` function runs when the app starts and:
- Checks if the `football_ai` database exists (creates if not)
- Creates all required tables
- Verifies connection

### 5. Deployment

1. Click **Deploy** in Coolify
2. Wait for build to complete
3. Check logs to verify:
   - `🔄 Initializing database schema...`
   - `✅ Database schema initialized successfully`
   - `✅ Connected to existing database`
   - Service running on port 8000

## Health Check

The service has a `/health` endpoint that returns:
```json
{
  "status": "ok",
  "service": "Football Safe Odds AI",
  "version": "1.0.0",
  "timestamp": "2025-11-21T...",
  "model_loaded": true/false
}
```

## API Endpoints

- `GET /health` - Health check
- `GET /safe-picks/today` - Get today's safe picks
- `GET /safe-picks/raw` - Get raw ML predictions
- `GET /matches/today` - Get today's matches
- `POST /admin/approve` - Approve a pick
- `POST /admin/reject` - Reject a pick

## Verification

After deployment, check:
1. **Logs**: Database initialization should succeed
2. **Health Check**: Visit `/health` endpoint
3. **Database**: Verify tables created in `football_ai` database

## Troubleshooting

### Database Connection Issues
- Verify `FOOTBALL_AI_DATABASE_URL` is correct
- Ensure database `football_ai` exists
- Check PostgreSQL container is running

### Model Not Found
- Model will be trained on first prediction request
- Or train manually: `python -m src.models.train`

### Port Conflicts
- Port 8000 should not conflict with friend's services
- If issues occur, update Dockerfile `EXPOSE` and Coolify port mapping

## Next Steps

After deployment:
1. Test the `/health` endpoint
2. Verify database tables are created
3. Test prediction endpoint: `/safe-picks/today`
4. Connect to Rolley backend for integration

