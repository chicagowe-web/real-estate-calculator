# Deployment Guide — Agent Ecosystem + Dashboard to Garage-Core

Complete deployment automation for 12 agents + production dashboard.

## 📋 Pre-Deployment Checklist

- [ ] SSH access to garage-core (user: tp, key-based auth)
- [ ] Docker & Docker Compose installed on garage-core
- [ ] 50GB free disk space
- [ ] Network access to all 5 devices (garage-core, tp, kali, canfd, canfd2)
- [ ] Git repository cloned/available
- [ ] Environment variables configured

## 🚀 Deployment Steps

### Step 1: Prepare Deployment Package

```bash
# On deployment machine (this session)
cd /home/tp

# Create deployment package
tar -czf agent-ecosystem-deployment.tar.gz \
  hermes/ \
  researchagent/ \
  monitoringagent/ \
  agentuptodate/ \
  backupagent/ \
  logagent/ \
  modelagent/ \
  securityagent/ \
  datasyncagent/ \
  notificationagent/ \
  perfagent/ \
  deployagent/ \
  agent-dashboard/ \
  garage-core-inference/ \
  AGENT_ECOSYSTEM.md \
  TEST_RESULTS.md \
  DEPLOYMENT_GUIDE.md

echo "✅ Deployment package created: agent-ecosystem-deployment.tar.gz"
```

### Step 2: Transfer to Garage-Core

```bash
# Transfer package to garage-core
scp agent-ecosystem-deployment.tar.gz tp@192.168.0.129:/opt/

# Verify transfer
ssh tp@192.168.0.129 "ls -lh /opt/agent-ecosystem-deployment.tar.gz"
```

### Step 3: Extract & Set Up on Garage-Core

```bash
# SSH to garage-core
ssh tp@192.168.0.129

# Extract package
cd /opt
sudo tar -xzf agent-ecosystem-deployment.tar.gz

# Create necessary directories
sudo mkdir -p /opt/agent-ecosystem/{logs,data,backups,ssl}
sudo chown -R tp:tp /opt/agent-ecosystem

# Create .env file
cat > /opt/agent-ecosystem/.env << 'EOF'
# Environment Configuration
ENV=production
LOG_LEVEL=info

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://192.168.0.129:3000,http://garage-core:3000

# WebSocket Configuration
WEBSOCKET_TIMEOUT=60
UPDATE_INTERVAL=2000

# Agent Configuration
AGENTS_PATH=/opt/agent-ecosystem
HERMES_HOST=localhost
HERMES_PORT=8001

# Device Configuration
DEVICES=garage-core,tp,kali,canfd,canfd2
GARAGE_CORE_IP=192.168.0.129
GARAGE_CORE_PORT=11434

# GPU Configuration
GPU_DEVICE=0
OLLAMA_URL=http://192.168.0.129:11434

# Backup Configuration
BACKUP_PATH=/opt/agent-ecosystem/backups
BACKUP_RETENTION_DAYS=30

# Logging
LOG_PATH=/opt/agent-ecosystem/logs
EOF

echo "✅ Environment configured"
```

### Step 4: Configure Docker Compose

```bash
# Navigate to dashboard
cd /opt/agent-ecosystem/agent-dashboard

# Update docker-compose.yml for production
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'

services:
  backend:
    image: agent-dashboard-backend:latest
    restart: always
    ports:
      - "8000:8000"
    environment:
      - ENV=production
      - LOG_LEVEL=info
      - CORS_ORIGINS=http://192.168.0.129:3000
    volumes:
      - /opt/agent-ecosystem/logs:/app/logs
      - /opt/agent-ecosystem/data:/app/data
    networks:
      - agent-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: agent-dashboard-frontend:latest
    restart: always
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://192.168.0.129:8000
      - VITE_WEBSOCKET_URL=ws://192.168.0.129:8000
    networks:
      - agent-network
    depends_on:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /opt/agent-ecosystem/nginx.conf:/etc/nginx/nginx.conf:ro
      - /opt/agent-ecosystem/ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
      - frontend
    networks:
      - agent-network

networks:
  agent-network:
    driver: bridge
EOF

echo "✅ Docker Compose configured for production"
```

### Step 5: Build Docker Images

```bash
cd /opt/agent-ecosystem/agent-dashboard

# Build backend image
docker build -t agent-dashboard-backend:latest ./backend

# Build frontend image
docker build -t agent-dashboard-frontend:latest ./frontend

echo "✅ Docker images built successfully"
```

