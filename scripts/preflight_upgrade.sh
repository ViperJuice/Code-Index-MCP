#!/usr/bin/env bash
# Validate an operator env file against production-config rules before upgrading.
# Usage: ./scripts/preflight_upgrade.sh <env_file_path>
# Exits 0 if no fatal errors; exits 1 with [FATAL]/[WARN] lines on stderr otherwise.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
else
    PYTHON="python3"
fi

exec "$PYTHON" -m mcp_server.cli preflight_env "$1"
