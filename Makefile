VENV := .venv/bin

.PHONY: init dev-install lint format typecheck test check run

init:
	@command -v python3.11 >/dev/null || { echo "python3.11 not found - install it (e.g. 'brew install python@3.11') and retry"; exit 1; }
	python3.11 -m venv .venv
	$(VENV)/pip install --upgrade pip
	$(VENV)/pip install -r requirements-dev.txt

dev-install:
	$(VENV)/pip install -r requirements-dev.txt

lint:
	$(VENV)/ruff check .

format:
	$(VENV)/ruff format .

typecheck:
	$(VENV)/mypy

test:
	$(VENV)/pytest

check: lint typecheck test

run:
	$(VENV)/python -m src
