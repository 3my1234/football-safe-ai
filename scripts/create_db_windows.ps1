# PowerShell script to create Football AI database
# For Windows users without psql command

Write-Host "🚀 Creating Football AI database..." -ForegroundColor Green

# Database connection details (update these if different)
$DB_HOST = if ($env:DB_HOST) { $env:DB_HOST } else { "localhost" }
$DB_PORT = if ($env:DB_PORT) { $env:DB_PORT } else { "5432" }
$DB_USER = if ($env:DB_USER) { $env:DB_USER } else { "postgres" }
$DB_PASSWORD = if ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { "PHYSICS1234" }
$DB_NAME = if ($env:FOOTBALL_AI_DB_NAME) { $env:FOOTBALL_AI_DB_NAME } else { "football_ai" }

Write-Host "Using PostgreSQL connection:" -ForegroundColor Yellow
Write-Host "  Host: $DB_HOST"
Write-Host "  Port: $DB_PORT"
Write-Host "  User: $DB_USER"
Write-Host "  Database: $DB_NAME"
Write-Host ""

# Option 1: Use Python script (if psycopg2 is installed)
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "Creating database using Python..." -ForegroundColor Cyan
    python scripts/create_database.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database created successfully!" -ForegroundColor Green
        exit 0
    }
}

# Option 2: If PostgreSQL is in Docker, use docker exec
Write-Host "Trying Docker method..." -ForegroundColor Cyan

# Check if PostgreSQL container exists
$postgresContainer = docker ps -a --filter "ancestor=postgres" --format "{{.Names}}" | Select-Object -First 1

if ($postgresContainer) {
    Write-Host "Found PostgreSQL container: $postgresContainer" -ForegroundColor Yellow
    
    # Try to create database via Docker
    docker exec -i $postgresContainer psql -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME;" 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Database created via Docker!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📝 Database URL for .env file:" -ForegroundColor Cyan
        Write-Host "FOOTBALL_AI_DATABASE_URL=postgresql://$DB_USER`:$DB_PASSWORD@$DB_HOST`:$DB_PORT/$DB_NAME?schema=public" -ForegroundColor White
        exit 0
    } else {
        Write-Host "⚠️ Could not create database via Docker. Container may not be running or credentials may be wrong." -ForegroundColor Yellow
    }
}

# Option 3: Manual instructions
Write-Host ""
Write-Host "⚠️ Could not create database automatically." -ForegroundColor Yellow
Write-Host ""
Write-Host "Please create the database manually:" -ForegroundColor Cyan
Write-Host ""
Write-Host "Option A: If PostgreSQL is in Docker:" -ForegroundColor White
Write-Host "  docker exec -it <postgres-container-name> psql -U postgres" -ForegroundColor Gray
Write-Host "  CREATE DATABASE football_ai;" -ForegroundColor Gray
Write-Host "  \q" -ForegroundColor Gray
Write-Host ""
Write-Host "Option B: If using Coolify/Railway remote PostgreSQL:" -ForegroundColor White
Write-Host "  1. Get connection string from your deployment dashboard" -ForegroundColor Gray
Write-Host "  2. Connect using any PostgreSQL client (pgAdmin, DBeaver, etc.)" -ForegroundColor Gray
Write-Host "  3. Run: CREATE DATABASE football_ai;" -ForegroundColor Gray
Write-Host ""
Write-Host "Option C: Install psql locally:" -ForegroundColor White
Write-Host "  Download PostgreSQL from: https://www.postgresql.org/download/windows/" -ForegroundColor Gray
Write-Host "  Or use Chocolatey: choco install postgresql" -ForegroundColor Gray
Write-Host ""
Write-Host "Then set in .env file:" -ForegroundColor Cyan
Write-Host "FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/football_ai?schema=public" -ForegroundColor White


