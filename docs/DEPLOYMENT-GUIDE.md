# Production Deployment Guide

## 🚀 Production Deployment Overview

The MCP server requires Docker for production deployment due to complex dependencies including tree-sitter language parsers, SQLite with FTS5, and repository management capabilities.

## ⚠️ Why Docker is Required

**Complex Dependencies:**
- Tree-sitter language parsers (C/C++ native extensions)
- SQLite with FTS5 full-text search support
- Git and file system monitoring tools
- Platform-specific compilation requirements

**Repository Management:**
- External repository indexing and cleanup
- File system monitoring for changes
- Git repository operations
- Cross-language pattern discovery

## 🐳 Production vs Development Containers

### **Development Container (DO NOT use in production)**
- Contains debugging tools and utilities
- Runs as root user (security risk)
- Larger image size (~800MB+)
- Debug logging enabled
- Development environment variables

### **Production Container (Use this)**
- Multi-stage build with minimal runtime
- Non-root user for security
- Optimized image size (~400MB)
- Production logging configuration
- Security hardening

## 📋 Production Deployment Steps

### **1. Environment Configuration**

Create `.env.production`:

```bash
# Core Configuration
MCP_ENVIRONMENT=production
PYTHONUNBUFFERED=1

# Repository Management
ENABLE_REPOSITORY_MANAGEMENT=true
REPOSITORY_AUTO_CLEANUP=true
DEFAULT_REPOSITORY_TTL_DAYS=30

# Security
DB_PASSWORD=your_secure_db_password_here
REDIS_PASSWORD=your_secure_redis_password_here
GRAFANA_ADMIN_PASSWORD=your_secure_grafana_password_here

# Optional: Database Configuration
# DATABASE_URL=postgresql://user:pass@localhost/dbname
# REDIS_URL=redis://localhost:6379/0

# Optional: Monitoring
# SENTRY_DSN=https://your-sentry-dsn
# PROMETHEUS_ENABLED=true
```

### **2. Production Build**

```bash
# Build production container
docker build -f Dockerfile.production -t mcp-server:production .

# Or use docker-compose
docker-compose -f docker-compose.production.yml build
```

### **3. Production Startup**

```bash
# Start all services
docker-compose -f docker-compose.production.yml up -d

# View logs
docker-compose -f docker-compose.production.yml logs -f mcp-server

# Health check
curl http://localhost:8000/health
```

## 🏗️ Production Architecture

The production setup includes:

### **Core Services**
- **MCP Server**: Main application with repository management
- **PostgreSQL**: Primary database (optional, can use SQLite)
- **Redis**: Caching and session storage (optional)
- **Nginx**: Reverse proxy and SSL termination

### **Monitoring Stack**
- **Prometheus**: Metrics collection
- **Grafana**: Dashboards and visualization
- **Loki**: Log aggregation (optional)

### **Security Features**
- Non-root container execution
- Health checks and automatic restart
- SSL/TLS termination
- Network isolation

## 📊 Resource Requirements

### **Minimum Requirements**
- **CPU**: 2 cores
- **Memory**: 4GB RAM
- **Storage**: 20GB SSD
- **Network**: 1Gbps

### **Recommended for Production**
- **CPU**: 4+ cores
- **Memory**: 8GB+ RAM
- **Storage**: 100GB+ SSD
- **Network**: 10Gbps

### **Scaling Considerations**
- Each repository adds ~50-200MB to database
- Vector embeddings require ~1KB per code symbol
- SQLite handles up to 100GB databases efficiently
- Consider PostgreSQL for >50GB or high concurrency

## 🔐 Security Configuration

### **Container Security**
```dockerfile
# Non-root user
USER mcp

# Read-only root filesystem
# Minimal attack surface
# No shell access in production
```

### **Network Security**
```yaml
# Internal network isolation
networks:
  mcp-network:
    driver: bridge

# Firewall configuration (recommended)
# - Allow 80/443 (HTTP/HTTPS)
# - Block direct database access
# - Restrict monitoring ports
```

