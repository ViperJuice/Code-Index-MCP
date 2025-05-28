#!/bin/bash
set -e

echo "🚀 Post-create: configuring environment"

# Create and activate virtual environment
uv venv
source .venv/bin/activate

# Install Python deps with uv
uv pip install -r requirements.txt

# Confirm tools
echo "✅ Python: $(python --version)"
echo "✅ UV: $(uv --version)"
echo "✅ Claude CLI: $(command -v claude)"
echo "✅ Codex CLI: $(command -v codex)"

echo "✅ Post-create setup complete."
