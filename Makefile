# Makefile para gestionar los contenedores con Docker / Podman

.PHONY: help up down start logs ps clean

help:
	@echo "Comandos disponibles:"
	@echo "  make up    - Levanta los contenedores en segundo plano"
	@echo "  make down  - Detiene contenedores, elimina redes y volúmenes (-v)"
	@echo "  make logs  - Muestra los logs en tiempo real"
	@echo "  make ps    - Lista el estado de los contenedores"
	@echo "  make start - Detiene, elimina todo, reconstruye y levanta desde cero"
	@echo "  make clean - Limpia contenedores y caché de BuildKit huérfanos"

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