### **Data Security**
- Database encryption at rest
- TLS encryption in transit
- Secure password policies
- Regular security updates

## 🔄 Repository Management in Production

### **External Repository Workflow**

```bash
# 1. Add reference repository via MCP
{
  "tool": "add_reference_repository",
  "arguments": {
    "path": "/app/repositories/golang-examples",
    "name": "Go Reference Code",
    "language": "go",
    "purpose": "python_to_go_translation",
    "days_to_keep": 30
  }
}

# 2. Repositories are automatically cleaned after TTL
# 3. Vector embeddings allow cross-language pattern discovery
```

### **Storage Layout**
```
/app/
├── data/                     # SQLite database
│   └── code_index.db        # All repositories in one database
├── repositories/            # External repository storage
│   ├── golang-examples/    # Cloned reference repositories
│   └── rust-patterns/      # Temporary translation references
├── uploads/                 # File upload staging
└── logs/                   # Application logs
```

### **Cleanup Automation**
- Automatic cleanup based on TTL
- Metadata-driven repository removal
- Vector embedding cleanup
- Storage optimization

## Production Deployment

### 1. Infrastructure Setup

#### Using Kubernetes

Create `kubernetes/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
  labels:
    app: mcp-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-server
  template:
    metadata:
      labels:
        app: mcp-server
    spec:
      containers:
      - name: mcp-server
        image: your-registry/code-index-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-server
spec:
  selector:
    app: mcp-server
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 2. Database Setup

#### PostgreSQL with High Availability

```sql
-- Create database and user
CREATE DATABASE codeindex;
CREATE USER mcp_user WITH ENCRYPTED PASSWORD 'secure-password';
GRANT ALL PRIVILEGES ON DATABASE codeindex TO mcp_user;

-- Create schema
\c codeindex;

CREATE TABLE IF NOT EXISTS repositories (
    id SERIAL PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    last_indexed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS files (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER REFERENCES repositories(id),
    path TEXT NOT NULL,
    content TEXT,
    language VARCHAR(50),
    last_modified TIMESTAMP,
    hash VARCHAR(64),
    UNIQUE(repository_id, path)
);

CREATE TABLE IF NOT EXISTS symbols (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES files(id),
    name TEXT NOT NULL,
    type VARCHAR(50),
    line_start INTEGER,
    line_end INTEGER,
    column_start INTEGER,
    column_end INTEGER,
    definition TEXT,
    INDEX idx_symbols_name (name),
    INDEX idx_symbols_type (type)
);

-- Full-text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_files_content_gin ON files USING gin(content gin_trgm_ops);
CREATE INDEX idx_symbols_name_gin ON symbols USING gin(name gin_trgm_ops);
```

### 3. Load Balancing

#### Nginx Configuration

```nginx
upstream mcp_backend {
    least_conn;
    server mcp-server-1:8000 weight=1 max_fails=3 fail_timeout=30s;
    server mcp-server-2:8000 weight=1 max_fails=3 fail_timeout=30s;
    server mcp-server-3:8000 weight=1 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.codeindex.example.com;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://mcp_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    location /health {
        access_log off;
        proxy_pass http://mcp_backend/health;
    }
}
```

### 4. Process Management with Systemd

Create `/etc/systemd/system/mcp-server.service`:

```ini
[Unit]
Description=Code-Index-MCP Server
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=mcp
Group=mcp
WorkingDirectory=/opt/code-index-mcp
Environment="PATH=/opt/code-index-mcp/venv/bin:/usr/local/bin:/usr/bin"
ExecStart=/opt/code-index-mcp/venv/bin/python -m mcp_server.gateway
ExecReload=/bin/kill -s HUP $MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/code-index-mcp/data

[Install]
WantedBy=multi-user.target
```

## Scaling Considerations

### 1. Horizontal Scaling

#### Auto-scaling Configuration (Kubernetes)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: mcp-server-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: mcp-server
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
```

### 2. Caching Strategy

#### Redis Configuration

```redis
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
```

#### Application-level Caching

