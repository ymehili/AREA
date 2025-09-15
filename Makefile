# Root Makefile for AREA monorepo

.DEFAULT_GOAL := help

# Configurable commands/paths
DOCKER ?= docker compose
COMPOSE_BASE := docker-compose.yml
COMPOSE_DEV := docker-compose.dev.yml
WEB_DIR := apps/web
SERVER_DIR := apps/server
MOBILE_DIR := apps/mobile
# Only server and web are managed by docker now
SERVICES := server web

# Usage: make [target]
# You can scope compose targets to a service with S=<service>
# Example: make up S=server

.PHONY: help
help: ## Show this help
	@printf "\nAREA Monorepo — Make targets\n\n"
	@awk 'BEGIN {FS = ":.*?## "}; /^[a-zA-Z0-9_.-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf "\nHints:\n  - Override compose cmd: make DOCKER=\"docker-compose\" up\n  - Scope to one service: make up S=server\n\n"

# -----------------------------
# Docker Compose orchestration
# -----------------------------
.PHONY: up
up: ## Build and start all services in background (S=<service> to scope)
	$(DOCKER) -f $(COMPOSE_BASE) up -d $(if $(S),$(S),$(SERVICES)) --build

.PHONY: down
down: ## Stop and remove containers, networks
	$(DOCKER) -f $(COMPOSE_BASE) down

.PHONY: clean
clean: ## Stop and remove containers, networks, volumes, orphans
	$(DOCKER) -f $(COMPOSE_BASE) down -v --remove-orphans

.PHONY: build
build: ## Build images (S=<service> to scope)
	$(DOCKER) -f $(COMPOSE_BASE) build $(S)

.PHONY: logs
logs: ## Tail logs for all or a single service (S=<service>)
	$(DOCKER) -f $(COMPOSE_BASE) logs -f $(S)

.PHONY: ps
ps: ## List compose services
	$(DOCKER) -f $(COMPOSE_BASE) ps

.PHONY: restart
restart: ## Restart services (S=<service> to scope)
	$(DOCKER) -f $(COMPOSE_BASE) restart $(if $(S),$(S),$(SERVICES))

# -----------------------------
# Dev Compose (hot reload)
# -----------------------------
.PHONY: dev
dev: ## Start dev stack with hot reload (S=<service> to scope)
	$(DOCKER) -f $(COMPOSE_BASE) -f $(COMPOSE_DEV) up -d $(if $(S),$(S),$(SERVICES)) --build

.PHONY: dev-down
dev-down: ## Stop dev stack and remove containers
	$(DOCKER) -f $(COMPOSE_BASE) -f $(COMPOSE_DEV) down

.PHONY: dev-logs
dev-logs: ## Tail dev stack logs (S=<service> to scope)
	$(DOCKER) -f $(COMPOSE_BASE) -f $(COMPOSE_DEV) logs -f $(S)

.PHONY: dev-restart
dev-restart: ## Restart dev services (S=<service> to scope)
	$(DOCKER) -f $(COMPOSE_BASE) -f $(COMPOSE_DEV) restart $(if $(S),$(S),$(SERVICES))

# -----------------------------
# Mobile (Expo) — local only
# -----------------------------
.PHONY: expo
expo: ## Start Expo locally for the mobile app
	cd $(MOBILE_DIR) && npm install && npm run start

.PHONY: expo-web
expo-web: ## Start Expo in web mode locally
	cd $(MOBILE_DIR) && npm install && npm run web
