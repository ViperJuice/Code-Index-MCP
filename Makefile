.PHONY: help install test test-unit test-integration test-all test-parallel test-interfaces test-plugins test-performance test-resilience lint format clean coverage benchmark security docker
.PHONY: docker-up docker-down docker-dev docker-prod docker-test docker-logs docker-health
.PHONY: test-dormant test-real-world test-semantic test-redis test-advanced test-cross-lang
.PHONY: setup-env setup-dev-env setup-prod-env backup restore clean-docker

help:
	@echo "Available commands:"
	@echo ""
	@echo "🐍 Python Development:"
	@echo "  install          Install dependencies"
	@echo "  test            Run unit tests"
	@echo "  test-unit       Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-all        Run all tests with coverage"
	@echo "  test-parallel   Run comprehensive parallel test suite"
	@echo "  test-interfaces Test interface compliance"
	@echo "  test-plugins    Test all plugin functionality"
	@echo "  test-performance Test performance and SLOs"
	@echo "  test-resilience Test error handling and edge cases"
	@echo "  lint            Run linters"
	@echo "  format          Format code"
	@echo "  coverage        Generate coverage report"
	@echo "  benchmark       Run performance benchmarks"
	@echo "  security        Run security checks"
	@echo ""
	@echo "🐳 Docker Operations:"
	@echo "  docker          Build Docker image"
	@echo "  docker-up       Start all services"
	@echo "  docker-dev      Start development environment"
	@echo "  docker-prod     Start production environment"
	@echo "  docker-down     Stop all services"
	@echo "  docker-logs     View service logs"
	@echo "  docker-health   Check service health"
	@echo "  docker-test     Run tests in Docker"
	@echo ""
	@echo "🧪 Dormant Features Testing:"
	@echo "  test-dormant    Test all dormant features"
	@echo "  test-real-world Test with real repositories"
	@echo "  test-semantic   Test semantic search"
	@echo "  test-redis      Test Redis caching"
	@echo "  test-advanced   Test advanced indexing"
	@echo "  test-cross-lang Test cross-language features"
	@echo ""
	@echo "🔧 Environment Setup:"
	@echo "  setup-env       Setup basic environment files"
	@echo "  setup-dev-env   Setup development environment"
	@echo "  setup-prod-env  Setup production environment"
	@echo ""
	@echo "💾 Data Management:"
	@echo "  backup          Backup all data"
	@echo "  restore         Restore from backup"
	@echo "  clean           Clean up temporary files"
	@echo "  clean-docker    Clean up Docker resources"

install:
	pip install -r requirements.txt
	pip install -e .

test:
	pytest tests -v -m "not integration and not slow and not benchmark"

test-unit:
	pytest tests -v -m "unit"

test-integration:
	pytest tests -v -m "integration"

test-all:
	pytest tests -v --cov=mcp_server --cov-report=term-missing --cov-report=html

lint:
	black --check mcp_server tests
	isort --check-only mcp_server tests
	flake8 mcp_server tests
	mypy mcp_server
	pylint mcp_server

format:
	black mcp_server tests
	isort mcp_server tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type d -name ".tox" -exec rm -rf {} +
	find . -type f -name "coverage.xml" -delete
	find . -type f -name "coverage.json" -delete

coverage:
	pytest tests --cov=mcp_server --cov-report=term-missing --cov-report=html --cov-report=xml
	@echo "Coverage report generated in htmlcov/index.html"

# Comprehensive parallel testing
test-parallel:
	@echo "🧪 Running comprehensive parallel test suite..."
	python run_parallel_tests.py

test-interfaces:
	@echo "🔧 Testing interface compliance..."
	python run_parallel_tests.py --phases interface_compliance

test-plugins:
	@echo "🔌 Testing plugin functionality..."
	python run_parallel_tests.py --phases plugin_functionality

test-performance:
	@echo "⚡ Testing performance and SLOs..."
	python run_parallel_tests.py --phases performance_validation

test-resilience:
	@echo "🛡️ Testing error handling and resilience..."
	python run_parallel_tests.py --phases resilience_testing

# Individual test components
test-setup:
	@echo "🔧 Setting up test environment..."
	python run_parallel_tests.py --setup-only

benchmark:
	pytest tests -v -m benchmark --benchmark-only --benchmark-autosave

security:
	safety check
	bandit -r mcp_server -f json -o bandit-report.json

docker:
	docker build -t mcp-server:latest .

# Docker operations
docker-up:
	@echo "🐳 Starting Docker services..."
	docker-compose up -d
	@echo "✅ Services started. Check status with: make docker-health"

docker-dev:
	@echo "🐳 Starting Docker development environment..."
	@if [ -z "$$VOYAGE_AI_API_KEY" ]; then \
		echo "⚠️  VOYAGE_AI_API_KEY not set - semantic search will be disabled"; \
	fi
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "✅ Development environment started:"
	@echo "   🌐 MCP Server: http://localhost:8000"
	@echo "   📊 Prometheus: http://localhost:9090"
	@echo "   📈 Grafana: http://localhost:3000 (admin/dev)"
	@echo "   🗄️  Redis Commander: http://localhost:8081"

docker-prod:
	@echo "🐳 Starting Docker production environment..."
	@if [ ! -f .env.production ]; then \
		echo "❌ .env.production not found. Run: make setup-prod-env"; \
		exit 1; \
	fi
	docker-compose --env-file .env.production up -d
	@echo "✅ Production environment started"

docker-down:
	@echo "🐳 Stopping Docker services..."
	docker-compose down
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

docker-logs:
	docker-compose logs -f

docker-health:
	@echo "🔍 Checking service health..."
	@echo "MCP Server:"
	@curl -s http://localhost:8000/health | grep -q '"status":"healthy"' && echo "  ✅ Healthy" || echo "  ❌ Unhealthy"
	@echo "Redis:"
	@docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG" && echo "  ✅ Healthy" || echo "  ❌ Unhealthy"
	@echo "Qdrant:"
	@curl -s http://localhost:6333/health 2>/dev/null | grep -q '"status":"ok"' && echo "  ✅ Healthy" || echo "  ❌ Unhealthy"

docker-test:
	@echo "🧪 Running tests in Docker..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml run --rm test-runner

# Dormant features testing
test-dormant:
	@echo "🧪 Testing dormant features validation..."
	python run_parallel_tests.py --phases dormant_features_validation

test-real-world:
	@echo "🌍 Testing with real-world repositories..."
	python run_parallel_tests.py --phases real_world_validation --setup-real-world

test-semantic:
	@echo "🔍 Testing semantic search (requires VOYAGE_AI_API_KEY)..."
	@if [ -z "$$VOYAGE_AI_API_KEY" ]; then \
		echo "❌ VOYAGE_AI_API_KEY environment variable not set"; \
		echo "   Get your API key from https://www.voyageai.com/"; \
		exit 1; \
	fi
	SEMANTIC_SEARCH_ENABLED=true pytest tests/real_world/test_semantic_search.py -v

test-redis:
	@echo "🗄️ Testing Redis caching (requires Redis server)..."
	@if ! command -v redis-cli >/dev/null 2>&1; then \
		echo "❌ Redis not available. Starting with Docker..."; \
		docker run -d --name test-redis -p 6379:6379 redis:7-alpine; \
		sleep 3; \
	fi
	REDIS_URL=redis://localhost:6379 pytest tests/real_world/test_redis_caching.py -v
	@if docker ps -q -f name=test-redis >/dev/null; then \
		docker stop test-redis && docker rm test-redis; \
	fi

test-advanced:
	@echo "🚀 Testing advanced indexing features..."
	pytest tests/real_world/test_advanced_indexing.py -v

test-cross-lang:
	@echo "🌐 Testing cross-language resolution..."
	pytest tests/real_world/test_cross_language.py -v

# Environment setup
setup-env:
	@echo "🔧 Setting up environment files..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env from .env.example"; \
	else \
		echo "⚠️  .env already exists"; \
	fi

setup-dev-env: setup-env
	@echo "🔧 Setting up development environment..."
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "🔑 To enable semantic search, add your Voyage AI API key:"
	@echo "   export VOYAGE_AI_API_KEY='your-key'"
	@echo "   echo 'VOYAGE_AI_API_KEY=your-key' >> .env"

setup-prod-env:
	@echo "🔧 Setting up production environment..."
	@if [ ! -f .env.production ]; then \
		cp .env.production.example .env.production; \
		echo "✅ Created .env.production from template"; \
		echo "🚨 IMPORTANT: Edit .env.production with production values:"; \
		echo "   - Set secure JWT_SECRET_KEY"; \
		echo "   - Set production VOYAGE_AI_API_KEY"; \
		echo "   - Configure production database"; \
		echo "   - Set proper CORS_ORIGINS"; \
		echo "   - Change default passwords"; \
	else \
		echo "⚠️  .env.production already exists"; \
	fi

# Data management
backup:
	@echo "💾 Creating backup..."
	@mkdir -p backup
	@if docker-compose ps | grep -q redis; then \
		docker run --rm -v mcp_redis-data:/data -v $(PWD)/backup:/backup alpine \
			tar czf /backup/redis-$(shell date +%Y%m%d-%H%M%S).tar.gz -C /data .; \
		echo "✅ Redis data backed up"; \
	fi
	@if docker-compose ps | grep -q qdrant; then \
		docker run --rm -v mcp_qdrant-data:/data -v $(PWD)/backup:/backup alpine \
			tar czf /backup/qdrant-$(shell date +%Y%m%d-%H%M%S).tar.gz -C /data .; \
		echo "✅ Qdrant data backed up"; \
	fi
	@if [ -f ./data/code_index.db ]; then \
		cp ./data/code_index.db ./backup/code_index-$(shell date +%Y%m%d-%H%M%S).db; \
		echo "✅ SQLite database backed up"; \
	fi
	@echo "💾 Backup completed in ./backup/"

restore:
	@echo "📥 Restore functionality - implement based on your backup files"
	@ls -la backup/ 2>/dev/null || echo "No backup directory found"

clean-docker:
	@echo "🧹 Cleaning up Docker resources..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "✅ Docker cleanup completed"