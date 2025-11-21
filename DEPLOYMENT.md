# 🚀 Deployment Guide - Football Safe Odds AI

## VPS Deployment (Contabo / Google Cloud / Any Ubuntu Server)

### Prerequisites

- Ubuntu 20.04+ or similar Linux distribution
- Docker & Docker Compose installed
- Domain name (optional, for Nginx reverse proxy)
- API-Football API key

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose -y

# Add user to docker group (optional)
sudo usermod -aG docker $USER
```

### Step 2: Clone/Upload Project

```bash
# Create project directory
mkdir -p ~/football-safe-ai
cd ~/football-safe-ai

# Upload files or clone from Git
# Then navigate to project directory
cd football-safe-ai
```

### Step 3: Configure Environment

```bash
# Create .env file
# Option 1: Use existing Rolley PostgreSQL (recommended)
cat > .env << EOF
API_FOOTBALL_KEY=your_api_football_key_here
# Use same PostgreSQL server, different database
FOOTBALL_AI_DATABASE_URL=postgresql://postgres:PHYSICS1234@localhost:5432/football_ai?schema=public
MIN_ODDS=1.03
MAX_ODDS=1.10
MODEL_PATH=./models/football_model.pkl
NODE_ENV=production
EOF

# Option 2: Use existing Rolley database connection
# FOOTBALL_AI_DATABASE_URL=postgresql://postgres:password@localhost:5432/rolley?schema=public
```

### Step 4: Build and Run

```bash
# Build Docker image
docker-compose build

# Initialize database
docker-compose run --rm football-ai python -m src.database.init_db

# Train model (if needed)
docker-compose run --rm football-ai python -m src.models.train

# Start service
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Step 5: Setup Nginx Reverse Proxy (Optional)

```bash
# Install Nginx
sudo apt install nginx -y

# Create Nginx config
sudo nano /etc/nginx/sites-available/football-ai
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/football-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Step 6: Firewall Configuration

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow SSH (IMPORTANT!)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable
```

### Step 7: SSL Certificate (Optional but Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is set up automatically
```

## Google Cloud 90-Day Free Trial Setup

1. **Create VM Instance:**
   - Go to Google Cloud Console
   - Compute Engine → VM Instances → Create
   - Choose: e2-micro (free tier eligible)
   - OS: Ubuntu 20.04 LTS
   - Allow HTTP/HTTPS traffic

2. **SSH into Instance:**
   ```bash
   gcloud compute ssh instance-name --zone=us-central1-a
   ```

3. **Follow Steps 1-7 above**

## Contabo VPS Setup

1. **Order VPS:**
   - Choose Ubuntu 20.04
   - Minimum 2GB RAM recommended

2. **SSH into Server:**
   ```bash
   ssh root@your-server-ip
   ```

3. **Follow Steps 1-7 above**

## Testing Deployment

```bash
# Test API endpoint
curl http://localhost:8000/

# Test safe picks endpoint
curl http://localhost:8000/safe-picks/today

# Test from remote (replace with your IP/domain)
curl http://your-server-ip:8000/safe-picks/today
```

## Monitoring

```bash
# View logs
docker-compose logs -f football-ai

# Check container status
docker-compose ps

# Restart service
docker-compose restart

# Stop service
docker-compose down

# Update and rebuild
git pull  # If using Git
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs football-ai

# Check if port is in use
sudo netstat -tulpn | grep 8000
```

### Database issues
```bash
# Reinitialize database (creates tables if not exist)
docker-compose run --rm football-ai python -m src.database.init_db

# Or manually connect to PostgreSQL and create database:
psql -U postgres -h localhost
CREATE DATABASE football_ai;
\q
```

### Model not found
```bash
# Train model
docker-compose run --rm football-ai python -m src.models.train
```

## n8n Integration

1. **Install n8n:**
   ```bash
   npm install -g n8n
   n8n start
   ```

2. **Import Workflow:**
   - Go to http://localhost:5678
   - Import `n8n-workflows/daily-safe-picks.json`
   - Configure environment variables
   - Activate workflow

3. **Set Environment Variables in n8n:**
   - `API_URL`: http://your-server:8000
   - `TELEGRAM_CHAT_ID`: Your Telegram chat ID
   - `ADMIN_EMAIL`: Admin email address
   - `ADMIN_URL`: http://your-server:8000/admin

## Maintenance

### Daily Operations
- Check logs daily: `docker-compose logs -f`
- Verify API is responding: `curl http://localhost:8000/`
- Monitor model performance

### Weekly Tasks
- Review rejected picks
- Update training data if needed
- Check system resources: `docker stats`

### Monthly Tasks
- Retrain model with new data
- Review and optimize filters
- Update dependencies: `pip install -r requirements.txt --upgrade`

