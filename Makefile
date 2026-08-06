# Makefile para gestionar los contenedores con Docker

.PHONY: help up down logs ps start

help:
	@echo "Comandos disponibles:"
	@echo "  make up    - Levanta los contenedores en segundo plano"
	@echo "  make down  - Detiene y elimina los contenedores"
	@echo "  make logs  - Muestra los logs en tiempo real"
	@echo "  make ps    - Lista el estado de los contenedores"
	@echo "  make start - Detiene, elimina, reconstruye y levanta los contenedores desde cero"

up:
	@echo "Levantando los contenedores con Docker..."
	docker-compose up -d --build

down:
	@echo "Deteniendo los contenedores de Docker..."
	docker-compose down

start: down up

logs:
	@echo "Mostrando los logs de los contenedores..."
	docker-compose logs -f

ps:
	@echo "Listando los contenedores de Docker..."
	docker-compose ps