### Step 6: Start Services

```bash
# Start dashboard
cd /opt/agent-ecosystem/agent-dashboard
docker-compose -f docker-compose.prod.yml up -d

# Verify services
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

echo "✅ Dashboard services started"
```

### Step 7: Configure Agents

```bash
# Create agent configuration
cat > /opt/agent-ecosystem/.hermes/config.json << 'EOF'
{
  "hermes": {
    "version": "1.0.0",
    "devices": ["garage-core", "tp", "kali", "canfd", "canfd2"],
    "gpu": {
      "enabled": true,
      "ollama_url": "http://192.168.0.129:11434",
      "models": [
        "gemma4:e4b",
        "gemma4:26b",
        "garage-ai-v12"
      ]
    }
  }
}
EOF

# Create monitoring configuration
cat > /opt/agent-ecosystem/.hermes/monitoring.yaml << 'EOF'
monitoring:
  devices:
    - name: garage-core
      host: 192.168.0.129
      port: 22
      metrics:
        - cpu
        - memory
        - disk
        - network
        - gpu
  
    - name: tp
      host: localhost
      port: 22
      metrics:
        - cpu
        - memory
        - disk
    
    - name: kali
      host: 192.168.0.200
      port: 22
      metrics:
        - cpu
        - memory
        - disk
    
    - name: canfd
      host: 192.168.0.201
      port: 22
      metrics:
        - cpu
        - memory
        - disk
    
    - name: canfd2
      host: 192.168.0.202
      port: 22
      metrics:
        - cpu
        - memory
        - disk
  
  alerts:
    cpu_threshold: 85
    memory_threshold: 80
    disk_threshold: 90
    gpu_temp_threshold: 80
EOF

echo "✅ Agent configurations created"
```

### Step 8: Verify Installation

```bash
# Check dashboard health
curl http://192.168.0.129:8000/health

# Check API endpoints
curl http://192.168.0.129:8000/api/dashboard

# Check frontend
curl http://192.168.0.129:3000

# View logs
docker-compose -f docker-compose.prod.yml logs --tail 50

echo "✅ Installation verified"
```

## 📊 Post-Deployment Validation

### Test Agent Connections

```bash
# SSH to garage-core
ssh tp@192.168.0.129

# Test agent imports
python -c "
import sys
sys.path.insert(0, '/opt/agent-ecosystem')
from hermes.hermes.models import Task
from researchagent.researchagent.models import ResearchResult
from monitoringagent.monitoringagent.models import Alert
print('✅ All agents imported successfully')
"

# Test GPU connection
python -c "
from agent_ecosystem.garage_core_inference.inference_client import GarageCoreInference
client = GarageCoreInference()
print('✅ GPU inference client ready')
"
```

### Monitor Dashboard

```bash
# View real-time logs
docker logs -f agent-dashboard-backend-1
docker logs -f agent-dashboard-frontend-1

# Check service health
docker ps -a | grep agent-dashboard

# View metrics
curl http://192.168.0.129:8000/api/devices
curl http://192.168.0.129:8000/api/agents
curl http://192.168.0.129:8000/api/gpu
```

### Access Dashboard

```
Frontend:     http://192.168.0.129:3000
Backend API:  http://192.168.0.129:8000
API Docs:     http://192.168.0.129:8000/docs
Health Check: http://192.168.0.129:8000/health
```

## 🔧 Post-Deployment Configuration

### Configure Notifications

```bash
# Edit notification settings
cat > /opt/agent-ecosystem/.hermes/notifications.yaml << 'EOF'
notifications:
  email:
    enabled: true
    smtp_server: smtp.gmail.com
    smtp_port: 587
    sender: alerts@garage-core.local
    recipients:
      - admin@garage-core.local
  
  slack:
    enabled: false
    webhook_url: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
  
  telegram:
    enabled: false
    bot_token: YOUR_BOT_TOKEN
    chat_id: YOUR_CHAT_ID
EOF
```

### Set Up SSL/HTTPS

```bash
# Generate self-signed certificate (development)
openssl req -x509 -newkey rsa:4096 -keyout /opt/agent-ecosystem/ssl/key.pem -out /opt/agent-ecosystem/ssl/cert.pem -days 365 -nodes

# Or use Let's Encrypt (production)
sudo certbot certonly --standalone -d garage-core.local

# Copy to SSL directory
sudo cp /etc/letsencrypt/live/garage-core.local/* /opt/agent-ecosystem/ssl/

# Update nginx.conf
# Uncomment SSL sections and restart
docker-compose -f docker-compose.prod.yml restart nginx
```

