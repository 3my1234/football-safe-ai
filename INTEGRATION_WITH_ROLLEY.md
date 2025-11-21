# 🔗 Integration with Rolley Backend

## Using Same PostgreSQL Database

The Football Safe Odds AI can use the same PostgreSQL server as your Rolley backend.

## Setup Options

### Option 1: Separate Database on Same Server (Recommended)

**Benefits:**
- Isolated data (easier to manage)
- Can backup separately
- Clear separation of concerns

**Setup:**
```bash
# Connect to your Rolley PostgreSQL
psql -U postgres -h localhost

# Create new database for Football AI
CREATE DATABASE football_ai;

# Exit
\q
```

**Environment Variable:**
```env
FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/football_ai?schema=public
```

### Option 2: Same Database, Different Schema

**Benefits:**
- Single database connection
- Shared connection pool
- Unified backup

**Setup:**
```bash
# Connect to PostgreSQL
psql -U postgres -h localhost -d rolley

# Create schema for Football AI
CREATE SCHEMA IF NOT EXISTS football_ai;
```

**Environment Variable:**
```env
FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/rolley?schema=football_ai
```

### Option 3: Same Database and Schema

**Benefits:**
- Unified database
- Easy queries across systems

**Setup:**
```bash
# Just use the same connection string as Rolley
```

**Environment Variable:**
```env
# Use your existing Rolley database URL
FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/rolley?schema=public
```

## Integration with Rolley Admin Panel

### Step 1: Deploy Football AI Service

Deploy the Football Safe Odds AI service to your VPS or run it alongside your Rolley backend.

### Step 2: Add Endpoint to Rolley Backend

In your Rolley backend, add a service call to fetch safe picks:

```typescript
// backend/src/admin/admin.service.ts

async getFootballAIPredictions() {
  const response = await fetch('http://localhost:8000/safe-picks/today');
  return await response.json();
}
```

### Step 3: Display in Admin Review Page

Show Football AI predictions in your admin review dashboard alongside manual predictions.

### Step 4: Approve and Publish

When admin approves Football AI picks, store them in your main `DailyEvent` table and publish to users.

## Connection from Docker

If Football AI runs in Docker but needs to connect to host PostgreSQL:

```yaml
# docker-compose.yml
services:
  football-ai:
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@host.docker.internal:5432/football_ai
```

## Connection from Same VPS

If both services run on the same VPS:

```env
# Use localhost or 127.0.0.1
FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/football_ai?schema=public
```

## Testing Connection

```bash
# Test PostgreSQL connection
python -c "from src.database.db import engine; print(engine.connect()); print('✅ Connected!')"

# Initialize tables
python -m src.database.init_db
```

## Recommended Setup

**For Production:**
- Use **Option 1** (separate database) for better isolation
- Deploy Football AI as separate service on same VPS
- Use n8n to fetch predictions daily
- Integrate with Rolley admin panel for approval

**For Development:**
- Use **Option 3** (same database) for simplicity
- Run Football AI locally on port 8000
- Test integration with Rolley backend

