UV := uv
UV_RUN := $(UV) run
COMPOSE_FILE := docker-compose.dev.yaml
COMPOSE := docker compose -f $(COMPOSE_FILE)

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install locked dependencies
	$(UV) sync --locked --all-groups

.PHONY: up
up: ## Build and start compose
	$(COMPOSE) up -d --build --wait

.PHONY: down
down: ## Stop compose
	$(COMPOSE) down

.PHONY: logs
logs: ## Follow compose containers logs
	$(COMPOSE) logs --follow

.PHONY: format
format: ## Format Python files
	$(UV_RUN) ruff check --fix .
	$(UV_RUN) ruff format .

.PHONY: lint
lint: ## Run code-quality checks
	$(UV_RUN) pre-commit run --all-files

.PHONY: test
test: ## Run tests with coverage
	$(UV_RUN) pytest --cov=src

.PHONY: gen-openapi
gen-openapi: ## Generate spec/openapi.yaml from the FastAPI application
	$(UV_RUN) python tools/generate_openapi.py

.PHONY: check-openapi
check-openapi: ## Validate the spec and check that it is up to date
	$(UV_RUN) python tools/generate_openapi.py --check

.PHONY: migrate
migrate: ## Apply all pending database migrations
	$(UV_RUN) alembic upgrade head

.PHONY: migration
migration: ## Generate a migration (usage: make migration message='describe change')
	@test -n "$(message)" || (echo 'message is required' >&2; exit 2)
	$(UV_RUN) alembic revision --autogenerate -m "$(message)"

.PHONY: check
check: lint test ## Run all checks
