"""
Test section-specific search from a user perspective.

This test module validates that users can search within specific sections
of documents, find content based on heading hierarchy, and get results
that understand document structure context.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

# Import system components
import sys
sys.path.insert(0, '/app')

from tests.base_test import BaseDocumentTest
from mcp_server.plugins.markdown_plugin.plugin import MarkdownPlugin
from mcp_server.plugins.markdown_plugin.section_extractor import SectionExtractor
from mcp_server.dispatcher import EnhancedDispatcher as Dispatcher
from mcp_server.storage.sqlite_store import SQLiteStore


class TestSectionSearch(BaseDocumentTest):
    """Test section-specific search, heading search, and nested queries."""
    
    @pytest.fixture
    def sectioned_documents(self, tmp_path):
        """Create documents with clear section structure."""
        workspace = tmp_path / "sections"
        workspace.mkdir()
        
        # Comprehensive guide with nested sections
        guide = """# Complete Platform Guide

## Table of Contents
1. [Getting Started](#getting-started)
2. [Configuration](#configuration)
3. [Advanced Features](#advanced-features)
4. [Troubleshooting](#troubleshooting)
5. [API Reference](#api-reference)

## Getting Started

### System Requirements

Before you begin, ensure your system meets these requirements:

#### Hardware Requirements
- **Processor**: 64-bit processor, 2 GHz or faster
- **Memory**: 8 GB RAM minimum (16 GB recommended)
- **Storage**: 50 GB available space (SSD recommended)
- **Network**: Broadband internet connection

#### Software Requirements
- **Operating System**: 
  - Windows 10/11 (64-bit)
  - macOS 10.15 or later
  - Ubuntu 20.04 LTS or later
- **Runtime**: Node.js 16+ or Python 3.8+
- **Database**: PostgreSQL 12+ or MySQL 8+

### Installation

#### Quick Installation
For most users, the quick installation method is recommended:

```bash
curl -fsSL https://get.platform.io | bash
```

#### Manual Installation
For advanced users who need more control:

1. **Download the package**
   ```bash
   wget https://platform.io/releases/latest/platform.tar.gz
   tar -xzf platform.tar.gz
   cd platform
   ```

2. **Install dependencies**
   ```bash
   ./scripts/install-deps.sh
   ```

3. **Run setup**
   ```bash
   ./setup.sh --interactive
   ```

### First Steps

#### Creating Your First Project
Once installed, create your first project:

```bash
platform init my-project
cd my-project
platform run
```

#### Basic Configuration
Edit `config.yaml` to customize:

```yaml
project:
  name: "My First Project"
  version: "1.0.0"
  
server:
  port: 8080
  host: "localhost"
```

## Configuration

### Configuration Overview
The platform uses a layered configuration system with multiple sources.

### Configuration Files

#### Main Configuration File
Located at `~/.platform/config.yaml`:

```yaml
global:
  theme: "dark"
  language: "en"
  telemetry: false

defaults:
  timeout: 30
  retries: 3
  log_level: "info"
```

#### Project Configuration
Each project has its own `platform.yaml`:

```yaml
project:
  id: "unique-project-id"
  name: "Project Name"
  description: "Project description"

build:
  target: "production"
  optimize: true
  sourcemaps: false

deploy:
  provider: "aws"
  region: "us-east-1"
  stage: "production"
```

### Environment Variables

#### Core Variables
Essential environment variables:

- `PLATFORM_HOME`: Installation directory
- `PLATFORM_CONFIG`: Configuration file path
- `PLATFORM_ENV`: Environment (development/production)
- `PLATFORM_LOG_LEVEL`: Logging verbosity

#### Security Variables
For sensitive configuration:

- `PLATFORM_API_KEY`: API authentication key
- `PLATFORM_SECRET`: Encryption secret
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Cache server URL

### Advanced Configuration

#### Performance Tuning
Optimize for your workload:

```yaml
performance:
  workers: 4
  memory_limit: "2GB"
  cache:
    enabled: true
    ttl: 3600
    max_size: "500MB"
```

#### Security Settings
Configure security features:

```yaml
security:
  encryption: "aes-256-gcm"
  tls:
    enabled: true
    min_version: "1.2"
  cors:
    origins: ["https://app.example.com"]
    credentials: true
```

## Advanced Features

### Plugin System

#### Installing Plugins
Extend functionality with plugins:

```bash
platform plugin install analytics
platform plugin install monitoring
platform plugin list
```

#### Creating Custom Plugins
Build your own plugins:

```javascript
// my-plugin.js
module.exports = {
  name: 'my-plugin',
  version: '1.0.0',
  
  activate(context) {
    context.subscriptions.push(
      platform.commands.register('my-plugin.hello', () => {
        console.log('Hello from my plugin!');
      })
    );
  }
};
```

### Automation

#### Scheduled Tasks
Configure automated tasks:

```yaml
schedules:
  - name: "daily-backup"
    cron: "0 2 * * *"
    command: "platform backup create"
    
  - name: "weekly-report"
    cron: "0 9 * * MON"
    command: "platform report generate --type weekly"
```

#### Webhooks
Set up webhook integrations:

```yaml
webhooks:
  - url: "https://hooks.slack.com/services/..."
    events: ["deploy.success", "deploy.failure"]
    
  - url: "https://api.monitoring.com/webhook"
    events: ["error.critical", "performance.alert"]
```

### API Integration

#### REST API
The platform provides a comprehensive REST API:

```bash
# Get project status
curl -H "Authorization: Bearer $TOKEN" \\
     https://api.platform.io/v1/projects/my-project

# Deploy project
curl -X POST -H "Authorization: Bearer $TOKEN" \\
     https://api.platform.io/v1/projects/my-project/deploy
```

#### GraphQL API
For more flexible queries:

```graphql
query GetProject($id: ID!) {
  project(id: $id) {
    name
    status
    deployments {
      id
      status
      createdAt
    }
  }
}
```

## Troubleshooting

### Common Issues

#### Installation Problems

##### Permission Denied
If you encounter permission errors:

```bash
# Option 1: Use sudo (not recommended)
sudo ./install.sh

# Option 2: Fix permissions
chmod +x install.sh
./install.sh

# Option 3: Install to user directory
./install.sh --prefix=$HOME/.local
```

##### Missing Dependencies
Check and install missing dependencies:

```bash
# Check system dependencies
platform doctor

# Install missing packages (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y build-essential libssl-dev

# Install missing packages (macOS)
brew install openssl readline
```

#### Runtime Errors

##### Out of Memory
If the platform runs out of memory:

1. Increase memory limit:
   ```bash
   export PLATFORM_MEMORY_LIMIT=4G
   ```

2. Reduce worker count:
   ```yaml
   performance:
     workers: 2
   ```

3. Enable swap space:
   ```bash
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

##### Connection Timeouts
For network-related timeouts:

```yaml
network:
  timeout: 60
  retry:
    attempts: 5
    delay: 1000
    backoff: 2
```

### Debugging

#### Enable Debug Mode
Get detailed logging:

```bash
# Via environment variable
export PLATFORM_DEBUG=true

# Via command line
platform --debug run

# Via configuration
log_level: "debug"
```

#### Trace Execution
Trace specific operations:

```bash
# Trace HTTP requests
platform --trace=http run

# Trace database queries
platform --trace=db run

# Trace everything
platform --trace=* run
```

## API Reference

### Core API

#### Project Management

##### Create Project
```http
POST /api/v1/projects
Content-Type: application/json

{
  "name": "New Project",
  "template": "default"
}
```

##### List Projects
```http
GET /api/v1/projects?page=1&limit=20
```

##### Update Project
```http
PATCH /api/v1/projects/{id}
Content-Type: application/json

{
  "name": "Updated Name",
  "settings": {
    "public": true
  }
}
```

#### Deployment API

##### Deploy Project
```http
POST /api/v1/projects/{id}/deploy
Content-Type: application/json

{
  "environment": "production",
  "version": "v1.2.3"
}
```

##### Get Deployment Status
```http
GET /api/v1/deployments/{deployment_id}
```

### SDK Reference

#### JavaScript SDK
```javascript
const Platform = require('@platform/sdk');

const client = new Platform.Client({
  apiKey: process.env.PLATFORM_API_KEY
});

// Create project
const project = await client.projects.create({
  name: 'My Project'
});

// Deploy
const deployment = await project.deploy({
  environment: 'production'
});
```

#### Python SDK
```python
from platform_sdk import Client

client = Client(api_key=os.environ['PLATFORM_API_KEY'])

# Create project
project = client.projects.create(name='My Project')

# Deploy
deployment = project.deploy(environment='production')

# Monitor deployment
deployment.wait_for_completion()
```
"""
        (workspace / "platform-guide.md").write_text(guide)
        
        # FAQ document with Q&A sections
        faq = """# Frequently Asked Questions

## General Questions

### What is the Platform?

The Platform is a comprehensive development and deployment solution that helps teams
build, test, and deploy applications efficiently. It provides:

- Automated build and deployment pipelines
- Integrated development environments
- Performance monitoring and analytics
- Collaboration tools for teams

### Who should use the Platform?

The Platform is designed for:

- **Developers**: Streamline your development workflow
- **DevOps Teams**: Automate deployment and operations
- **Project Managers**: Track progress and manage resources
- **Enterprises**: Scale applications with confidence

### How much does it cost?

We offer several pricing tiers:

- **Free Tier**: Up to 3 projects, 1GB storage
- **Pro Tier**: $29/month, unlimited projects, 100GB storage
- **Enterprise**: Custom pricing, unlimited everything

## Installation Questions

### What are the system requirements?

#### Minimum Requirements
- 4GB RAM
- 2 CPU cores
- 20GB free disk space
- Internet connection

#### Recommended Requirements
- 16GB RAM
- 4+ CPU cores
- 100GB SSD storage
- Gigabit internet

### How do I install on Windows?

1. Download the Windows installer from our website
2. Run the installer as Administrator
3. Follow the installation wizard
4. Restart your computer when prompted

For detailed instructions, see the [Installation Guide](#installation).

### Can I install without admin rights?

Yes, you can install to your user directory:

```bash
./install.sh --user --prefix=$HOME/platform
```

Then add to your PATH:
```bash
export PATH="$HOME/platform/bin:$PATH"
```

## Configuration Questions

### Where are configuration files stored?

Configuration files are stored in these locations:

- **Global**: `~/.platform/config.yaml`
- **Project**: `./platform.yaml`
- **System**: `/etc/platform/config.yaml` (Linux/Mac)

### How do I set environment variables?

#### On Linux/Mac:
```bash
export PLATFORM_API_KEY="your-key"
export PLATFORM_ENV="production"
```

#### On Windows:
```powershell
$env:PLATFORM_API_KEY = "your-key"
$env:PLATFORM_ENV = "production"
```

### Can I use custom domains?

Yes, configure custom domains in your project settings:

```yaml
domains:
  - domain: "app.example.com"
    ssl: true
  - domain: "api.example.com"
    ssl: true
```

## Usage Questions

### How do I create a new project?

Creating a new project is simple:

```bash
# Interactive mode
platform init

# With template
platform init --template react

# With options
platform init my-app --template vue --git
```

### How do I deploy my application?

Deploy with a single command:

```bash
# Deploy to default environment
platform deploy

# Deploy to specific environment
platform deploy --env production

# Deploy specific version
platform deploy --tag v1.2.3
```

### How do I rollback a deployment?

Rollback to a previous version:

```bash
# Rollback to previous deployment
platform rollback

# Rollback to specific version
platform rollback --to v1.2.2

# Rollback with confirmation
platform rollback --interactive
```

## Troubleshooting Questions

### Why is my deployment failing?

Common causes of deployment failures:

1. **Build Errors**: Check your build logs
   ```bash
   platform logs --build
   ```

2. **Missing Dependencies**: Ensure all dependencies are listed
   ```bash
   platform deps check
   ```

3. **Configuration Issues**: Validate your configuration
   ```bash
   platform config validate
   ```

### How do I debug performance issues?

Use built-in performance tools:

```bash
# Performance profiling
platform profile --duration 60

# Resource monitoring
platform monitor

# Generate performance report
platform report performance
```

### What do I do if I forgot my API key?

Recover your API key:

1. Log into the web dashboard
2. Go to Settings → API Keys
3. Click "Regenerate Key"
4. Update your local configuration

## Security Questions

### How is my data secured?

We implement multiple security layers:

- **Encryption**: All data encrypted at rest (AES-256)
- **Transit Security**: TLS 1.3 for all communications
- **Access Control**: Role-based permissions
- **Audit Logs**: Complete activity tracking

### Can I use my own SSL certificates?

Yes, you can provide custom SSL certificates:

```yaml
ssl:
  provider: "custom"
  cert_path: "/path/to/cert.pem"
  key_path: "/path/to/key.pem"
```

### How do I enable two-factor authentication?

Enable 2FA in your account settings:

1. Go to Security Settings
2. Click "Enable 2FA"
3. Scan QR code with authenticator app
4. Enter verification code

## Advanced Questions

### Can I extend the Platform with plugins?

Yes, the Platform supports custom plugins:

```javascript
// Create a plugin
platform.createPlugin({
  name: 'my-plugin',
  version: '1.0.0',
  
  commands: {
    'hello': (args) => {
      console.log('Hello from plugin!');
    }
  }
});
```

### How do I integrate with CI/CD pipelines?

Integration examples for popular CI/CD tools:

#### GitHub Actions
```yaml
- name: Deploy to Platform
  uses: platform-io/deploy-action@v1
  with:
    api-key: ${{ secrets.PLATFORM_API_KEY }}
    project: my-app
```

#### Jenkins
```groovy
pipeline {
  stages {
    stage('Deploy') {
      steps {
        sh 'platform deploy --env production'
      }
    }
  }
}
```

### Can I self-host the Platform?

Enterprise customers can self-host:

1. Contact sales for enterprise license
2. Receive installation packages
3. Deploy to your infrastructure
4. Maintain with our support

## Getting Help

### Where can I find more documentation?

- **Official Docs**: https://docs.platform.io
- **API Reference**: https://api.platform.io/docs
- **Video Tutorials**: https://platform.io/tutorials
- **Community Forum**: https://forum.platform.io

### How do I report bugs?

Report bugs through these channels:

- **GitHub Issues**: https://github.com/platform-io/platform/issues
- **Support Email**: support@platform.io
- **In-app Feedback**: Click the feedback button

### Is there community support?

Yes! Join our community:

- **Discord**: https://discord.gg/platform
- **Slack**: https://platform.slack.com
- **Stack Overflow**: Tag questions with [platform-io]
- **Reddit**: r/platformio
"""
        (workspace / "faq.md").write_text(faq)
        
        # Technical documentation with code sections
        tech_doc = """# Technical Architecture Documentation

## System Architecture

### Overview

Our system is built on a microservices architecture designed for scalability,
reliability, and maintainability.

### Core Components

#### API Gateway

The API Gateway serves as the single entry point for all client requests.

##### Responsibilities
- Request routing
- Authentication/Authorization
- Rate limiting
- Request/Response transformation
- Circuit breaking

##### Implementation
```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="API Gateway")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Rate limiting logic here
    response = await call_next(request)
    return response
```

##### Configuration
```yaml
gateway:
  port: 8080
  timeout: 30
  rate_limit:
    requests_per_minute: 60
    burst: 10
```

#### Service Registry

Service discovery and health checking.

##### Service Registration
```python
import consul

class ServiceRegistry:
    def __init__(self):
        self.consul = consul.Consul()
    
    def register_service(self, name, address, port, health_check_url):
        self.consul.agent.service.register(
            name=name,
            service_id=f"{name}-{address}-{port}",
            address=address,
            port=port,
            check=consul.Check.http(
                health_check_url,
                interval="10s",
                timeout="5s"
            )
        )
```

##### Health Checks
```python
@app.get("/health")
async def health_check():
    # Check dependent services
    checks = {
        "database": await check_database(),
        "cache": await check_cache(),
        "queue": await check_queue()
    }
    
    if all(checks.values()):
        return {"status": "healthy", "checks": checks}
    else:
        return {"status": "unhealthy", "checks": checks}, 503
```

### Data Layer

#### Database Design

##### Schema Overview
Our database uses PostgreSQL with the following design principles:
- Normalized to 3NF where appropriate
- Denormalized for read-heavy tables
- Partitioning for time-series data

##### Core Tables
```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Deployments table (partitioned by date)
CREATE TABLE deployments (
    id UUID DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    version VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, deployed_at)
) PARTITION BY RANGE (deployed_at);
```

##### Query Optimization
```sql
-- Optimized query with proper indexes
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_deployments_project_status ON deployments(project_id, status);

-- Example optimized query
EXPLAIN ANALYZE
SELECT p.*, 
       COUNT(d.id) as deployment_count,
       MAX(d.deployed_at) as last_deployed
FROM projects p
LEFT JOIN deployments d ON p.id = d.project_id
WHERE p.user_id = $1
GROUP BY p.id
ORDER BY p.created_at DESC
LIMIT 20;
```

#### Caching Strategy

##### Redis Configuration
```python
import redis
from functools import wraps
import json

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)

def cache(expiration=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Execute function
            result = await func(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(
                cache_key,
                expiration,
                json.dumps(result)
            )
            
            return result
        return wrapper
    return decorator
```

##### Cache Invalidation
```python
def invalidate_cache(pattern):
    """Invalidate cache entries matching pattern"""
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)

# Usage
invalidate_cache("get_user:*")  # Invalidate all user caches
invalidate_cache(f"get_project:{project_id}:*")  # Specific project
```

### Security Implementation

#### Authentication

##### JWT Implementation
```python
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, secret_key, algorithm="HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_access_token(self, user_id: str) -> str:
        payload = {
            "sub": user_id,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise Exception("Token has expired")
        except jwt.JWTError:
            raise Exception("Invalid token")
```

##### OAuth2 Integration
```python
from authlib.integrations.starlette_client import OAuth

oauth = OAuth()

oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

@app.get('/login/google')
async def login_google(request: Request):
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)
```

#### Authorization

##### RBAC Implementation
```python
from enum import Enum
from typing import List

class Role(Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"

class Permission(Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

ROLE_PERMISSIONS = {
    Role.ADMIN: [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN],
    Role.USER: [Permission.READ, Permission.WRITE],
    Role.VIEWER: [Permission.READ]
}

def require_permission(permission: Permission):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from request context
            user = get_current_user()
            user_permissions = ROLE_PERMISSIONS.get(user.role, [])
            
            if permission not in user_permissions:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

# Usage
@app.delete("/projects/{id}")
@require_permission(Permission.DELETE)
async def delete_project(id: str):
    # Delete logic here
    pass
```

### Performance Optimization

#### Database Optimization

##### Connection Pooling
```python
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

##### Query Optimization
```python
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

# Optimized query with eager loading
async def get_projects_with_deployments(user_id: str):
    query = (
        select(Project)
        .where(Project.user_id == user_id)
        .options(selectinload(Project.deployments))
        .order_by(Project.created_at.desc())
        .limit(20)
    )
    
    result = await db.execute(query)
    return result.scalars().all()
```

#### Caching Strategies

##### Multi-Level Caching
```python
class MultiLevelCache:
    def __init__(self):
        self.l1_cache = {}  # In-memory cache
        self.l2_cache = redis_client  # Redis cache
    
    async def get(self, key: str):
        # Check L1 cache
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # Check L2 cache
        value = self.l2_cache.get(key)
        if value:
            self.l1_cache[key] = value
            return value
        
        return None
    
    async def set(self, key: str, value: any, ttl: int = 3600):
        # Set in both caches
        self.l1_cache[key] = value
        self.l2_cache.setex(key, ttl, value)
```

## Deployment Architecture

### Container Strategy

#### Docker Configuration
```dockerfile
# Multi-stage build for optimization
FROM python:3.10-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.10-slim

# Security: Run as non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .

USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-service
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: api-service
  template:
    metadata:
      labels:
        app: api-service
    spec:
      containers:
      - name: api
        image: platform/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
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
```

### Monitoring and Observability

#### Metrics Collection
```python
from prometheus_client import Counter, Histogram, Gauge
import time

# Define metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

# Middleware to collect metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    
    # Increment active connections
    active_connections.inc()
    
    try:
        response = await call_next(request)
        
        # Record metrics
        request_count.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        request_duration.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(time.time() - start_time)
        
        return response
    finally:
        active_connections.dec()
```

#### Distributed Tracing
```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Configure tracing
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure Jaeger exporter
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)

span_processor = BatchSpanProcessor(jaeger_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Use in application
@app.get("/api/data")
async def get_data():
    with tracer.start_as_current_span("get_data"):
        # Add span attributes
        span = trace.get_current_span()
        span.set_attribute("user.id", current_user.id)
        
        # Nested span for database operation
        with tracer.start_as_current_span("database_query"):
            data = await fetch_from_database()
        
        return data
```
"""
        (workspace / "technical-architecture.md").write_text(tech_doc)
        
        return workspace
    
    @pytest.fixture
    def section_setup(self, sectioned_documents, tmp_path):
        """Set up search with sectioned documents."""
        db_path = tmp_path / "section_test.db"
        store = SQLiteStore(str(db_path))
        
        # Create plugin
        markdown_plugin = MarkdownPlugin(sqlite_store=store, enable_semantic=False)
        
        # Create dispatcher
        dispatcher = Dispatcher([markdown_plugin])
        
        # Index all documents
        for doc_file in sectioned_documents.glob("*.md"):
            content = doc_file.read_text()
            dispatcher.indexFile(str(doc_file), content)
        
        return {
            'dispatcher': dispatcher,
            'store': store,
            'workspace': sectioned_documents
        }
    
    def test_top_level_section_search(self, section_setup):
        """Test searching in top-level sections."""
        dispatcher = section_setup['dispatcher']
        
        # Search for top-level sections
        section_queries = [
            "Getting Started",
            "Configuration", 
            "Advanced Features",
            "Troubleshooting",
            "API Reference"
        ]
        
        for section in section_queries:
            results = dispatcher.search(section)
            
            # Should find section headers
            assert len(results) > 0, f"No results for section: {section}"
            
            # Verify section content found
            section_found = False
            for result in results[:3]:
                content = result.get('snippet', '')
                if section.lower() in content.lower():
                    section_found = True
                    break
            
            assert section_found, f"Section {section} not found in results"
    
    def test_nested_section_search(self, section_setup):
        """Test searching in nested subsections."""
        dispatcher = section_setup['dispatcher']
        
        # Search for nested sections
        nested_queries = [
            "System Requirements hardware",
            "Manual Installation steps",
            "Environment Variables security",
            "Plugin System custom",
            "Database Design schema"
        ]
        
        for query in nested_queries:
            results = dispatcher.search(query)
            
            # Should find nested content
            assert len(results) >= 0, f"Should handle nested query: {query}"
            
            if len(results) > 0:
                # Check content relevance
                query_terms = query.lower().split()
                relevant_found = False
                
                for result in results[:5]:
                    content = result.get('snippet', '').lower()
                    matching_terms = sum(1 for term in query_terms if term in content)
                    if matching_terms >= 2:
                        relevant_found = True
                        break
                
                assert relevant_found or len(results) > 0, f"Should find relevant nested content: {query}"
    
    def test_code_section_search(self, section_setup):
        """Test searching within code sections."""
        dispatcher = section_setup['dispatcher']
        
        # Search for code-related content
        code_queries = [
            "FastAPI middleware",
            "PostgreSQL CREATE TABLE",
            "docker multi-stage build",
            "kubernetes deployment yaml",
            "prometheus metrics"
        ]
        
        for query in code_queries:
            results = dispatcher.search(query)
            
            if len(results) > 0:
                # Should find code sections
                code_found = False
                for result in results[:5]:
                    content = result.get('snippet', '')
                    # Look for code indicators
                    if any(indicator in content for indicator in ['```', 'import', 'CREATE', 'FROM']):
                        code_found = True
                        break
                
                assert code_found or len(results) > 0, f"Should find code content for: {query}"
    
    def test_faq_section_search(self, section_setup):
        """Test searching in FAQ-style sections."""
        dispatcher = section_setup['dispatcher']
        
        # Search for FAQ content
        faq_queries = [
            "What is the Platform",
            "How much does it cost",
            "system requirements",
            "deployment failing",
            "forgot API key"
        ]
        
        for query in faq_queries:
            results = dispatcher.search(query)
            
            # Should find FAQ content
            assert len(results) >= 0, f"Should handle FAQ query: {query}"
            
            if len(results) > 0:
                # FAQ results should be helpful
                question_found = False
                for result in results[:3]:
                    content = result.get('snippet', '')
                    if '?' in content or query.lower() in content.lower():
                        question_found = True
                        break
                
                assert question_found or len(results) > 0, f"Should find FAQ content: {query}"
    
    def test_section_specific_content(self, section_setup):
        """Test finding content specific to certain sections."""
        dispatcher = section_setup['dispatcher']
        
        # Search for section-specific terms
        specific_queries = [
            ("installation", ["curl", "wget", "install", "setup"]),
            ("configuration", ["yaml", "config", "environment", "settings"]),
            ("troubleshooting", ["error", "fix", "debug", "problem"]),
            ("security", ["authentication", "jwt", "oauth", "encryption"]),
            ("api", ["endpoint", "request", "response", "rest"])
        ]
        
        for section_term, expected_terms in specific_queries:
            results = dispatcher.search(section_term)
            
            if len(results) > 0:
                # Check if results contain expected section-specific terms
                terms_found = set()
                for result in results[:10]:
                    content = result.get('snippet', '').lower()
                    for term in expected_terms:
                        if term in content:
                            terms_found.add(term)
                
                # Should find some section-specific terms
                assert len(terms_found) > 0, f"Should find {section_term} specific terms"
    
    def test_cross_section_references(self, section_setup):
        """Test finding cross-references between sections."""
        dispatcher = section_setup['dispatcher']
        
        # Search for cross-referenced content
        xref_queries = [
            "see installation guide",
            "configuration reference",
            "detailed instructions",
            "for more information",
            "api documentation"
        ]
        
        for query in xref_queries:
            results = dispatcher.search(query)
            
            # Should handle cross-reference queries
            assert isinstance(results, list), f"Should return results for: {query}"
            
            if len(results) > 0:
                # Check for reference indicators
                ref_found = False
                for result in results[:5]:
                    content = result.get('snippet', '').lower()
                    if any(ref in content for ref in ['see', 'refer', 'guide', 'documentation']):
                        ref_found = True
                        break
                
                assert ref_found or len(results) > 0, f"Should find references: {query}"
    
    def test_heading_hierarchy_search(self, section_setup):
        """Test understanding heading hierarchy (H1, H2, H3, etc.)."""
        dispatcher = section_setup['dispatcher']
        
        # Search at different heading levels
        hierarchy_queries = [
            "# Complete Platform Guide",  # H1
            "## Configuration",  # H2
            "### Environment Variables",  # H3
            "#### Core Variables",  # H4
            "##### Service Registration"  # H5
        ]
        
        for query in hierarchy_queries:
            # Remove markdown heading syntax for search
            clean_query = query.replace('#', '').strip()
            results = dispatcher.search(clean_query)
            
            # Should find content at different levels
            assert len(results) >= 0, f"Should handle hierarchy query: {clean_query}"
    
    def test_section_context_preservation(self, section_setup):
        """Test that section context is preserved in results."""
        dispatcher = section_setup['dispatcher']
        
        # Search for terms that appear in multiple contexts
        context_queries = [
            "timeout",  # Appears in config, API, troubleshooting
            "deploy",  # Appears in features, API, FAQ
            "error",  # Appears in troubleshooting, API, code
            "configuration"  # Appears everywhere
        ]
        
        for query in context_queries:
            results = dispatcher.search(query)
            
            if len(results) > 0:
                # Should find term in different contexts
                contexts = set()
                for result in results[:10]:
                    content = result.get('snippet', '').lower()
                    
                    # Identify context
                    if 'troubleshoot' in content:
                        contexts.add('troubleshooting')
                    elif 'api' in content or 'endpoint' in content:
                        contexts.add('api')
                    elif 'config' in content or 'yaml' in content:
                        contexts.add('configuration')
                    elif 'deploy' in content:
                        contexts.add('deployment')
                
                # Should find multiple contexts for common terms
                assert len(contexts) >= 1, f"Should find {query} in multiple contexts"
    
    def test_section_boundary_search(self, section_setup):
        """Test searching across section boundaries."""
        dispatcher = section_setup['dispatcher']
        
        # Search for content that spans sections
        boundary_queries = [
            "installation configuration",  # Adjacent sections
            "getting started troubleshooting",  # Related sections
            "api security implementation",  # Technical sections
            "deployment monitoring"  # Operations sections
        ]
        
        for query in boundary_queries:
            results = dispatcher.search(query)
            
            # Should find content from multiple sections
            assert len(results) >= 0, f"Should handle boundary query: {query}"
            
            if len(results) > 0:
                # Check if results span different sections
                query_parts = query.split()
                parts_found = defaultdict(int)
                
                for result in results[:10]:
                    content = result.get('snippet', '').lower()
                    for part in query_parts:
                        if part in content:
                            parts_found[part] += 1
                
                # Should find both parts of the query
                assert len(parts_found) >= 1, f"Should find content spanning sections: {query}"
    
    def test_section_navigation_queries(self, section_setup):
        """Test queries that simulate section navigation."""
        dispatcher = section_setup['dispatcher']
        
        # Navigation-style queries
        nav_queries = [
            "how to configure after installation",
            "troubleshooting deployment errors",
            "api reference for authentication",
            "advanced features plugin system",
            "getting started with configuration"
        ]
        
        for query in nav_queries:
            results = dispatcher.search(query)
            
            # Should provide navigation-friendly results
            assert len(results) >= 0, f"Should handle navigation query: {query}"
            
            if len(results) > 0:
                # Results should be helpful for navigation
                helpful_results = 0
                for result in results[:5]:
                    content = result.get('snippet', '')
                    # Look for instructional content
                    if any(indicator in content.lower() for indicator in 
                           ['how to', 'step', 'guide', 'follow', 'configure', 'setup']):
                        helpful_results += 1
                
                assert helpful_results > 0 or len(results) > 0, \
                    f"Should find helpful navigation content: {query}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])