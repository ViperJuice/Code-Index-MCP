#!/bin/bash
# Start a distributed worker

WORKER_ID=${1:-1}

echo "Starting worker $WORKER_ID..."

cd /app
export PYTHONPATH=/app
export WORKER_ID=$WORKER_ID

python -c "
from mcp_server.distributed.worker.processor import IndexingWorker
worker = IndexingWorker('worker_$WORKER_ID')
worker.start_processing()
"
