PNPM := pnpm
COMPOSE_FILE := docker-compose.dev.yaml
COMPOSE := docker compose -f $(COMPOSE_FILE)

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available targets
	@awk 'BEGIN {FS = ":.*## "; printf "Usage: make <target>\n\n"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install locked dependencies
	$(PNPM) install --frozen-lockfile

.PHONY: up
up: ## Build and start the development container
	$(COMPOSE) up -d --build --wait

.PHONY: down
down: ## Stop the development container
	$(COMPOSE) down

.PHONY: logs
logs: ## Follow development container logs
	$(COMPOSE) logs --follow

.PHONY: dev
dev: ## Start the local Vite development server
	$(PNPM) dev

.PHONY: generate-api
generate-api: ## Generate the API client from the backend OpenAPI schema
	$(PNPM) generate:api

.PHONY: format
format: ## Apply automatic ESLint fixes
	$(PNPM) lint:fix

.PHONY: lint
lint: ## Run ESLint
	$(PNPM) lint

.PHONY: typecheck
typecheck: ## Run TypeScript checks
	$(PNPM) typecheck

.PHONY: build
build: ## Build the production frontend
	$(PNPM) build

.PHONY: check
check: lint typecheck build ## Run all checks
