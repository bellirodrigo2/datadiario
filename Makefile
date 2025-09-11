.PHONY: install dev test lint flake8 format clean 

install:
	@echo "Instaling dependencies..."
	fastmcp install ./src/mcp.py

dev:
	@echo "Instaling dev dependencies..."
	fastmcp dev ./src/mcp.py

inspector:
	@echo "inspect mcp server..."
	npx @modelcontextprotocol/inspector ./mcp_config.json

test:
	@echo "Running tests..."
	pytest -p no:warnings

lint:
	@echo "Running linter (ruff)..."
	ruff check src

flake8:
	@echo "Running flake8..."
	flake8 src

format:
	@echo "Formatting code (black e isort)..."
	black src
	isort src

clean:
	@echo "Cleaning cache and build/dist related files..."
	@python -c "import shutil, glob, os; [shutil.rmtree(d, ignore_errors=True) for d in ['dist', 'build', '.mypy_cache', '.pytest_cache', '.ruff_cache'] + glob.glob('*.egg-info')]; [shutil.rmtree(os.path.join(r, d), ignore_errors=True) for r, ds, _ in os.walk('.') for d in ds if d == '__pycache__']"
