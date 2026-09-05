# Makefile para gestionar los contenedores con Podman Compose

.PHONY: help up down start logs ps clean shell lint format

help:
	@echo "Comandos disponibles:"
	@echo "\n--- Gestión de Contenedores ---"
	@echo "  make up      - Levanta los contenedores en segundo plano"
	@echo "  make down    - Detiene contenedores, elimina redes y volúmenes (-v)"
	@echo "  make start   - Detiene, elimina todo, reconstruye y levanta desde cero"
	@echo "  make logs    - Muestra los logs en tiempo real"
	@echo "  make ps      - Lista el estado de los contenedores"
	@echo "  make clean   - Limpia contenedores y caché huérfanos"
	@echo "\n--- Desarrollo ---"
	@echo "  make shell   - Inicia un shell interactivo en el contenedor de la API"
	@echo "  make lint    - Ejecuta el linter (flake8) en el código de la API"
	@echo "  make format  - Formatea el código de la API con black y isort"

up:
	@echo "Levantando los contenedores..."
	podman-compose up -d --build

down:
	@echo "Deteniendo contenedores y eliminando volúmenes..."
	podman-compose down -v
	@echo "Limpiando contenedores huérfanos..."
	podman container prune -f 2>/dev/null || true

start: down up

logs:
	@echo "Mostrando los logs de los contenedores..."
	podman-compose logs -f

ps:
	@echo "Listando los contenedores..."
	podman-compose ps

clean: down
	@echo "Limpiando sistema de Podman..."
	podman system prune -f

shell:
	@echo "Iniciando shell en el contenedor medical_rag_api..."
	podman-compose exec medical-rag-api /bin/sh

lint:
	@echo "Ejecutando linter (flake8)..."
	podman-compose exec medical-rag-api flake8 backend

format:
	@echo "Formateando el código con black y isort..."
	podman-compose exec medical-rag-api black backend
	podman-compose exec medical-rag-api isort backend