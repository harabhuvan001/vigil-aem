.PHONY: install lint format typecheck test test-cov services-up services-down mlflow check
install:
	uv sync --locked
lint:
	uv run --locked ruff check .
	uv run --locked ruff format --check .
format:
	uv run --locked ruff check --fix .
	uv run --locked ruff format .
typecheck:
	uv run --locked mypy
test:
	uv run --locked pytest
test-cov:
	uv run --locked pytest --cov=vigil --cov-report=term-missing --cov-report=xml
services-up:
	docker compose up -d --wait
services-down:
	docker compose down
mlflow:
	uv run --locked mlflow server --host 127.0.0.1 --port 5000 --workers 1 --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlartifacts
check: lint typecheck test
