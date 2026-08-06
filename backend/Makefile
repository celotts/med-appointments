# Makefile para gestionar los contenedores con Podman

.PHONY: up down logs ps

up:
	@echo "Levantando los contenedores con Podman..."
	podman-compose up -d --build

down:
	@echo "Deteniendo los contenedores de Podman..."
	podman-compose down

logs:
	@echo "Mostrando los logs de los contenedores..."
	podman-compose logs -f

ps:
	@echo "Listando los contenedores de Podman..."
	podman-compose ps

