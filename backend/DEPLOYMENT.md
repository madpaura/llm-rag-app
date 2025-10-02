# RAG Engine Deployment Guide

Complete guide for deploying the RAG engine to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Monitoring & Maintenance](#monitoring--maintenance)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **CPU**: 4+ cores (8+ recommended for large models)
- **RAM**: 8GB minimum (16GB+ recommended)
- **Storage**: 50GB+ for models and vector stores
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2

### Software Requirements

- Python 3.10+
- Ollama
- Docker & Docker Compose (for containerized deployment)
- PostgreSQL (optional, for metadata)

---

## Local Development

### 1. Setup Development Environment

```bash
# Clone repository
git clone <repository-url>
cd llm-rag-app/backend

# Run automated setup
./setup.sh

# Or manual setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434

# Vector Store
VECTOR_STORE_PERSIST_DIR=./data/vector_stores

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Logging
LOG_LEVEL=debug
```

### 3. Start Development Server

```bash
# Start Ollama
ollama serve

# Start FastAPI (with auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## Docker Deployment

### Single Container Deployment

#### Dockerfile

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /app/data/vector_stores

# Expose ports
EXPOSE 8000 11434

# Start script
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
```

#### docker-entrypoint.sh

```bash
#!/bin/bash
set -e

# Start Ollama in background
ollama serve &

# Wait for Ollama to be ready
sleep 5

# Pull required models
echo "Pulling models..."
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# Start FastAPI
exec uvicorn main:app --host 0.0.0.0 --port 8000
```

#### Build and Run

```bash
# Build image
docker build -t rag-engine:latest .

# Run container
docker run -d \
  --name rag-engine \
  -p 8000:8000 \
  -p 11434:11434 \
  -v $(pwd)/data:/app/data \
  -e VECTOR_STORE_PERSIST_DIR=/app/data/vector_stores \
  rag-engine:latest
```

### Docker Compose Deployment

#### docker-compose.yml

```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3

  rag-backend:
    build: .
    container_name: rag-backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - VECTOR_STORE_PERSIST_DIR=/app/data/vector_stores
      - DEBUG=false
      - LOG_LEVEL=info
    depends_on:
      ollama:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    container_name: postgres
    environment:
      - POSTGRES_DB=rag_db
      - POSTGRES_USER=rag_user
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

volumes:
  ollama_data:
  postgres_data:
```

#### Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f rag-backend

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

---

## Production Deployment

### 1. Environment Configuration

Create production `.env`:

```bash
# Ollama
OLLAMA_BASE_URL=http://ollama:11434

# Vector Store
VECTOR_STORE_PERSIST_DIR=/data/vector_stores

# API
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# CORS
ALLOWED_ORIGINS=https://your-domain.com,https://app.your-domain.com

# Security
SECRET_KEY=<generate-secure-key>
ALLOWED_HOSTS=your-domain.com,api.your-domain.com

# Logging
LOG_LEVEL=info
SENTRY_DSN=<your-sentry-dsn>

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/rag_db

# Performance
WORKERS=4
MAX_CONNECTIONS=100
```

### 2. Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/rag-api

upstream rag_backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name api.your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy settings
    location / {
        proxy_pass http://rag_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running queries
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;
}
```

### 3. Systemd Service (Alternative to Docker)

```ini
# /etc/systemd/system/rag-engine.service

[Unit]
Description=RAG Engine API
After=network.target ollama.service

[Service]
Type=simple
User=rag
WorkingDirectory=/opt/rag-engine
Environment="PATH=/opt/rag-engine/venv/bin"
ExecStart=/opt/rag-engine/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable rag-engine
sudo systemctl start rag-engine
sudo systemctl status rag-engine
```

### 4. Model Pre-loading

Create initialization script:

```bash
#!/bin/bash
# init-models.sh

MODELS=(
    "llama3.2:3b"
    "llama3.1:8b"
    "nomic-embed-text"
    "mxbai-embed-large"
)

for model in "${MODELS[@]}"; do
    echo "Pulling $model..."
    ollama pull "$model"
done

echo "All models ready!"
```

### 5. Backup Strategy

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/rag-engine"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup vector stores
tar -czf "$BACKUP_DIR/vector_stores_$DATE.tar.gz" /data/vector_stores

# Backup database
pg_dump -U rag_user rag_db > "$BACKUP_DIR/db_$DATE.sql"

# Keep only last 7 days
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.sql" -mtime +7 -delete
```

Add to crontab:
```bash
0 2 * * * /opt/rag-engine/backup.sh
```

---

## Monitoring & Maintenance

### 1. Health Checks

```python
# Add to main.py

from fastapi import FastAPI
from datetime import datetime

@app.get("/health/detailed")
async def detailed_health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "ollama": check_ollama_health(),
            "vector_store": check_vector_store_health(),
            "database": check_database_health()
        }
    }
```

### 2. Prometheus Metrics

```python
# metrics.py

from prometheus_client import Counter, Histogram, Gauge
from prometheus_client import make_asgi_app

# Metrics
query_counter = Counter('rag_queries_total', 'Total queries', ['technique', 'collection'])
query_duration = Histogram('rag_query_duration_seconds', 'Query duration')
active_collections = Gauge('rag_active_collections', 'Active collections')
model_usage = Counter('rag_model_usage', 'Model usage', ['model_name'])

# Add to main.py
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)
```

### 3. Logging Configuration

```python
# logging_config.py

import structlog
import logging

def setup_production_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

### 4. Monitoring Dashboard

Use Grafana with Prometheus:

```yaml
# prometheus.yml

global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'rag-engine'
    static_configs:
      - targets: ['localhost:8000']
```

---

## Troubleshooting

### Common Issues

#### 1. Ollama Connection Failed

```bash
# Check Ollama status
systemctl status ollama

# Check Ollama logs
journalctl -u ollama -f

# Test connection
curl http://localhost:11434/api/tags
```

#### 2. Out of Memory

```bash
# Check memory usage
docker stats

# Reduce model size or use quantized models
# Update config to use smaller models
```

#### 3. Slow Queries

```bash
# Check model performance
time ollama run llama3.2:3b "test query"

# Optimize configuration
- Reduce top_k
- Use smaller models
- Enable GPU acceleration
```

#### 4. Vector Store Corruption

```bash
# Backup and recreate
mv /data/vector_stores /data/vector_stores.bak
mkdir /data/vector_stores

# Re-ingest documents
python scripts/reingest.py
```

### Performance Tuning

#### 1. Optimize Uvicorn Workers

```bash
# Calculate optimal workers
workers = (2 * CPU_cores) + 1

# Start with optimized settings
uvicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

#### 2. Enable GPU Acceleration

```dockerfile
# Dockerfile with GPU support
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

# Install Ollama with GPU support
# Ollama automatically detects and uses GPU
```

#### 3. Connection Pooling

```python
# config.py

from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

### Security Checklist

- [ ] Enable HTTPS with valid SSL certificates
- [ ] Configure CORS properly
- [ ] Implement rate limiting
- [ ] Use environment variables for secrets
- [ ] Enable authentication and authorization
- [ ] Regular security updates
- [ ] Monitor for suspicious activity
- [ ] Backup encryption
- [ ] Network isolation for services
- [ ] Input validation and sanitization

---

## Scaling Strategies

### Horizontal Scaling

```yaml
# docker-compose.scale.yml

services:
  rag-backend:
    deploy:
      replicas: 3
    
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    ports:
      - "80:80"
    depends_on:
      - rag-backend
```

### Load Balancing

```nginx
# nginx.conf

upstream rag_cluster {
    least_conn;
    server rag-backend-1:8000;
    server rag-backend-2:8000;
    server rag-backend-3:8000;
}
```

### Caching Strategy

```python
from functools import lru_cache
from redis import Redis

redis_client = Redis(host='redis', port=6379)

@lru_cache(maxsize=1000)
def get_cached_embedding(text: str):
    # Cache embeddings
    pass
```

---

## Maintenance Tasks

### Daily
- Check service health
- Monitor error logs
- Review query performance

### Weekly
- Backup vector stores
- Update models if needed
- Review resource usage

### Monthly
- Security updates
- Performance optimization
- Capacity planning

---

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- Health endpoint: `http://localhost:8000/health`
- Metrics: `http://localhost:8000/metrics`
- API docs: `http://localhost:8000/docs`

---

**Last Updated**: 2025-10-02