### Configure Backups

```bash
# Create backup schedule
cat > /opt/agent-ecosystem/backup-schedule.cron << 'EOF'
# Daily backups at 2 AM
0 2 * * * /opt/agent-ecosystem/scripts/backup.sh

# Weekly full backup Sunday at 3 AM
0 3 * * 0 /opt/agent-ecosystem/scripts/full-backup.sh

# Cleanup old backups daily at 4 AM
0 4 * * * /opt/agent-ecosystem/scripts/cleanup-backups.sh
EOF

# Install cron job
crontab /opt/agent-ecosystem/backup-schedule.cron
```

## 🚨 Monitoring & Maintenance

### Health Checks

```bash
# Weekly health check script
cat > /opt/agent-ecosystem/scripts/health-check.sh << 'EOF'
#!/bin/bash

echo "=== Agent Ecosystem Health Check ==="
echo

# Check Docker containers
echo "Docker Status:"
docker ps -a | grep agent-dashboard

# Check API health
echo "API Health:"
curl -s http://localhost:8000/health | python -m json.tool

# Check device connectivity
echo "Device Connectivity:"
for device in garage-core tp kali canfd canfd2; do
  if ping -c 1 $device &> /dev/null; then
    echo "✅ $device: Online"
  else
    echo "❌ $device: Offline"
  fi
done

# Check disk usage
echo "Disk Usage:"
df -h /opt/agent-ecosystem

# Check logs for errors
echo "Recent Errors:"
docker-compose logs --tail 20 | grep -i error || echo "No errors found"

echo
echo "=== Health Check Complete ==="
EOF

chmod +x /opt/agent-ecosystem/scripts/health-check.sh
```

### Log Rotation

```bash
# Create logrotate config
sudo cat > /etc/logrotate.d/agent-ecosystem << 'EOF'
/opt/agent-ecosystem/logs/*.log {
  daily
  rotate 7
  compress
  delaycompress
  notifempty
  create 0644 tp tp
  sharedscripts
  postrotate
    docker-compose -f /opt/agent-ecosystem/agent-dashboard/docker-compose.prod.yml restart
  endscript
}
EOF
```

## 📈 Performance Optimization

### Resource Limits

```yaml
# Add to docker-compose.prod.yml services
services:
  backend:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  frontend:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Database Connection Pooling

```python
# Add to backend/app/services/*.py
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
)
```

## 🆘 Troubleshooting

### Dashboard Won't Start

```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Rebuild images
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### Agents Not Connecting

```bash
# Test connectivity to devices
ssh tp@garage-core "ssh -T tp@kali 'echo OK'" 2>&1

# Check agent logs
docker logs agent-dashboard-backend-1 | grep -i agent

# Verify inference_client
python -c "from garage_core_inference.inference_client import GarageCoreInference; print('OK')"
```

### GPU Inference Not Working

```bash
# Check Ollama status
curl http://192.168.0.129:11434/api/tags

# Test inference
curl http://192.168.0.129:11434/api/generate -X POST -H "Content-Type: application/json" \
  -d '{"model":"gemma4:e4b","prompt":"Hello"}'

# Check backend logs for GPU errors
docker logs agent-dashboard-backend-1 | grep -i ollama
```

## 📝 Deployment Checklist

- [ ] Package created and transferred
- [ ] Extracted on garage-core
- [ ] .env file configured
- [ ] Docker images built
- [ ] Services started
- [ ] Health checks passing
- [ ] Dashboard accessible
- [ ] Agents connected
- [ ] GPU inference working
- [ ] Alerts configured
- [ ] Backups scheduled
- [ ] Monitoring active
- [ ] SSL certificates installed
- [ ] Notifications configured

## 🎯 Post-Deployment Next Steps

1. **Configure Monitoring** — Set up alerting for critical events
2. **Test Deployments** — Verify deployment agent works
3. **Backup Testing** — Verify backups and recovery
4. **Performance Baseline** — Establish baseline metrics
5. **User Training** — Train team on dashboard usage
6. **Incident Response** — Document on-call procedures

---

**Status:** Ready for deployment | **Version:** 1.0 | **Date:** 2026-09-20
