# Production Deployment Guide

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Architectures](#deployment-architectures)
4. [Deployment Methods](#deployment-methods)
5. [Configuration](#configuration)
6. [Security Considerations](#security-considerations)
7. [Monitoring Setup](#monitoring-setup)
8. [Backup and Recovery](#backup-and-recovery)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

## Overview

This guide provides comprehensive instructions for deploying the MCP Server to production environments. The deployment process is fully automated with multiple safety mechanisms.

### Key Features
- Blue-green deployment for zero downtime
- Automated rollback on failures
- Health checks and smoke tests
- Comprehensive monitoring integration
- Security hardening

## Prerequisites

### Infrastructure Requirements
- Kubernetes cluster (1.24+) or Docker Swarm
- Load balancer (nginx, HAProxy, or cloud LB)
- Persistent storage (50GB minimum)
- SSL/TLS certificates

### Tools Required
- `kubectl` (matching cluster version)
- `docker` CLI (20.10+)
- `helm` (3.0+)
- `jq` for JSON processing
- `curl` for health checks

### Access Requirements
- Kubernetes cluster admin access
- Container registry credentials
- Monitoring system access
- Backup storage access

## Deployment Architectures

### 1. Single Instance (Development)
```yaml
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
┌──────▼──────┐
│ MCP Server  │
│  (Single)   │
└──────┬──────┘
       │
┌──────▼──────┐
│  Database   │
└─────────────┘
```

### 2. High Availability (Production)
```yaml
┌─────────────┐
│ Load Balancer│
└──────┬──────┘
       │
┌──────▼──────────────┐
│   MCP Servers (3+)  │
│  ┌────┐┌────┐┌────┐│
│  │Pod1││Pod2││Pod3││
│  └────┘└────┘└────┘│
└─────────┬───────────┘
          │
┌─────────▼───────────┐
│  Shared Storage &   │
│     Database        │
└─────────────────────┘
```

### 3. Multi-Region
```yaml
Region A              Region B
┌──────────┐         ┌──────────┐
│MCP Cluster│◄──────►│MCP Cluster│
└─────┬────┘         └─────┬────┘
      │                    │
┌─────▼────┐         ┌─────▼────┐
│ Database │◄──────►│ Database │
│ Primary  │         │ Replica  │
└──────────┘         └──────────┘
```

## Deployment Methods

### Method 1: Automated Script Deployment

```bash
# Clone repository
git clone https://github.com/your-org/code-index-mcp.git
cd code-index-mcp

# Run deployment script
VERSION=v1.0.0 ./scripts/deploy-production.sh
```

### Method 2: Kubernetes Manifests

```bash
# Create namespace
kubectl create namespace mcp-system

# Apply configurations
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# Verify deployment
kubectl rollout status deployment/code-index-mcp -n mcp-system
```

### Method 3: Helm Chart

```bash
# Add helm repository
helm repo add mcp https://charts.mcp-server.io
helm repo update

# Install with custom values
helm install mcp-server mcp/code-index-mcp \
  --namespace mcp-system \
  --create-namespace \
  --values production-values.yaml
```

### Method 4: Docker Compose (Single Node)

```bash
# Production deployment
docker-compose -f docker-compose.production.yml up -d

# With monitoring
docker-compose -f docker-compose.production.yml \
               -f docker-compose.monitoring.yml up -d
```

## Configuration

### Environment Variables

```bash
# Core Configuration
DATABASE_URL=postgresql://user:pass@db:5432/mcp
REDIS_URL=redis://redis:6379
LOG_LEVEL=INFO

# Security
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
PASSWORD_MIN_LENGTH=12

# Performance
MAX_WORKERS=4
CACHE_BACKEND=redis
CACHE_DEFAULT_TTL=3600
QUERY_CACHE_ENABLED=true

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=9090
ENABLE_DETAILED_METRICS=true

# Semantic Search (Optional)
VOYAGE_AI_API_KEY=your-voyage-api-key
QDRANT_URL=http://qdrant:6333
ENABLE_SEMANTIC_SEARCH=true
```

### Plugin Configuration

Edit `/app/plugins.yaml`:

```yaml
enabled_languages:
  - python
  - javascript
  - java
  # ... add languages as needed

plugins:
  python:
    enabled: true
    priority: 10
    settings:
      enable_semantic: true
      cache_size: 2000
      max_file_size: 10485760

# System settings
auto_discover: true
enable_hot_reload: false  # Always false in production
max_concurrent_loads: 8
```

### Resource Limits

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

## Security Considerations

### 1. Network Security
```bash
# Restrict ingress
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcp-server-netpol
  namespace: mcp-system
spec:
  podSelector:
    matchLabels:
      app: code-index-mcp
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
EOF
```

### 2. Secrets Management
```bash
# Create sealed secrets
kubectl create secret generic mcp-secrets \
  --from-literal=jwt-secret=$JWT_SECRET \
  --from-literal=db-password=$DB_PASSWORD \
  --dry-run=client -o yaml | kubeseal -o yaml > sealed-secrets.yaml
```

### 3. RBAC Configuration
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: mcp-server-role
  namespace: mcp-system
rules:
- apiGroups: [""]
  resources: ["configmaps", "secrets"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["pods"]
  verbs: ["get", "list"]
```

### 4. Security Scanning
```bash
# Scan image for vulnerabilities
trivy image ghcr.io/your-org/code-index-mcp:v1.0.0

# Runtime security
kubectl apply -f https://raw.githubusercontent.com/falcosecurity/falco/master/deploy/kubernetes/falco-daemonset-configmap.yaml
```

## Monitoring Setup

### 1. Deploy Monitoring Stack
```bash
# Deploy Prometheus & Grafana
docker-compose -f docker-compose.monitoring.yml up -d

# Or with Kubernetes
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace
```

### 2. Configure Alerts
```yaml
# monitoring/prometheus/alerts.yml
groups:
  - name: mcp_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(mcp_errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate detected"
```

### 3. Import Dashboards
1. Access Grafana at http://localhost:3000
2. Go to Dashboards → Import
3. Upload `/monitoring/grafana/dashboards/mcp-server-dashboard.json`

### 4. Configure Notifications
```bash
# Slack notifications
kubectl create secret generic alertmanager-slack \
  --from-literal=webhook-url=$SLACK_WEBHOOK
```

## Backup and Recovery

### 1. Database Backup
```bash
# Automated backup script
cat > /etc/cron.daily/mcp-backup <<EOF
#!/bin/bash
DATE=$(date +%Y%m%d-%H%M%S)
kubectl exec -n mcp-system deployment/code-index-mcp -- \
  sqlite3 /app/data/code_index.db ".backup /backup/mcp-\$DATE.db"
EOF

chmod +x /etc/cron.daily/mcp-backup
```

### 2. Persistent Volume Backup
```bash
# Using Velero
velero install --provider aws --bucket mcp-backups

# Create backup
velero backup create mcp-backup-$(date +%Y%m%d) \
  --include-namespaces mcp-system
```

### 3. Disaster Recovery
```bash
# Restore from backup
velero restore create --from-backup mcp-backup-20240109

# Verify restoration
kubectl get all -n mcp-system
```

## Troubleshooting

### Common Issues

#### 1. Pod Crashes
```bash
# Check logs
kubectl logs -n mcp-system deployment/code-index-mcp --previous

# Describe pod
kubectl describe pod -n mcp-system -l app=code-index-mcp

# Common fixes:
# - Increase memory limits
# - Check database connectivity
# - Verify environment variables
```

#### 2. Slow Performance
```bash
# Check resource usage
kubectl top pods -n mcp-system

# Analyze metrics
curl http://localhost:8000/metrics | grep -E "mcp_request_duration|mcp_memory_usage"

# Solutions:
# - Scale horizontally
# - Enable caching
# - Optimize database queries
```

#### 3. Plugin Loading Failures
```bash
# Check plugin status
curl http://localhost:8000/status | jq '.plugins'

# Verify plugin files
kubectl exec -n mcp-system deployment/code-index-mcp -- ls -la /app/mcp_server/plugins/

# Debug specific plugin
kubectl exec -n mcp-system deployment/code-index-mcp -- \
  python -m mcp_server.plugin_system.cli info python
```

### Debug Mode
```bash
# Enable debug logging
kubectl set env deployment/code-index-mcp LOG_LEVEL=DEBUG -n mcp-system

# Port forward for local debugging
kubectl port-forward -n mcp-system deployment/code-index-mcp 8000:8000
```

## Maintenance

### Regular Tasks

#### Daily
- Monitor error rates and alerts
- Check backup completion
- Review security logs

#### Weekly
- Update dependencies
- Run security scans
- Performance analysis

#### Monthly
- Capacity planning review
- Disaster recovery test
- Documentation updates

### Upgrade Process

```bash
# 1. Backup current state
./scripts/backup-production.sh

# 2. Test in staging
VERSION=v1.1.0 DEPLOYMENT_ENV=staging ./scripts/deploy-production.sh

# 3. Deploy to production
VERSION=v1.1.0 ./scripts/deploy-production.sh

# 4. Verify deployment
./scripts/verify-deployment.sh
```

### Rollback Procedure

```bash
# Automatic rollback (built into deployment script)
ROLLBACK_ON_FAILURE=true ./scripts/deploy-production.sh

# Manual rollback
kubectl rollout undo deployment/code-index-mcp -n mcp-system

# Restore from backup
kubectl apply -f backups/20240109-120000/deployment.yaml
```

## Performance Tuning

### 1. Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX idx_symbols_name ON symbols(name);
CREATE INDEX idx_symbols_file_path ON symbols(file_path);
CREATE INDEX idx_symbols_language ON symbols(language);

-- Vacuum database
VACUUM ANALYZE;
```

### 2. Caching Strategy
```yaml
# Optimize cache settings
CACHE_BACKEND=redis
CACHE_DEFAULT_TTL=7200
QUERY_CACHE_SYMBOL_TTL=3600
QUERY_CACHE_SEARCH_TTL=1800
```

### 3. Horizontal Scaling
```bash
# Scale deployment
kubectl scale deployment/code-index-mcp --replicas=5 -n mcp-system

# Or use HPA
kubectl autoscale deployment/code-index-mcp \
  --min=3 --max=10 --cpu-percent=70 -n mcp-system
```

## Support

### Getting Help
- Documentation: https://docs.mcp-server.io
- Issues: https://github.com/your-org/code-index-mcp/issues
- Slack: #mcp-server-support

### Logs Collection
```bash
# Collect support bundle
kubectl logs -n mcp-system -l app=code-index-mcp --tail=1000 > mcp-logs.txt
kubectl describe all -n mcp-system > mcp-describe.txt
kubectl get events -n mcp-system > mcp-events.txt

# Create archive
tar -czf mcp-support-$(date +%Y%m%d-%H%M%S).tar.gz mcp-*.txt
```

### Reporting Issues
Include:
1. Deployment method used
2. Version information
3. Error messages and logs
4. Steps to reproduce
5. Environment details