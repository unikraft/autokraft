.PHONY: help format lint check test clean install setup-hooks

# Default target
help:
	@echo "Available targets:"
	@echo "  make install       - Install all dependencies"
	@echo "  make setup-hooks   - Set up pre-commit hooks"
	@echo "  make format        - Format code with black and isort"
	@echo "  make lint          - Run pylint on all Python files"
	@echo "  make check         - Check code formatting without modifying files"
	@echo "  make test          - Run all pre-commit checks"
	@echo "  make clean         - Remove cache and temporary files"

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

# Set up pre-commit hooks
setup-hooks:
	@echo "Setting up pre-commit hooks..."
	@chmod +x setup-pre-commit.sh
	@./setup-pre-commit.sh

# Format code with black and isort
format:
	@echo "Formatting code with black..."
	black .
	@echo "Sorting imports with isort..."
	isort .

# Run pylint
lint:
	@echo "Running pylint..."
	pylint src/ overall_test.py

# Check code formatting without modifying
check:
	@echo "Checking code formatting..."
	black --check .
	isort --check-only .
	@echo "All formatting checks passed!"

# Run all pre-commit checks
test:
	@echo "Running all pre-commit checks..."
	pre-commit run --all-files

# Clean up cache and temporary files
clean:
	@echo "Cleaning up cache and temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Cleanup complete!"
