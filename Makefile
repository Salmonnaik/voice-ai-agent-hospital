.PHONY: up down build test lint migrate seed

up:
	docker compose up --build

down:
	docker compose down -v

build:
	docker compose build

test:
	cd backend && poetry run pytest tests/ -v --tb=short

lint:
	cd backend && poetry run ruff check . && poetry run mypy .

migrate:
	docker compose exec postgres psql -U postgres -d voiceai -f /docker-entrypoint-initdb.d/init.sql

seed:
	cd backend && poetry run python -m scheduler.slot_generator

# Tail logs from all services
logs:
	docker compose logs -f --tail=100

# Scale orchestrator (e.g. make scale-orchestrator N=5)
scale-orchestrator:
	docker compose up -d --scale orchestrator=$(N)

# Load test (requires k6 installed)
loadtest:
	k6 run tests/load/call_simulation.js --vus 100 --duration 5m