```python
# In mcp_server/utils/cache.py
from functools import lru_cache
import redis
import json
import hashlib

class CacheManager:
    def __init__(self, redis_url):
        self.redis = redis.from_url(redis_url)
        
    def cache_key(self, *args, **kwargs):
        """Generate cache key from arguments"""
        key_data = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True)
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_or_set(self, key, func, ttl=3600):
        """Get from cache or compute and store"""
        cached = self.redis.get(key)
        if cached:
            return json.loads(cached)
        
        result = func()
        self.redis.setex(key, ttl, json.dumps(result))
        return result
```

### 3. Database Optimization

#### Connection Pooling

```python
# In mcp_server/db.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

#### Query Optimization

```sql
-- Add indexes for common queries
CREATE INDEX idx_files_language ON files(language);
CREATE INDEX idx_files_repo_path ON files(repository_id, path);
CREATE INDEX idx_symbols_file_type ON symbols(file_id, type);

-- Partitioning for large tables
CREATE TABLE symbols_2024 PARTITION OF symbols
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### 4. Message Queue for Background Tasks

#### Celery Configuration

```python
# celery_config.py
from celery import Celery

app = Celery('mcp_server')
app.config_from_object({
    'broker_url': 'redis://localhost:6379/1',
    'result_backend': 'redis://localhost:6379/2',
    'task_serializer': 'json',
    'accept_content': ['json'],
    'result_serializer': 'json',
    'timezone': 'UTC',
    'enable_utc': True,
    'task_routes': {
        'mcp_server.tasks.index_repository': {'queue': 'indexing'},
        'mcp_server.tasks.update_symbols': {'queue': 'symbols'},
    },
    'task_annotations': {
        'mcp_server.tasks.index_repository': {'rate_limit': '10/m'},
    }
})
```

## Monitoring and Observability

### 1. Prometheus Metrics

```python
# In mcp_server/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Define metrics
request_count = Counter('mcp_requests_total', 'Total requests', ['method', 'endpoint'])
request_duration = Histogram('mcp_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
active_connections = Gauge('mcp_active_connections', 'Active connections')
index_queue_size = Gauge('mcp_index_queue_size', 'Indexing queue size')

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### 2. Logging Configuration

```python
# logging_config.py
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'level': 'INFO'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/mcp-server/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json',
            'level': 'INFO'
        }
    },
    'loggers': {
        'mcp_server': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False
        }
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

### 3. Grafana Dashboard

Create a dashboard with panels for:

- Request rate and latency
- Error rate
- Active connections
- CPU and memory usage
- Database connection pool stats
- Cache hit/miss ratio
- Indexing queue size
- Background job processing rate

### 4. Health Checks

```python
# In mcp_server/health.py
from fastapi import APIRouter, Response
import psutil
import asyncpg

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy"}

@router.get("/ready")
async def readiness_check():
    """Detailed readiness check"""
    checks = {}
    
    # Database check
    try:
        async with asyncpg.connect(DATABASE_URL) as conn:
            await conn.fetchval("SELECT 1")
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
    
    # Redis check
    try:
        redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"
    
    # System resources
    checks["cpu_percent"] = psutil.cpu_percent()
    checks["memory_percent"] = psutil.virtual_memory().percent
    
    status_code = 200 if all(v == "ok" or isinstance(v, (int, float)) for v in checks.values()) else 503
    return Response(content=json.dumps(checks), status_code=status_code)
```

## Security Best Practices

### 1. Authentication and Authorization

```python
# In mcp_server/auth.py
from fastapi import Security, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# Apply to routes
@app.get("/api/search", dependencies=[Depends(verify_token)])
async def search(query: str):
    # ... implementation
```

### 2. Input Validation

```python
from pydantic import BaseModel, validator, constr
from typing import List, Optional

class SearchRequest(BaseModel):
    query: constr(min_length=1, max_length=200)
    language: Optional[constr(regex="^[a-zA-Z0-9_-]+$")]
    limit: int = Field(default=50, ge=1, le=1000)
    
    @validator('query')
    def validate_query(cls, v):
        # Prevent injection attacks
        dangerous_chars = ['<', '>', '&', '"', "'", '\0']
        if any(char in v for char in dangerous_chars):
            raise ValueError('Query contains invalid characters')
        return v
```

