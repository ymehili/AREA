# Root Makefile for AREA monorepo

.DEFAULT_GOAL := help

# Configurable commands/paths
DOCKER ?= docker compose
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
	$(DOCKER) up -d $(if $(S),$(S),$(SERVICES))

.PHONY: down
down: ## Stop and remove containers, networks
	$(DOCKER) down

.PHONY: clean
clean: ## Stop and remove containers, networks, volumes, orphans
	$(DOCKER) down -v --remove-orphans

.PHONY: build
build: ## Build images (S=<service> to scope)
	$(DOCKER) build $(S)

.PHONY: logs
logs: ## Tail logs for all or a single service (S=<service>)
	$(DOCKER) logs -f $(S)

.PHONY: ps
ps: ## List compose services
	$(DOCKER) ps

.PHONY: restart
restart: ## Restart services (S=<service> to scope)
	$(DOCKER) restart $(if $(S),$(S),$(SERVICES))

# -----------------------------
# Mobile (Expo) — local only
# -----------------------------
.PHONY: expo
expo: ## Start Expo locally for the mobile app
	cd $(MOBILE_DIR) && npm install && npm run start

.PHONY: expo-web
expo-web: ## Start Expo in web mode locally
	cd $(MOBILE_DIR) && npm install && npm run web
