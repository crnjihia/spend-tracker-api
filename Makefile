# Makefile for Spend Tracker API

.PHONY: install dev test lint format migrate seed up down help

help:
	@echo "Available commands:"
	@echo "  make install  - Install project dependencies with Poetry"
	@echo "  make dev      - Start FastAPI development server with reload"
	@echo "  make test     - Run pytest with code coverage report"
	@echo "  make lint     - Run ruff linter and mypy static type checking"
	@echo "  make format   - Automatically format code with ruff"
	@echo "  make migrate  - Apply latest Alembic database migrations"
	@echo "  make seed     - Seed initial Kenyan system categories"
	@echo "  make up       - Start background Docker Compose services (API, DB, Redis)"
	@echo "  make down     - Stop and remove Docker Compose containers"

install:
	@echo "Installing dependencies..."
	poetry install

dev:
	@echo "Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	@echo "Running test suite with coverage..."
	pytest --cov=app --cov-report=term-missing --cov-report=xml

lint:
	@echo "Running ruff check..."
	ruff check .
	@echo "Running mypy..."
	mypy .

format:
	@echo "Formatting code with ruff..."
	ruff check . --fix
	ruff format .

migrate:
	@echo "Applying Alembic migrations..."
	alembic upgrade head

seed:
	@echo "Seeding default categories..."
	python -m app.db.seed

up:
	@echo "Starting Docker Compose services..."
	docker-compose up -d

down:
	@echo "Stopping Docker Compose services..."
	docker-compose down
