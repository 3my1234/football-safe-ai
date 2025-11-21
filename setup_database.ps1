# PowerShell script to setup Football AI database
# Option 1: Use same database as Rolley (EASIEST)

Write-Host "🚀 Setting up Football AI database..." -ForegroundColor Green
Write-Host ""

Write-Host "Option 1: Use Same Database as Rolley (RECOMMENDED)" -ForegroundColor Cyan
Write-Host "This will create tables in your existing 'rolley' database" -ForegroundColor Yellow
Write-Host ""

# Check if .env file exists
if (Test-Path ".env") {
    Write-Host "✅ .env file exists" -ForegroundColor Green
} else {
    Write-Host "📝 Creating .env file..." -ForegroundColor Yellow
    Copy-Item "env.example" ".env"
    
    # Update database URL to use same database
    $content = Get-Content .env
    $content = $content -replace 'FOOTBALL_AI_DATABASE_URL=.*', 'FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/rolley?schema=public'
    $content | Set-Content .env
    
    Write-Host "✅ .env file created with same database connection" -ForegroundColor Green
}

Write-Host ""
Write-Host "📝 Your Football AI will use the same PostgreSQL database as Rolley backend" -ForegroundColor Cyan
Write-Host "   Database: rolley" -ForegroundColor White
Write-Host "   Tables will be created: matches, raw_predictions, filtered_picks, etc." -ForegroundColor White
Write-Host ""
Write-Host "✅ No need to create a new database!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Install dependencies: pip install -r requirements.txt" -ForegroundColor White
Write-Host "2. Initialize tables: python -m src.database.init_db" -ForegroundColor White
Write-Host "3. Start service: uvicorn src.api.main:app --host 0.0.0.0 --port 8000" -ForegroundColor White
