# Makefile - Common development tasks for LineUp AI

.PHONY: help install setup run test clean format lint coverage dev

# Default target
help:
	@echo "LineUp AI - Development Commands"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install    - Install dependencies"
	@echo "  make setup      - Complete setup (install + config + db)"
	@echo ""
	@echo "Run:"
	@echo "  make run        - Start the server"
	@echo "  make dev        - Start in development mode"
	@echo ""
	@echo "Testing:"
	@echo "  make test       - Run tests"
	@echo "  make coverage   - Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format     - Format code with black"
	@echo "  make lint       - Check code with flake8"
	@echo "  make check      - Run format + lint + test"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean      - Remove temporary files"
	@echo "  make reset      - Reset database"
	@echo ""

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Complete setup
setup:
	@echo "🚀 Running complete setup..."
	python setup.py

# Run the server
run:
	@echo "🚀 Starting LineUp AI..."
	python app_refactored.py

# Development mode (with auto-reload)
dev:
	@echo "🔧 Starting in development mode..."
	FLASK_ENV=development FLASK_APP=app_refactored.py flask run --reload

# Run tests
test:
	@echo "🧪 Running tests..."
	pytest -v

# Run tests with coverage
coverage:
	@echo "📊 Running tests with coverage..."
	pytest --cov=. --cov-report=html --cov-report=term
	@echo "✅ Coverage report generated in htmlcov/"

# Format code
format:
	@echo "✨ Formatting code with black..."
	black *.py tests/
	@echo "✅ Code formatted"

# Lint code
lint:
	@echo "🔍 Linting code with flake8..."
	flake8 *.py tests/ --max-line-length=100 --exclude=venv,__pycache__
	@echo "✅ Linting complete"

# Full check (format + lint + test)
check: format lint test
	@echo "✅ All checks passed!"

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov/ build/ dist/
	@echo "✅ Cleaned"

# Reset database
reset:
	@echo "🗄️  Resetting database..."
	rm -f lineup.db
	@echo "✅ Database removed (will be recreated on next run)"

# Show status
status:
	@echo "📊 LineUp AI Status"
	@echo "=================="
	@python -c "from config import Config; print('Database:', Config.DATABASE_URL); print('Debug:', Config.DEBUG)"
	@echo "Tests: $$(pytest --co -q 2>/dev/null | grep -c test_ || echo 0) test functions"
	@echo "Database: $$([ -f lineup.db ] && echo 'exists' || echo 'not created yet')"

