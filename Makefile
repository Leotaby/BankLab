.PHONY: all build data test lint report clean help

# Default target
all: build data test report

# Install package in development mode
build:
	pip install -e ".[dev,analysis]"

# Download and process all data
data:
	python -m banklab.run --stage data

# Run test suite
test:
	pytest tests/ -v --tb=short

# Run linter
lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

# Format code
format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

# Generate analysis report
report:
	python -m banklab.run --stage report

# Clean cached data (keeps processed outputs)
clean:
	rm -rf data/raw/*
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

# Full clean including processed data
clean-all: clean
	rm -rf data/processed/*

# Show help
help:
	@echo "BankLab Makefile Commands:"
	@echo ""
	@echo "  make all       - Full pipeline: build → data → test → report"
	@echo "  make build     - Install package in development mode"
	@echo "  make data      - Download and process all data"
	@echo "  make test      - Run pytest test suite"
	@echo "  make lint      - Run ruff linter"
	@echo "  make format    - Auto-format code with ruff"
	@echo "  make report    - Generate analysis report"
	@echo "  make clean     - Remove cached data and build artifacts"
	@echo "  make clean-all - Remove all data including processed outputs"
	@echo "  make help      - Show this help message"
