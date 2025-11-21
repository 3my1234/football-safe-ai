# 🚀 Quick Start Guide

## Local Development Setup

### 1. Install Dependencies

```bash
cd football-safe-ai
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and configure:
nano .env
# - API_FOOTBALL_KEY: Your API-Football API key
# - FOOTBALL_AI_DATABASE_URL: PostgreSQL connection string
#   Example: postgresql://postgres:PHYSICS1234@localhost:5432/football_ai?schema=public
```

**PostgreSQL Setup Options:**

**Option 1: Create separate database on same PostgreSQL server (recommended)**
```bash
# Connect to PostgreSQL
psql -U postgres -h localhost

# Create database for Football AI
CREATE DATABASE football_ai;

# Exit
\q
```

**Option 2: Use existing Rolley database**
- Just point `FOOTBALL_AI_DATABASE_URL` to your Rolley database connection string
- Tables will be created in the same database

### 3. Initialize Database

```bash
python -m src.database.init_db
```

### 4. Train Initial Model

```bash
python -m src.models.train
```

### 5. Start API Server

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Test API

```bash
# Health check
curl http://localhost:8000/

# Get today's safe picks
curl http://localhost:8000/safe-picks/today

# Get raw predictions
curl http://localhost:8000/safe-picks/raw

# Get today's matches
curl http://localhost:8000/matches/today
```

## API Documentation

Once server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing Endpoints

### Get Safe Picks

```bash
curl http://localhost:8000/safe-picks/today
```

Response:
```json
{
  "combo_odds": 1.07,
  "games_used": 2,
  "picks": [
    {
      "match": "Arsenal vs Sheffield United",
      "market": "over_0.5_goals",
      "odds": 1.04,
      "confidence": 0.97,
      "worstCaseSafe": true,
      "safety_score": 0.95
    }
  ],
  "reason": "2-game combo: 1.07x odds with 96% confidence",
  "confidence": 0.96
}
```

### Admin Approve Pick

```bash
curl -X POST http://localhost:8000/admin/approve \
  -H "Content-Type: application/json" \
  -d '{
    "pick_id": 1,
    "notes": "Looks good",
    "approved_by": "admin"
  }'
```

### Admin Reject Pick

```bash
curl -X POST http://localhost:8000/admin/reject \
  -H "Content-Type: application/json" \
  -d '{
    "pick_id": 2,
    "rejection_reason": "Odds too low",
    "rejected_by": "admin"
  }'
```

## Docker Quick Start

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Next Steps

1. **Train Model with Real Data**: Replace sample data with real historical matches
2. **Configure API-Football**: Add your API key to fetch real match data
3. **Setup n8n**: Import workflow and configure daily automation
4. **Deploy to VPS**: Follow `DEPLOYMENT.md` for production setup

## Integration with Rolley Backend

To integrate with your existing Rolley backend:

1. Add this service as a separate microservice
2. Call `/safe-picks/today` endpoint from your admin panel
3. Store approved picks in your main database
4. Display on user dashboard when admin publishes

