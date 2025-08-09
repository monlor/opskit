# OpsKit Test and Development Makefile

.PHONY: help test test-unit test-integration test-all test-coverage test-fast test-slow clean install-dev lint format security check-all

# Default target
help:
	@echo "OpsKit Development Commands:"
	@echo ""
	@echo "Testing:"
	@echo "  test          - Run all tests (unit + integration)"
	@echo "  test-unit     - Run only unit tests"
	@echo "  test-integration - Run only integration tests"
	@echo "  test-coverage - Run tests with coverage report"
	@echo "  test-fast     - Run fast tests only (exclude slow tests)"
	@echo "  test-slow     - Run all tests including slow ones"
	@echo "  test-core     - Test only core modules"
	@echo "  test-common   - Test only common libraries"
	@echo "  test-tools    - Test only tool execution"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          - Run linting (flake8, black, isort, mypy)"
	@echo "  format        - Format code (black, isort)"
	@echo "  security      - Run security checks (bandit, safety)"
	@echo "  check-all     - Run all checks (lint + security + tests)"
	@echo ""
	@echo "Development:"
	@echo "  install-dev   - Install development dependencies"
	@echo "  clean         - Clean up generated files"
	@echo ""

# Testing targets
test:
	python run_tests.py

test-unit:
	python run_tests.py --unit

test-integration:
	python run_tests.py --integration

test-coverage:
	python run_tests.py --coverage --html-coverage

test-fast:
	python run_tests.py

test-slow:
	python run_tests.py --slow

test-core:
	python run_tests.py --core

test-common:
	python run_tests.py --common

test-tools:
	python run_tests.py --tools

test-python:
	python run_tests.py --python

test-shell:
	python run_tests.py --shell

test-parallel:
	python run_tests.py --parallel 4

# Code quality targets
lint:
	@echo "Running flake8..."
	flake8 core/ common/python/ --max-line-length=100 --extend-ignore=E203,W503 || true
	@echo "Running black check..."
	black --check --diff core/ common/python/ || true
	@echo "Running isort check..."
	isort --check-only --diff core/ common/python/ || true
	@echo "Running mypy..."
	mypy core/ common/python/ --ignore-missing-imports || true

format:
	@echo "Formatting with black..."
	black core/ common/python/
	@echo "Sorting imports with isort..."
	isort core/ common/python/

security:
	@echo "Running bandit security checks..."
	bandit -r core/ common/python/ || true
	@echo "Running safety dependency checks..."
	safety check || true

check-all: lint security test

# Development targets
install-dev:
	@echo "Installing development dependencies..."
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-mock pytest-timeout pytest-xdist pytest-benchmark
	pip install flake8 black isort mypy bandit safety

clean:
	@echo "Cleaning up generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf tests/coverage_html/ tests/coverage.xml tests/.coverage 2>/dev/null || true
	rm -rf .pytest_cache/ .mypy_cache/ 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/ 2>/dev/null || true
	rm -f security-report.json safety-report.json 2>/dev/null || true

# Development workflow shortcuts
dev-setup: install-dev
	@echo "Development environment setup complete!"

dev-check: format lint security test-fast
	@echo "Development checks complete!"

ci-test: test-coverage security
	@echo "CI test suite complete!"

# Benchmark and performance testing
benchmark:
	python run_tests.py -k "benchmark or performance" --timeout 900

# Tool-specific testing
test-mysql-sync:
	python run_tests.py tests/integration/tools/ -k "mysql"

test-system-info:
	python run_tests.py tests/integration/tools/ -k "system_info"

test-disk-usage:
	python run_tests.py tests/integration/tools/ -k "disk_usage"

test-port-scanner:
	python run_tests.py tests/integration/tools/ -k "port_scanner"

# Debug testing
test-debug:
	python run_tests.py --pdb -v

test-last-failed:
	python run_tests.py --lf

test-failed-first:
	python run_tests.py --ff

# Documentation
docs:
	@echo "Generating documentation..."
	@echo "API documentation would be generated here"

# Release preparation
pre-release: clean format lint security test-all
	@echo "Pre-release checks complete!"