# =============================================================================
# Smart Campus Service Platform - Makefile
# =============================================================================
# Cross-platform commands for development workflow
# Note: For Windows, install Make from chocolatey or use Git Bash
# =============================================================================

.PHONY: help setup start stop restart logs clean build test migrate seed

# Default target
help:
	@echo "Smart Campus Service Platform - Available Commands:"
	@echo ""
	@echo "  make setup      - Initial setup (copy .env, create directories)"
	@echo "  make git-cleanup - Remove tracked files that should be ignored"
	@echo "  make start      - Start all services"
	@echo "  make stop       - Stop all services"
	@echo "  make restart    - Restart all services"
	@echo "  make logs       - View logs (all services)"
	@echo "  make logs-be    - View backend logs"
	@echo "  make logs-fe    - View frontend logs"
	@echo "  make clean      - Stop and remove all containers, volumes"
	@echo "  make build      - Rebuild all images"
	@echo ""
	@echo "  make migrate    - Run database migrations"
	@echo "  make seed       - Seed initial data"
	@echo "  make db-shell   - Open PostgreSQL shell"
	@echo "  make be-shell   - Open backend shell"
	@echo ""
	@echo "  make test       - Run tests (when implemented)"
	@echo "  make lint       - Run linter"
	@echo ""
	@echo "  make prod-test  - Test production build locally"
	@echo "  (deploy: push to dev/main -> GitHub Actions -> Cloud Run, see DEPLOYMENT.md)"

# =============================================================================
# Setup & Configuration
# =============================================================================

setup:
	@echo "📦 Setting up project..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Created .env file"; \
		echo "⚠️  Please edit .env and set SECRET_KEY!"; \
	else \
		echo "✅ .env already exists"; \
	fi
	@if [ ! -f backend/.env ]; then \
		cp .env.example backend/.env; \
		echo "✅ Created backend/.env file"; \
	fi
	@echo "✅ Setup complete!"

git-cleanup:
	@echo "🧹 Cleaning up git repository..."
	@if command -v pwsh >/dev/null 2>&1; then \
		pwsh -File git-cleanup.ps1; \
	else \
		chmod +x .git-cleanup.sh && ./.git-cleanup.sh; \
	fi

# =============================================================================
# Docker Compose Commands
# =============================================================================

start:
	@echo "🚀 Starting all services..."
	docker-compose up -d
	@echo "✅ Services started!"
	@echo "Frontend: http://localhost:5173"
	@echo "Backend: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/api/v1/docs"

stop:
	@echo "🛑 Stopping all services..."
	docker-compose down
	@echo "✅ Services stopped!"

restart:
	@echo "🔄 Restarting services..."
	docker-compose restart
	@echo "✅ Services restarted!"

logs:
	docker-compose logs -f

logs-be:
	docker-compose logs -f backend

logs-fe:
	docker-compose logs -f frontend

logs-db:
	docker-compose logs -f db

clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v --remove-orphans
	@echo "✅ Cleanup complete!"

build:
	@echo "🔨 Rebuilding images..."
	docker-compose build --no-cache
	@echo "✅ Build complete!"

# =============================================================================
# Database Commands
# =============================================================================

migrate:
	@echo "📊 Running database migrations..."
	docker-compose exec backend alembic upgrade head
	@echo "✅ Migrations complete!"

migrate-create:
	@echo "📝 Creating new migration..."
	@read -p "Migration message: " msg; \
	docker-compose exec backend alembic revision --autogenerate -m "$$msg"

migrate-rollback:
	@echo "⏪ Rolling back last migration..."
	docker-compose exec backend alembic downgrade -1

seed:
	@echo "🌱 Seeding database..."
	docker-compose exec -e SEED_DEMO_DATA=true backend python seed.py
	@echo "✅ Seed complete!"
	@echo ""
	@echo "Default credentials:"
	@echo "  Student: student1@smartcampus.dev / student12345"
	@echo "  Staff:   staff@smartcampus.dev / staff12345"
	@echo "  (admin: set SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD before seeding)"

db-shell:
	@echo "🗄️  Opening PostgreSQL shell..."
	docker-compose exec db psql -U campus_admin -d smart_campus

be-shell:
	@echo "🐍 Opening backend shell..."
	docker-compose exec backend bash

# =============================================================================
# Testing & Quality
# =============================================================================

test:
	@echo "🧪 Running tests..."
	-docker-compose exec db sh -c 'createdb -U "$$POSTGRES_USER" campus_test 2>/dev/null'
	docker-compose exec -e TEST_POSTGRES_DB=campus_test backend pytest
	@echo "✅ Tests complete!"

test-cov:
	@echo "🧪 Running tests with coverage..."
	-docker-compose exec db sh -c 'createdb -U "$$POSTGRES_USER" campus_test 2>/dev/null'
	docker-compose exec -e TEST_POSTGRES_DB=campus_test backend pytest
	@echo "✅ Tests complete! Coverage report: backend/htmlcov/index.html"

lint:
	@echo "🔍 Running linter..."
	docker-compose exec backend ruff check .
	docker-compose exec backend ruff format --check .

lint-fix:
	@echo "🔧 Fixing lint issues..."
	docker-compose exec backend ruff check . --fix
	docker-compose exec backend ruff format .

# =============================================================================
# Production Testing
# =============================================================================

prod-test:
	@echo "🚢 Testing production build locally..."
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build
	@echo "Frontend: http://localhost"
	@echo "Backend: http://localhost:8000"

# =============================================================================
# Development Helpers
# =============================================================================

ps:
	@echo "📋 Service status:"
	docker-compose ps

health:
	@echo "🏥 Checking health..."
	@curl -s http://localhost:8000/healthz | python -m json.tool
	@echo ""
	@curl -s http://localhost:8000/readyz | python -m json.tool

api-docs:
	@echo "📚 Opening API documentation..."
	@echo "Swagger UI: http://localhost:8000/api/v1/docs"
	@echo "ReDoc: http://localhost:8000/api/v1/redoc"

init: setup start migrate seed
	@echo ""
	@echo "✅ Project initialized successfully!"
	@echo ""
	@echo "Access points:"
	@echo "  Frontend: http://localhost:5173"
	@echo "  Backend: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/api/v1/docs"
	@echo ""
	@echo "Default credentials:"
	@echo "  Student: student1@smartcampus.dev / student12345"
	@echo "  Staff:   staff@smartcampus.dev / staff12345"

# =============================================================================
# Windows-specific helpers (use PowerShell)
# =============================================================================

# For Windows users without Make, you can run:
# pwsh -Command "docker-compose up -d"
# pwsh -Command "docker-compose exec backend alembic upgrade head"
# pwsh -Command "docker-compose exec backend python seed.py"
