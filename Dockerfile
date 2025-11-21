# Multi-stage build for Football Safe Odds AI
# FastAPI application with PostgreSQL support
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# No runtime dependencies needed - using Python for health check
RUN apt-get update && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create non-root user first (before copying)
RUN useradd -m -u 1001 footballai

# Copy Python packages from builder to a location accessible to all users
COPY --from=builder /root/.local /usr/local

# Copy application code with proper ownership
COPY --chown=footballai:footballai . .

# Make sure Python packages are in PATH
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONPATH=/app

# Switch to non-root user
USER footballai

# Expose port (Coolify will map this)
# Using port 8000 - different from friend's services (3000, 3001, 3002)
EXPOSE 8000

# Health check (Coolify will also use this)
# Note: curl might not be available, use Python instead
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run application
# Database initialization happens at startup in main.py
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

