# Makefile para gestionar contenedores - Opciones para Docker y Podman
# Compatible con: make up, make up-prueba, make down, make start, make logs, make ps, make clean, make shell, make lint, make format, make seed

# ----- OPCIÓN DOCKER -----
# Levanta contenedores usando Docker Compose
up:
	@echo "Levantando contenedores con Docker..."
	docker compose up -d --build

# Detiene y limpia usando Docker
down:
	@echo "Deteniendo contenedores con Docker..."
	docker compose down -v
	@echo "Limpiando contenedores huérfanos..."
	docker container prune -f 2>/dev/null || true

# Reinicia desde cero usando Docker
start: down up

# Logs usando Docker
logs:
	@echo "Mostrando logs con Docker..."
	docker compose logs -f

# Estado usando Docker
ps:
	@echo "Listando contenedores con Docker..."
	docker compose ps

# Limpieza completa usando Docker
clean: down
	@echo "Limpiando sistema de Docker..."
	docker system prune -f

# Shell usando Docker
shell:
	@echo "Shell en contenedor API (Docker)..."
	docker compose exec medical-rag-api /bin/sh

# Linter usando Docker
lint:
	@echo "Linter con flake8 (Docker)..."
	docker compose exec medical-rag-api flake8 backend

# Formatear usando Docker
format:
	@echo "Formateando con black e isort (Docker)..."
	docker compose exec medical-rag-api black backend
	docker compose exec medical-rag-api isort backend

# Datos de prueba
seed:
	@./scripts/seed.sh

# Ayuda específica Docker
docker-help:
	@echo "--- Comandos Docker ---"
	@echo "  make up              - Levanta con Docker"
	@echo "  make down            - Detiene con Docker"
	@echo "  make start           - Reinicia con Docker"
	@echo "  make logs            - Logs con Docker"
	@echo "  make ps              - Estado con Docker"
	@echo "  make clean           - Limpieza con Docker"
	@echo "  make shell           - Shell con Docker"
	@echo "  make lint            - Linter con Docker"
	@echo "  make format          - Formateo con Docker"
	@echo "  make seed            - Datos de prueba"

# ----- OPCIÓN PODMAN -----
# Levanta contenedores usando Podman Compose
up-podman:
	@echo "Levantando contenedores con Podman..."
	podan-compose up -d --build

# Detiene y limpia usando Podman
down-podman:
	@echo "Deteniendo contenedores con Podman..."
	podan-compose down -v
	@echo "Limpiando contenedores huérfanos..."
	podan container prune -f 2>/dev/null || true

# Reinicia usando Podman
start-podman: down-podman up-podman

# Logs usando Podman
logs-podman:
	@echo "Mostrando logs con Podman..."
	podan-compose logs -f

# Estado usando Podman
ps-podman:
	@echo "Listando contenedores con Podman..."
	podan-compose ps

# Limpieza completa usando Podman
clean-podman: down-podman
	@echo "Limpiando sistema de Podman..."
	podan system prune -f

# Shell usando Podman
shell-podman:
	@echo "Shell en contenedor API (Podman)..."
	podan-compose exec medical-rag-api /bin/sh

# Linter usando Podman
lint-podman:
	@echo "Linter con flake8 (Podman)..."
	podan-compose exec medical-rag-api flake8 backend

# Formatear usando Podman
format-podman:
	@echo "Formateando con black e isort (Podman)..."
	podan-compose exec medical-rag-api black backend
	podan-compose exec medical-rag-api isort backend

# Datos de prueba (mismo script)
seed-podman:
	@./scripts/seed.sh

# Ayuda específica Podman
podman-help:
	@echo "--- Comandos Podman ---"
	@echo "  make up-podman       - Levanta con Podman"
	@echo "  make down-podman     - Detiene con Podman"
	@echo "  make start-podman    - Reinicia con Podman"
	@echo "  make logs-podman     - Logs con Podman"
	@echo "  make ps-podman       - Estado con Podman"
	@echo "  make clean-podman    - Limpieza con Podman"
	@echo "  make shell-podman    - Shell con Podman"
	@echo "  make lint-podman     - Linter con Podman"
	@echo "  make format-podman   - Formateo con Podman"
	@echo "  make seed-podman     - Datos de prueba"

# Ayuda general
help:
	@echo "=== Makefile: Gestión de Contenedores ==="
	@echo ""
	@echo "--- Por defecto (Docker) ---"
	@echo "  make up              - Levanta contenedores"
	@echo "  make down            - Detiene y limpia"
	@echo "  make start           - Reinicia desde cero"
	@echo "  make logs            - Ver logs en tiempo real"
	@echo "  make ps              - Ver estado de contenedores"
	@echo "  make clean           - Limpiar sistema"
	@echo "  make shell           - Shell interactivo API"
	@echo "  make lint            - Ejecutar flake8"
	@echo "  make format          - Formatear código (black + isort)"
	@echo "  make seed            - Cargar datos de prueba"
	@echo ""
	@echo "--- Podman (explicito) ---"
	@echo "  make up-podman       - Levantar con Podman"
	@echo "  make down-podman     - Detener con Podman"
	@echo "  make start-podman    - Reiniciar con Podman"
	@echo "  make logs-podman     - Ver logs con Podman"
	@echo "  make ps-podman       - Ver estado con Podman"
	@echo "  make clean-podman    - Limpiar sistema con Podman"
	@echo "  make shell-podman    - Shell en API con Podman"
	@echo "  make lint-podman     - Linter con flake8 (Podman)"
	@echo "  make format-podman   - Formatear con black/isort (Podman)"
	@echo "  make seed-podman     - Cargar datos de prueba"
	@echo ""
	@echo "  make docker-help     - Ver solo comandos Docker"
	@echo "  make podman-help     - Ver solo comandos Podman"
