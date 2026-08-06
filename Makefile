# Makefile para gestionar los contenedores con Docker / Podman

.PHONY: help up down start logs ps clean shell lint format

help:
	@echo "Comandos disponibles:"
	@echo "\n--- Gestión de Contenedores ---"
	@echo "  make up      - Levanta los contenedores en segundo plano"
	@echo "  make down    - Detiene contenedores, elimina redes y volúmenes (-v)"
	@echo "  make start   - Detiene, elimina todo, reconstruye y levanta desde cero"
	@echo "  make logs    - Muestra los logs en tiempo real"
	@echo "  make ps      - Lista el estado de los contenedores"
	@echo "  make clean   - Limpia contenedores y caché de BuildKit huérfanos"
	@echo "\n--- Desarrollo ---"
	@echo "  make shell   - Inicia un shell interactivo en el contenedor de la API"
	@echo "  make lint    - Ejecuta el linter (flake8) en el código de la API"
	@echo "  make format  - Formatea el código de la API con black y isort"

up:
	@echo "Levantando los contenedores..."
	docker compose up -d --build

down:
	@echo "Deteniendo contenedores y eliminando volúmenes..."
	docker compose down -v
	@echo "Deteniendo y eliminando motor BuildKit..."
	docker buildx stop buildx_buildkit_podman 2>/dev/null || true
	docker container prune -f 2>/dev/null || true
	podman rm -f buildx_buildkit_podman 2>/dev/null || true
start: down up

logs:
	@echo "Mostrando los logs de los contenedores..."
	docker compose logs -f

ps:
	@echo "Listando los contenedores..."
	docker compose ps

clean: down
	@echo "Limpiando contenedores detenidos y caché de build..."
	docker system prune -f

shell:
	@echo "Iniciando shell en el contenedor medical_rag_api..."
	docker compose exec medical-rag-api /bin/sh

lint:
	@echo "Ejecutando linter (flake8)..."
	docker compose exec medical-rag-api flake8 backend

format:
	@echo "Formateando el código con black y isort..."
	docker compose exec medical-rag-api black backend
	docker compose exec medical-rag-api isort backend