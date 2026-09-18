# Makefile para gestionar contenedores - Opciones para Docker y Podman
# Compatible con: make containers, make up, make up-test, make down, make start, make logs, make ps, make clean, make shell, make lint, make format, make seed

# ----- SELECTOR INTERACTIVO (Docker / Podman) -----
# Pregunta el motor y la acción, y ejecuta el comando correspondiente
containers:
	@printf "\n=== ¿Con qué motor? ===\n"; \
	printf "  1) Docker\n  2) Podman\n"; \
	printf "Opción [1]: "; read motor; \
	printf "\n=== ¿Qué acción? ===\n"; \
	printf "  1) Levantar\n  2) Bajar\n"; \
	printf "Opción [1]: "; read accion; \
	[ -z "$$motor" ] && motor=1; \
	[ -z "$$accion" ] && accion=1; \
	if [ "$$motor" = "2" ]; then engine="Podman"; compose="podman-compose"; cli="podman"; else engine="Docker"; compose="docker compose"; cli="docker"; fi; \
	if [ "$$accion" = "2" ]; then \
		printf "\n==> Bajando contenedores con %s...\n" "$$engine"; \
		$$compose down -v; \
	else \
		printf "\n¿Cargar datos de prueba? [s/N]: "; read datos; \
		printf "\n==> Levantando contenedores con %s...\n" "$$engine"; \
		$$compose up -d; \
		case "$$datos" in s|S|si|Si|SI) printf "\n==> Cargando datos de prueba...\n"; ./scripts/seed.sh "$$cli" ;; esac; \
	fi

# Alias de `containers`
choose: containers

# ----- OPCIÓN DOCKER -----
# Levanta contenedores con la BD LIMPIA (solo esquema, tablas vacías).
# Usa `make up-test` si quieres los datos de prueba cargados.
up:
	@echo "Levantando contenedores con Docker (imagen cached)..."
	docker compose up -d

# Levanta con rebuild forzado (solo si es absolutamente necesario)
# Nota: El build frontal falla en macOS ARM64 por incompatibilidades Node.js/Tailwind
up-build:
	@echo "Levantando contenedores con rebuild..."
	docker compose up -d --build

# Levanta en MODO PRUEBA: recrea la BD (tablas vacías) y carga los datos de prueba
up-test: down up
	@echo "Cargando datos de prueba..."
	@./scripts/seed.sh docker

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
	@echo "Mostrando los logs de los contenedores..."
	docker compose logs -f

# Estado usando Docker
ps:
	@echo "Listando los contenedores..."
	docker compose ps

# Limpieza completa usando Docker
clean: down
	@echo "Limpiando sistema de Docker..."
	docker system prune -f

# Shell usando Docker
shell:
	@echo "Iniciando shell en el contenedor medical_rag_api..."
	docker compose exec medical-rag-api /bin/sh

# Linter usando Docker
lint:
	@echo "Ejecutando linter (flake8)..."
	docker compose exec medical-rag-api flake8 backend

# Formatear usando Docker
format:
	@echo "Formateando el código con black y isort..."
	docker compose exec medical-rag-api black backend
	docker compose exec medical-rag-api isort backend

# Datos de prueba (catálogos + datos de ejemplo) sobre la BD en ejecución
seed:
	@./scripts/seed.sh docker

# Ejecuta TODAS las pruebas de certificación (backend + front)
test: test-back test-front

# Pruebas de contrato del API (pytest) dentro del contenedor
test-back:
	@echo "==> Backend: asegurando catálogos + pytest en medical_rag_api..."
	docker exec -i medical_pgvector psql -U postgres -d appointment -v ON_ERROR_STOP=1 < script_BD/seeds/seed_catalogs.sql >/dev/null
	docker compose exec -T -w /app medical-rag-api python -m pytest -q

# Typecheck del front (tsc --noEmit) en un contenedor Node 20 aislado
test-front:
	@echo "==> Front: typecheck (tsc) con Node 20..."
	docker run --rm \
		-v "$(CURDIR)/front":/app \
		-v med_front_node_modules:/app/node_modules \
		-w /app node:20-alpine \
		sh -c "npm ci --no-audit --no-fund --silent && npm run typecheck"

# Ejecuta TODAS las pruebas con Podman
test-podman: test-back-podman test-front-podman

test-back-podman:
	@echo "==> Backend: asegurando catálogos + pytest con Podman..."
	podman exec -i medical_pgvector psql -U postgres -d appointment -v ON_ERROR_STOP=1 < script_BD/seeds/seed_catalogs.sql >/dev/null
	podman-compose exec -T -w /app medical-rag-api python -m pytest -q

test-front-podman:
	@echo "==> Front: typecheck (tsc) con Podman y Node 20..."
	podman run --rm \
		-v "$(CURDIR)/front":/app \
		-v med_front_node_modules:/app/node_modules \
		-w /app node:20-alpine \
		sh -c "npm ci --no-audit --no-fund --silent && npm run typecheck"

