# Medical Appointments RAG API

Una API moderna y contenerizada para la gestión de citas médicas, potenciada con capacidades de Generación Aumentada por Recuperación (RAG). Construida con Python, FastAPI y Docker, siguiendo las mejores prácticas de desarrollo de software.

## Características Principales

* **API Moderna**: Construida con FastAPI, ofreciendo alto rendimiento y documentación interactiva automática (Swagger UI y ReDoc).
* **Entorno Contenerizado**: Totalmente gestionado con Docker y Docker Compose para un entorno de desarrollo y despliegue consistente y reproducible.
* **Base de Datos Vectorial**: Utiliza PostgreSQL con la extensión `pgvector` para búsquedas de similitud eficientes, la base para el sistema RAG.
* **Arquitectura Limpia**: Sigue una clara separación de responsabilidades (API, Lógica de Negocio, Acceso a Datos, Modelos).
* **Flujo de Desarrollo Optimizado**: Incluye un `Makefile` con comandos para simplificar las tareas más comunes del ciclo de vida del desarrollo.
* **Operaciones CRUD**: Implementación inicial de endpoints CRUD para gestionar especialidades médicas.

## Tecnologías Utilizadas

* **Backend**: Python 3.11, FastAPI
* **Base de Datos**: PostgreSQL 16, PGVector
* **Contenerización**: Docker, Docker Compose
* **ORM**: SQLAlchemy
* **Validación de Datos**: Pydantic
* **Herramientas de Desarrollo**: Make, Uvicorn

## Estructura del Proyecto

```text
med-appoinments/
│
├── .env
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── README.md
│
└── backend/
    └── app/
        ├── api/
        │   ├── deps.py
        │   └── endpoints/
        │       └── specialties.py
        ├── core/
        │   ├── config.py
        │   └── db.py
        ├── crud/
        │   └── crud_specialty.py
        ├── models/
        │   └── specialty.py
        ├── schemas/
        │   └── specialty.py
        └── main.py
```

## Cómo Empezar

Sigue estos pasos para levantar el entorno de desarrollo local.

### Prerrequisitos

* Docker
* Docker Compose
* `make` (generalmente preinstalado en Linux y macOS)

### 1. Clonar el Repositorio

```sh
git clone <URL_DEL_REPOSITORIO>
cd med-appoinments
```

### 2. Configurar Variables de Entorno

Crea un archivo `.env` a partir de la plantilla de ejemplo y ajústalo si es necesario.

```sh
cp .env.example .env
```

### 3. Levantar los Contenedores

Usa el comando `make` para construir las imágenes y levantar todos los servicios (API y base de datos).

```sh
make up
```

El servicio de la API estará disponible en `http://localhost:8000`.

## Documentación de la API

Una vez que la aplicación esté corriendo, puedes acceder a la documentación interactiva generada automáticamente por FastAPI en las siguientes URLs:

* **Swagger UI**: <http://localhost:8000/docs>
* **ReDoc**: <http://localhost:8000/redoc>

## Comandos de Desarrollo (`Makefile`)

Para facilitar el desarrollo, se han definido los siguientes comandos:

* `make up`: Levanta los contenedores en segundo plano y reconstruye la imagen si hay cambios.
* `make down`: Detiene y elimina los contenedores, redes y volúmenes.
* `make start`: Ejecuta `down` y luego `up` para un reinicio limpio.
* `make logs`: Muestra los logs de los contenedores en tiempo real.
* `make shell`: Inicia una sesión de shell (`/bin/sh`) dentro del contenedor de la API.
* `make format`: Formatea automáticamente el código con `black` y `isort`.
* `make lint`: Ejecuta el linter `flake8` para revisar la calidad del código.
* `make clean`: Detiene todo y limpia el sistema de artefactos de Docker.

---
*Este proyecto fue configurado siguiendo las mejores prácticas para un desarrollo robusto y escalable.*
