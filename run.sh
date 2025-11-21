#!/bin/bash
# Quick start script for Football Safe Odds AI

echo "🚀 Starting Football Safe Odds AI..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Initialize database
echo "Initializing database..."
python -m src.database.init_db

# Train model (if not exists)
if [ ! -f "models/football_model.pkl" ]; then
    echo "Training model..."
    python -m src.models.train
else
    echo "Model already exists, skipping training..."
fi

# Start server
echo "Starting API server..."
echo "API available at: http://localhost:8000"
echo "Docs available at: http://localhost:8000/docs"
echo ""
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

