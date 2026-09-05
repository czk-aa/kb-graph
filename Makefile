.PHONY: up down migrate test seed dev-backend dev-frontend

up:
	docker compose up -d --build

down:
	docker compose down

migrate:
	docker compose exec backend alembic upgrade head

test:
	cd backend && python -m pytest

seed:
	docker compose exec backend python -m app.tasks.seed

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev
