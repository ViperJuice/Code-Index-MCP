#!/bin/bash
# Setup script for repository management development environment

set -e

echo "🚀 Setting up Code-Index-MCP development environment with repository management..."

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create external repositories directory
echo "📁 Creating external repositories directory..."
mkdir -p external_repos

# Create development data directories
echo "📁 Creating development data directories..."
mkdir -p data logs benchmarks repositories

# Set up test repositories
echo "🔧 Setting up test repositories..."
python3 scripts/development/setup_repository_test.py

# Build development container
echo "🏗️ Building development container..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build

echo "✅ Development environment setup complete!"
echo ""
echo "🎯 To start the development environment:"
echo "   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up"
echo ""
echo "🧪 To test repository management features:"
echo "   1. Add reference repository:"
echo "      add_reference_repository({"
echo "        'path': '/external_repos/rust_auth_examples',"
echo "        'language': 'rust',"
echo "        'purpose': 'translation_reference',"
echo "        'days_to_keep': 7"
echo "      })"
echo ""
echo "   2. Index the repository:"
echo "      index_file('/external_repos/rust_auth_examples', {"
echo "        'repository_metadata': {'type': 'reference', 'temporary': true}"
echo "      })"
echo ""
echo "   3. Cross-repository search:"
echo "      search_code('authentication', {"
echo "        'repository_filter': {'group_by_repository': true}"
echo "      })"
echo ""
echo "   4. List repositories:"
echo "      list_repositories({'include_stats': true})"
echo ""
echo "   5. Cleanup when done:"
echo "      cleanup_repositories({'cleanup_expired': true})"
echo ""
echo "📖 See docs/TRANSLATION_WORKFLOW_GUIDE.md for complete workflow examples."