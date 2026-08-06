.PHONY: all up down build start stop restart logs ps clean

# Define the path to the docker-compose.yml file.
# This assumes the Makefile is in the backend directory alongside docker-compose.yml
COMPOSE_FILE := docker-compose.yml
# Define a project name for docker-compose.
# This helps isolate resources for this project.
COMPOSE_PROJECT_NAME := medical-app

# Default target
all: up

# Build, create, and start containers
up:
	@echo "Bringing up containers..."
	@docker-compose -f $(COMPOSE_FILE) -p $(COMPOSE_PROJECT_NAME) up --build -d

# Stop and remove containers, networks, and volumes
down:
	@echo "Bringing down containers..."
	@docker-compose -f $(COMPOSE_FILE) -p $(COMPOSE_PROJECT_NAME) down -v

# Build or rebuild services
build:
	@echo "Building containers..."
	@docker-compose -f $(COMPOSE_FILE) -p $(COMPOSE_PROJECT_NAME) build

# Start existing containers
start:
	@echo "Starting containers..."
	@docker-compose -f $(COMPOSE_FILE) -p $(COMPOSE_PROJECT_NAME) start

# Stop running containers
stop:
	@echo "Stopping containers..."
	@docker-compose -f $(COMPOSE_FILE) -p $(COMPOSE_PROJECT_NAME) stop

# Restart containers
restart:
	@echo "Restarting containers..."
	@docker-compose -f $(COMPOSE_FILE) -p $(COMPOSE_PROJECT_NAME) restart

# View output from containers
logs:
	@echo "Viewing container logs (press Ctrl+C to exit)..."
	@docker-compose -f $(COMPOSE_FILE) -p $(COMPOSE_PROJECT_NAME) logs -f

# List containers
ps:
	@echo "Listing containers..."
	@docker-compose -f $(COMPOSE_FILE) -p $(COMPOSE_PROJECT_NAME) ps

# Remove all stopped containers, dangling images, and unused networks/volumes
clean:
	@echo "Cleaning up Docker Compose resources (containers, networks, volumes, images)..."
	@docker-compose -f $(COMPOSE_FILE) -p $(COMPOSE_PROJECT_NAME) down -v --rmi all
	@echo "Cleanup complete. If you experience issues, consider 'docker system prune' or 'podman system prune' with caution."