# Ayuda específica Docker
docker-help:
	@echo "--- Comandos Docker ---"
	@echo "  make up              - Levanta con Docker, BD limpia (tablas vacías)"
	@echo "  make up-test         - Levanta + carga datos de prueba"
	@echo "  make up-build        - Levantar con rebuild (puede fallar)"
	@echo "  make down            - Detiene con Docker"
	@echo "  make start           - Reinicia desde cero"
	@echo "  make logs            - Ver logs en tiempo real"
	@echo "  make ps              - Ver estado de contenedores"
	@echo "  make clean           - Limpieza con Docker"
	@echo "  make shell           - Shell con Docker"
	@echo "  make lint            - Linter con Docker"
	@echo "  make format          - Formateo con Docker"
	@echo "  make seed            - Datos de prueba"
	@echo "  make test            - Pruebas: pytest (API) + typecheck (front)"
	@echo "  make test-back       - Solo pytest del API"
	@echo "  make test-front      - Solo typecheck del front (tsc)"
	@echo "  make test-podman     - Pruebas con Podman"

# ----- OPCIÓN PODMAN -----
# Levanta contenedores usando Podman Compose
up-podman:
	@echo "Levantando contenedores con Podman..."
	podman-compose up -d --build

# Levanta en MODO PRUEBA con Podman: recrea la BD y carga los datos de prueba
up-test-podman: down-podman up-podman
	@echo "Cargando datos de prueba (Podman)..."
	@./scripts/seed.sh podman

# Detiene y limpia usando Podman
down-podman:
	@echo "Deteniendo contenedores con Podman..."
	podman-compose down -v
	@echo "Limpiando contenedores huérfanos..."
	podman container prune -f 2>/dev/null || true

# Reinicia usando Podman
start-podman: down-podman up-podman

# Logs usando Podman
logs-podman:
	@echo "Mostrando los logs con Podman..."
	podman-compose logs -f

# Estado usando Podman
ps-podman:
	@echo "Listando los contenedores con Podman..."
	podman-compose ps

# Limpieza completa usando Podman
clean-podman: down-podman
	@echo "Limpiando sistema de Podman..."
	podman system prune -f

# Shell usando Podman
shell-podman:
	@echo "Shell en contenedor API (Podman)..."
	podman-compose exec medical-rag-api /bin/sh

# Linter usando Podman
lint-podman:
	@echo "Linter con flake8 (Podman)..."
	podman-compose exec medical-rag-api flake8 backend

# Formatear usando Podman
format-podman:
	@echo "Formateando con black e isort (Podman)..."
	podman-compose exec medical-rag-api black backend
	podman-compose exec medical-rag-api isort backend

# Datos de prueba (mismo script)
seed-podman:
	@./scripts/seed.sh podman

# Ayuda específica Podman
podman-help:
	@echo "--- Comandos Podman ---"
	@echo "  make up-podman       - Levantar con Podman"
	@echo "  make up-test-podman  - Levantar con Podman + datos de prueba"
	@echo "  make down-podman     - Detener con Podman"
	@echo "  make start-podman    - Reiniciar con Podman"
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
	@echo "  make containers      - Selector interactivo Docker/Podman (levantar/bajar)"
	@echo "  make up              - Levanta contenedores, BD limpia (tablas vacías)"
	@echo "  make up-test         - Levanta + carga datos de prueba"
	@echo "  make up-build        - Levantar con rebuild (puede fallar)"
	@echo "  make down            - Detiene y limpia"
	@echo "  make start           - Reinicia desde cero"
	@echo "  make logs            - Ver logs en tiempo real"
	@echo "  make ps              - Ver estado de contenedores"
	@echo "  make clean           - Limpiar sistema"
	@echo "  make shell           - Shell interactivo API"
	@echo "  make lint            - Ejecutar flake8"
	@echo "  make format          - Formatear código (black + isort)"
	@echo "  make seed            - Cargar datos de prueba"
	@echo "  make test            - Pruebas: pytest (API) + typecheck (front)"
	@echo ""
	@echo "--- Podman (explicito) ---"
	@echo "  make up-podman       - Levantar con Podman"
	@echo "  make up-test-podman  - Levantar con Podman + datos de prueba"
	@echo "  make down-podman     - Detener con Podman"
	@echo "  make start-podman    - Reiniciar con Podman"
	@echo "  make logs-podman     - Ver logs con Podman"
	@echo "  make ps-podman       - Ver estado con Podman"
	@echo "  make clean-podman    - Limpiar sistema con Podman"
	@echo "  make shell-podman    - Shell en API con Podman"
	@echo "  make lint-podman     - Linter con flake8 (Podman)"
	@echo "  make format-podman   - Formateo con black/isort (Podman)"
	@echo "  make seed-podman     - Cargar datos de prueba"
	@echo ""
	@echo "  make docker-help     - Ver solo comandos Docker"
	@echo "  make podman-help     - Ver solo comandos Podman"
