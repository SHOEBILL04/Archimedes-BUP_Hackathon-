# Smart Campus Energy Optimization Platform - Development Automation Makefile
.PHONY: help dev backend frontend test test-backend test-frontend lint lint-backend lint-frontend format docker-up docker-down migration migrate clean

help: ## Display available commands
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-18s\033[0m %s\n", $$1, $$2}'

dev: ## Run both backend and frontend concurrently for local development
	@echo "Starting development servers..."
	@(trap 'kill 0' SIGINT; make backend & make frontend & wait)

backend: ## Run FastAPI backend development server on port 8000
	@echo "Starting FastAPI backend on http://localhost:8000..."
	@cd backend && .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Run Next.js frontend development server on port 3000
	@echo "Starting Next.js frontend on http://localhost:3000..."
	@cd frontend && npm run dev

test: test-backend test-frontend ## Run all test suites (backend and frontend)

test-backend: ## Run backend unit and API tests with pytest
	@echo "Running backend pytest suite..."
	@cd backend && .venv/bin/pytest tests

test-frontend: ## Run frontend TypeScript validation
	@echo "Running frontend TypeScript type checking..."
	@cd frontend && npx tsc --noEmit

lint: lint-backend lint-frontend ## Run lint checks on backend (ruff) and frontend (eslint)

lint-backend: ## Run Ruff linter on backend
	@echo "Linting backend with ruff..."
	@cd backend && .venv/bin/ruff check app tests alembic

lint-frontend: ## Run ESLint on frontend
	@echo "Linting frontend with eslint..."
	@cd frontend && npm run lint

format: ## Format codebase with ruff
	@echo "Formatting backend with ruff..."
	@cd backend && .venv/bin/ruff format app tests alembic
	@cd backend && .venv/bin/ruff check --fix app tests alembic

migration: ## Generate a new Alembic migration (usage: make migration msg="migration_name")
	@echo "Generating new Alembic revision..."
	@cd backend && .venv/bin/alembic -c alembic.ini revision --autogenerate -m "$(msg)"

migrate: ## Apply latest database migrations (alembic upgrade head)
	@echo "Applying Alembic migrations to SQLite..."
	@cd backend && .venv/bin/alembic -c alembic.ini upgrade head

docker-up: ## Build and start services using Docker Compose
	@echo "Starting Docker Compose services..."
	docker compose up --build -d

docker-down: ## Stop and remove Docker Compose containers
	@echo "Stopping Docker Compose services..."
	docker compose down

clean: ## Clean up build artifacts, caches, and temporary files
	@echo "Cleaning up temporary cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf frontend/.next frontend/out
