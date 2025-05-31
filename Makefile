.PHONY: help install test test-unit test-integration test-all test-parallel test-interfaces test-plugins test-performance test-resilience lint format clean coverage benchmark security docker

help:
	@echo "Available commands:"
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
	@echo "  clean           Clean up temporary files"
	@echo "  coverage        Generate coverage report"
	@echo "  benchmark       Run performance benchmarks"
	@echo "  security        Run security checks"
	@echo "  docker          Build Docker image"

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