### 3. Rate Limiting

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/search")
@limiter.limit("10/minute")
async def search(request: Request, query: str):
    # ... implementation
```

### 4. Network Security

```yaml
# Network policies for Kubernetes
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcp-server-netpol
spec:
  podSelector:
    matchLabels:
      app: mcp-server
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

## Troubleshooting

### Common Issues

#### 1. High Memory Usage

```bash
# Check memory usage by process
ps aux | grep mcp_server | awk '{print $2, $4, $11}'

# Profile memory usage
python -m memory_profiler mcp_server/gateway.py

# Limit memory in Docker
docker run -m 2g --memory-swap 2g your-image
```

#### 2. Slow Indexing

```python
# Add profiling
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()
# ... indexing code
profiler.disable()
stats = pstats.Stats(profiler).sort_stats('cumulative')
stats.print_stats(10)
```

#### 3. Database Connection Issues

```sql
-- Check active connections
SELECT pid, usename, application_name, client_addr, state 
FROM pg_stat_activity 
WHERE datname = 'codeindex';

-- Kill stuck queries
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'codeindex' 
  AND state = 'idle in transaction' 
  AND state_change < current_timestamp - interval '5 minutes';
```

#### 4. Debugging Production Issues

```bash
# Enable debug logging temporarily
curl -X POST http://localhost:8000/admin/log-level \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"level": "DEBUG"}'

# Collect diagnostics
curl http://localhost:8000/admin/diagnostics > diagnostics.json

# Thread dump
kill -USR1 $(pgrep -f mcp_server)
```

### Performance Tuning

#### 1. Python Optimization

```python
# Use uvloop for better async performance
import uvloop
uvloop.install()

# Optimize imports
import lazy_import
lazy_import.lazy_module("heavy_module")
```

#### 2. Database Tuning

```sql
-- PostgreSQL configuration
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET min_wal_size = '1GB';
ALTER SYSTEM SET max_wal_size = '4GB';
```

#### 3. Linux Kernel Tuning

```bash
# /etc/sysctl.conf
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.ip_local_port_range = 1024 65535
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
net.core.netdev_max_backlog = 65535
net.ipv4.tcp_keepalive_time = 300
net.ipv4.tcp_keepalive_probes = 5
net.ipv4.tcp_keepalive_intvl = 15
```

## Backup and Recovery

### 1. Database Backup

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"

# Create backup
pg_dump -h localhost -U postgres -d codeindex -F c -f "$BACKUP_DIR/codeindex_$DATE.dump"

# Upload to S3
aws s3 cp "$BACKUP_DIR/codeindex_$DATE.dump" s3://your-backup-bucket/postgres/

# Clean old backups
find $BACKUP_DIR -name "*.dump" -mtime +7 -delete
```

### 2. Disaster Recovery Plan

1. **RTO (Recovery Time Objective)**: 1 hour
2. **RPO (Recovery Point Objective)**: 15 minutes

```yaml
# Kubernetes CronJob for backups
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "*/15 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: postgres-backup
            image: postgres:15
            command:
            - /bin/bash
            - -c
            - |
              pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER -d codeindex | \
              gzip | aws s3 cp - s3://backups/postgres/$(date +%Y%m%d_%H%M%S).sql.gz
          restartPolicy: OnFailure
```

## Conclusion

This deployment guide covers the essential aspects of deploying Code-Index-MCP from local development to production environments. Key takeaways:

1. **Start simple**: Begin with local development and Docker Compose before moving to complex orchestration
2. **Monitor everything**: Implement comprehensive monitoring from day one
3. **Plan for scale**: Design with horizontal scaling in mind
4. **Security first**: Implement authentication, authorization, and encryption at all levels
5. **Automate operations**: Use infrastructure as code and automated deployment pipelines

For additional support and updates, refer to the project documentation and community resources.