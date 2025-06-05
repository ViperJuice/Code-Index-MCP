#!/bin/bash
# Start Phase 5 development environment

echo "🚀 Starting Phase 5 development environment..."

# Start Redis and Qdrant if not already running
if ! pgrep -f redis-server > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes --port 6379
fi

if ! pgrep -f qdrant > /dev/null; then
    echo "Starting Qdrant..."
    docker run -d --name qdrant-dev -p 6333:6333 -p 6334:6334 qdrant/qdrant:latest || echo "Qdrant already running"
fi

echo "✅ Development environment ready!"
echo ""
echo "Available commands:"
echo "  ./scripts/run-parallel-tests.sh  - Run all tests in parallel"
echo "  ./scripts/start-worker.sh 1      - Start a distributed worker"
echo "  python -m mcp_server              - Start MCP server"
echo ""
echo "Development tracks:"
echo "  git checkout feature/phase5-language-plugins"
echo "  git checkout feature/phase5-vector-enhancement" 
echo "  git checkout feature/phase5-distributed"
echo "  git checkout feature/phase5-performance"
