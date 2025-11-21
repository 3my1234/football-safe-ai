# 🚀 Quick Database Setup for Football AI

Since you don't have `psql` locally, here are the **easiest** options:

## ⚡ Option 1: Use Same Database as Rolley (EASIEST - No Setup Needed!)

**Just use your existing Rolley database connection:**

In `football-safe-ai/.env`:
```env
FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/rolley?schema=public
```

**That's it!** The Football AI tables will be created in the same database. They have different names so they won't conflict.

✅ **No need to create new database**
✅ **Uses existing connection**
✅ **Works immediately**

## ⚡ Option 2: Create Database via Backend Prisma

**If you want a separate database:**

1. **From your backend directory**, run:
```powershell
cd backend
npx ts-node ../football-safe-ai/scripts/create_db_via_backend.ts
```

This uses your existing Prisma connection to create the new database.

## ⚡ Option 3: Use Docker PostgreSQL (if available)

**If PostgreSQL is in Docker:**

```powershell
# Find PostgreSQL container
docker ps | findstr postgres

# Create database (replace <container-name>)
docker exec -it <postgres-container-name> psql -U postgres -c "CREATE DATABASE football_ai;"
```

## ⚡ Option 4: Use pgAdmin or DBeaver (GUI)

**Install a PostgreSQL GUI client:**
- **pgAdmin**: https://www.pgadmin.org/download/
- **DBeaver**: https://dbeaver.io/download/

Then:
1. Connect using: `postgresql://postgres:PHYSICS1234@localhost:5432/postgres`
2. Right-click → Create → Database
3. Name: `football_ai`
4. Click Save

## ⚡ Option 5: If PostgreSQL is on Coolify/Railway

**Get connection string from your deployment dashboard:**

1. Go to Coolify/Railway dashboard
2. Find PostgreSQL service
3. Copy connection string
4. Create database via their admin panel or GUI client
5. Use connection string in `.env`

## 🎯 Recommended: Option 1 (Use Same Database)

**For fastest setup, just use:**

```env
# football-safe-ai/.env
FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/rolley?schema=public
```

Then initialize tables:
```powershell
cd football-safe-ai
# Install dependencies first if needed
pip install psycopg2-binary sqlalchemy
python -m src.database.init_db
```

**Tables created:**
- `matches`
- `raw_predictions`
- `filtered_picks`
- `approved_picks`
- `rejected_picks`
- `daily_combos`

These won't conflict with your Rolley tables.

---

**After database is set up**, initialize tables:
```powershell
cd football-safe-ai
python -m src.database.init_db
```


