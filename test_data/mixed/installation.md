# Installation Guide

This guide covers various installation methods for the Code Index MCP Server on different platforms and environments.

## Table of Contents

- [System Requirements](#system-requirements)
- [Quick Install](#quick-install)
- [Platform-Specific Instructions](#platform-specific-instructions)
  - [Linux](#linux)
  - [macOS](#macos)
  - [Windows](#windows)
- [Docker Installation](#docker-installation)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Building from Source](#building-from-source)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## System Requirements

Before installing, ensure your system meets these requirements:

- **Operating System**: Linux, macOS 10.14+, or Windows 10+
- **Python**: 3.8 or higher
- **Memory**: Minimum 2GB RAM (4GB+ recommended)
- **Storage**: 500MB for installation + space for indexes
- **Network**: Internet connection for package downloads

Optional requirements:
- Docker 20.10+ (for containerized deployment)
- Redis 6.0+ (for caching)
- PostgreSQL 12+ (for production storage)

## Quick Install

The fastest way to get started:

```bash
pip install code-index-mcp
mcp-server start
```

## Platform-Specific Instructions

### Linux

#### Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Install Python and pip
sudo apt install python3 python3-pip python3-venv

# Install system dependencies
sudo apt install build-essential git

# Install the package
pip3 install code-index-mcp

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify installation
mcp-server --version
```

#### Fedora/RHEL/CentOS

```bash
# Install Python and development tools
sudo dnf install python3 python3-pip python3-devel gcc git

# Install the package
pip3 install --user code-index-mcp

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Start the server
mcp-server start
```

#### Arch Linux

```bash
# Install from AUR
yay -S code-index-mcp

# Or manually
sudo pacman -S python python-pip base-devel git
pip install --user code-index-mcp
```

### macOS

#### Using Homebrew

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Install the package
pip3 install code-index-mcp

# Start the server
mcp-server start
```

#### Manual Installation

```bash
# Download Python from python.org or use pyenv
curl https://pyenv.run | bash

# Add pyenv to PATH
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
source ~/.zshrc

# Install Python
pyenv install 3.11.0
pyenv global 3.11.0

# Install the package
pip install code-index-mcp
```

### Windows

#### Using PowerShell

```powershell
# Install Python from Microsoft Store or python.org
# Open PowerShell as Administrator

# Install the package
pip install code-index-mcp

# Add to PATH if needed
$env:Path += ";$env:APPDATA\Python\Python311\Scripts"

# Verify installation
mcp-server --version
```

#### Using WSL2

```bash
# In WSL2 Ubuntu
sudo apt update
sudo apt install python3 python3-pip
pip3 install code-index-mcp

# Start the server
mcp-server start
```

## Docker Installation

### Using Docker Hub

```bash
# Pull the latest image
docker pull codeindex/mcp-server:latest

# Run the container
docker run -d \
  --name mcp-server \
  -p 8000:8000 \
  -v $(pwd):/workspace \
  -v ~/.mcp:/root/.mcp \
  codeindex/mcp-server:latest
```

### Using Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  mcp-server:
    image: codeindex/mcp-server:latest
    ports:
      - "8000:8000"
    volumes:
      - ./workspace:/workspace
      - ./config:/root/.mcp
    environment:
      - MCP_WORKERS=4
      - MCP_LOG_LEVEL=INFO
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: mcp_index
      POSTGRES_USER: mcp_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  redis-data:
  postgres-data:
```

Run with:

```bash
docker-compose up -d
```

## Kubernetes Deployment

### Using Helm

```bash
# Add the repository
helm repo add codeindex https://charts.codeindex.dev
helm repo update

# Install the chart
helm install mcp-server codeindex/mcp-server \
  --set image.tag=latest \
  --set service.type=LoadBalancer \
  --set persistence.enabled=true \
  --set persistence.size=10Gi
```

### Manual Deployment

Save as `mcp-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-server
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
        image: codeindex/mcp-server:latest
        ports:
        - containerPort: 8000
        env:
        - name: MCP_WORKERS
          value: "4"
        volumeMounts:
        - name: workspace
          mountPath: /workspace
        - name: config
          mountPath: /root/.mcp
      volumes:
      - name: workspace
        persistentVolumeClaim:
          claimName: workspace-pvc
      - name: config
        configMap:
          name: mcp-config

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

Deploy with:

```bash
kubectl apply -f mcp-deployment.yaml
```

## Building from Source

### Prerequisites

- Git
- Python 3.8+ with development headers
- C compiler (gcc/clang)
- Make

### Build Steps

```bash
# Clone the repository
git clone https://github.com/codeindex/mcp-server.git
cd mcp-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install build dependencies
pip install --upgrade pip setuptools wheel
pip install -r requirements-dev.txt

# Build the project
python setup.py build

# Install in development mode
pip install -e .

# Run tests
pytest

# Build distribution packages
python setup.py sdist bdist_wheel
```

## Configuration

After installation, configure the server:

### Create Configuration Directory

```bash
mkdir -p ~/.mcp
cd ~/.mcp
```

### Basic Configuration

Create `config.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4
  
storage:
  type: sqlite
  path: ~/.mcp/index.db
  
indexing:
  batch_size: 100
  ignore_patterns:
    - "*.pyc"
    - "__pycache__"
    - "node_modules"
    - ".git"
    
logging:
  level: INFO
  file: ~/.mcp/server.log
```

### Environment Variables

You can also use environment variables:

```bash
export MCP_PORT=8080
export MCP_WORKERS=8
export MCP_LOG_LEVEL=DEBUG
export MCP_STORAGE_TYPE=postgresql
export MCP_STORAGE_URL=postgresql://user:pass@localhost/mcp_db
```

## Verifying Installation

Run these commands to verify your installation:

```bash
# Check version
mcp-server --version

# Test configuration
mcp-server config test

# Run health check
curl http://localhost:8000/health

# Index a test directory
mcp-cli index /path/to/small/project

# Perform a test search
mcp-cli search "hello world"
```

## Troubleshooting

### Common Issues

#### ImportError: No module named 'mcp_server'

Solution:
```bash
# Ensure pip installed to the correct location
pip show code-index-mcp

# Add to PYTHONPATH if needed
export PYTHONPATH="${PYTHONPATH}:$(pip show code-index-mcp | grep Location | cut -d' ' -f2)"
```

#### Permission Denied Errors

Solution:
```bash
# Install to user directory
pip install --user code-index-mcp

# Or use virtual environment
python -m venv mcp-env
source mcp-env/bin/activate
pip install code-index-mcp
```

#### Port Already in Use

Solution:
```bash
# Find process using port 8000
lsof -i :8000  # On Linux/macOS
netstat -ano | findstr :8000  # On Windows

# Use different port
mcp-server start --port 8080
```

#### Database Connection Failed

Solution:
```bash
# Check database service
systemctl status postgresql  # or redis

# Test connection
psql -h localhost -U mcp_user -d mcp_index

# Use SQLite for testing
export MCP_STORAGE_TYPE=sqlite
```

### Getting Help

If you encounter issues:

1. Check the logs: `tail -f ~/.mcp/server.log`
2. Run in debug mode: `mcp-server start --debug`
3. Check documentation: https://docs.codeindex.dev
4. Search issues: https://github.com/codeindex/mcp-server/issues
5. Join Discord: https://discord.gg/codeindex

## Next Steps

After successful installation:

1. Read the [Quick Start Guide](quickstart.md)
2. Configure your first project
3. Explore the [API Documentation](api-reference.md)
4. Set up IDE integration
5. Join the community

Congratulations! You've successfully installed the Code Index MCP Server. 🎉