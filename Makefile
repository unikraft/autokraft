.PHONY: lint format check

# Format code with black and isort
format:
	black src/ overall_test.py
	isort src/ overall_test.py

# Run all linters (non-destructive)
lint:
	black --check src/ overall_test.py
	isort --check-only src/ overall_test.py
	pylint src/

# Alias for lint
check: lint
