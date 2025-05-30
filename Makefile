.PHONY: help install test test-unit test-integration test-all lint format clean coverage benchmark security docker

help:
	@echo "Available commands:"
	@echo "  install          Install dependencies"
	@echo "  test            Run unit tests"
	@echo "  test-unit       Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-all        Run all tests with coverage"
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

benchmark:
	pytest tests -v -m benchmark --benchmark-only

security:
	safety check
	bandit -r mcp_server -f json -o bandit-report.json

docker:
	docker build -t mcp-server:latest .