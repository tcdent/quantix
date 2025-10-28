.PHONY: all build install test test-verbose clean

# Build the Python package
build:
	uv pip install -e .

# Install in development mode with dev dependencies
install: build
	uv pip install -e ".[dev]"

# Run tests with pytest
test:
	uv run pytest tests/ -v

# Run tests with coverage
test-coverage:
	uv run pytest tests/ --cov=pyquantis --cov-report=term-missing

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info .eggs/
	rm -rf src/pyquantis/__pycache__
	rm -rf .pytest_cache .coverage
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Default target
all: build
