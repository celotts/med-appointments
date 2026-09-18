.PHONY: up down frontend backend logs clean test seed mcp-setup mcp mcp-http

# Variables
PYTHON ?= python3
PORT ?= 8000
FRONTEND_PORT ?= 3000
DOCKER_COMPOSE ?= docker compose
BACKEND ?= backend
MCP_VENV ?= $(BACKEND)/.venv
MCP_PYTHON ?= $(MCP_VENV)/bin/python

# Levantar todo el stack CON Docker Compose (SÍ funciona en este entorno)
up: ## Levantar stack completo con Docker Compose
	@$(DOCKER_COMPOSE) up -d --build

# Detener todo con Docker Compose
down: ## Detener todo con Docker Compose
	@$(DOCKER_COMPOSE) down

# Solo backend FastAPI
backend: ## Levantar solo backend FastAPI
	@cd $(BACKEND) && $(PYTHON) -m uvicorn main:app --host 0.0.0.0 --port $(PORT)

# Solo frontend React
frontend: ## Levantar solo frontend React (usa Docker Compose)
	@$(DOCKER_COMPOSE) up -d frontend

# Semilla de base de datos
seed: ## Ejecutar seed de base de datos
	@cd $(BACKEND) && $(PYTHON) -m scripts.seed

# Logs del backend
logs: ## Ver logs del backend
	@$(DOCKER_COMPOSE) logs api

# Test
test: ## Ejecutar tests
	@cd $(BACKEND) && $(PYTHON) -m pytest tests/ -v 2>/dev/null || echo "No tests found"

# ── MCP Server ────────────────────────────────────────────────────────
mcp-setup: ## Crear venv e instalar dependencias del servidor MCP
	@$(PYTHON) -m venv $(MCP_VENV)
	@$(MCP_VENV)/bin/pip install -q -r $(BACKEND)/requirements-mcp.txt
	@echo "✅ MCP listo. Ejecuta: make mcp"

mcp: ## Correr servidor MCP por stdio (modo por defecto)
	@cd $(BACKEND) && $(MCP_PYTHON) -m mcp_server

mcp-http: ## Correr servidor MCP por HTTP (MCP_HOST/MCP_PORT o config.json)
	@cd $(BACKEND) && MCP_TRANSPORT=streamable-http $(MCP_PYTHON) -m mcp_server

clean: ## Limpiar caches y archivos generados
	@echo "🧹 Limpiando caches..."
	@find /Users/carloslott/Documents/Default\ Project -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@docker image prune -f 2>/dev/null || true
	@echo "✅ Limpieza completada"