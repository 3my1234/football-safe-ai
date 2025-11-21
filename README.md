# ⚽ Football Safe Odds AI Predictor (1.03-1.10)

Ultra-safe daily football predictions using ML models, worst-case simulation, and risk-based filtering.

## 🎯 Goal

Produce the safest possible daily football picks in the 1.03-1.10 odds range, prioritizing safety over high returns.

## 🏗️ Architecture

- **ML Model**: XGBoost/RandomForest for match outcome prediction
- **Worst-Case Simulator**: Stress tests predictions against dangerous scenarios
- **Safe Odds Filter**: Filters matches by risk level and league stability
- **Odds Combiner**: Combines picks to achieve 1.03-1.10 total odds
- **FastAPI Backend**: REST API for predictions and admin management
- **PostgreSQL Database**: Stores matches, predictions, and admin decisions (uses same DB as Rolley backend)
- **n8n Integration**: Automated daily workflows
- **Docker Deployment**: Containerized for VPS deployment

## 📦 Installation

### Requirements

- Python 3.10+
- Docker & Docker Compose (optional)
- n8n (for automation)

### Setup

```bash
cd football-safe-ai
pip install -r requirements.txt
python -m src.database.init_db  # Initialize database
python -m src.models.train  # Train initial ML model
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Docker Setup

```bash
docker-compose up -d
```

## 🚀 Usage

### Get Today's Safe Picks

```bash
curl http://localhost:8000/safe-picks/today
```

### Admin Approve Pick

```bash
curl -X POST http://localhost:8000/admin/approve \
  -H "Content-Type: application/json" \
  -d '{"pick_id": 123, "notes": "Looks good"}'
```

## 📊 API Endpoints

- `GET /safe-picks/today` - Final recommended combo
- `GET /safe-picks/raw` - Raw model output before filtering
- `POST /admin/approve` - Admin approves pick
- `POST /admin/reject` - Admin rejects pick
- `GET /matches/today` - All matches being considered

## 🔧 Configuration

Set environment variables in `.env`:

```env
API_FOOTBALL_KEY=your_api_key
# Option 1: Use existing Rolley PostgreSQL (recommended)
FOOTBALL_AI_DATABASE_URL=postgresql://postgres:password@localhost:5432/football_ai?schema=public
# Option 2: Use same PostgreSQL server, different database
# DATABASE_URL=postgresql://postgres:password@localhost:5432/rolley?schema=public
MIN_ODDS=1.03
MAX_ODDS=1.10
MODEL_PATH=./models/football_model.pkl
```

## 📈 Model Training

```bash
python -m src.models.train --data-path ./data --epochs 100
```

## 🐳 Deployment

See `DEPLOYMENT.md` for VPS setup instructions (Contabo, Google Cloud, etc.)

