# Medical Appointments RAG API

API contenerizada para la **gestión de citas médicas** (agendar, reagendar, transición de estados, notas clínicas), potenciada con un **agente conversacional RAG** (recuperación aumentada) que consulta la base de datos y documentos vectoriales en lenguaje natural.

- **Backend**: Python 3.14, FastAPI (asíncrono: asyncpg + SQLAlchemy AsyncSession)
- **Base de datos**: PostgreSQL 16 + `pgvector` (contenedor `medical_pgvector`)
- **IA local**: Ollama (`nomic-embed-text` para embeddings, `llama3.2` como LLM) + LangChain
- **Migraciones**: Alembic (schema + seeds versionados)
- **Autenticación**: JWT (OAuth2)

---

## Arquitectura

```
medical_appointments/
│
├── backend/
│   ├── alembic/             # Migraciones de esquema y seeds
│   ├── app/
│   │   ├── api/endpoints/   # Routers (login, users, specialties, medicos,
│   │   │                    #   pacientes, estados-cita, citas, notas, rag)
│   │   ├── core/            # config, db, base, CRUDs, rag, agent
│   │   ├── models/          # ORM (user, role, audit, specialty, medico,
│   │   │                    #   paciente, estado_cita, cita, nota_medica)
│   │   ├── schemas/         # Pydantic
│   │   ├── dependencies.py  # get_db, get_current_user (JWT)
│   │   └── main.py          # App FastAPI + registro de routers
│   ├── tests/               # Smoke tests integrales contra la BD real
│   ├── run.sh               # Script de arranque/verificación
│   └── requirements.txt
│
├── docker-compose.yml       # postgres(pgvector) + api
├── script_BD/init.sql       # Esquema inicial (source-of-truth)
└── .env                     # Variables de entorno (NO versionar)
```

---

## Requisitos

- Docker + Docker Compose (para la BD)
- Ollama corriendo en `http://localhost:11434` con:
  - `nomic-embed-text` (embeddings, 768 dims)
  - `llama3.2` (LLM)
  ```sh
  ollama pull nomic-embed-text
  ollama pull llama3.2
  ```
- Python 3.11+ (venv)

---

## Configuración

Crea un `.env` en la raíz del proyecto:

```env
DATABASE_URL=postgresql+asyncpg://root:fc100711@localhost:5432/appointment

# Primer superusuario (se crea automáticamente al arrancar)
FIRST_SUPERUSER_EMAIL=admin@medapi.com
FIRST_SUPERUSER_PASSWORD=cambia_esta_password

# Seguridad
SECRET_KEY=genera_una_clave_secreta
ACCESS_TOKEN_EXPIRE_SECONDS=90000

# Ollama / RAG (opciones por defecto)
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_EMBEDDING_MODEL=nomic-embed-text
# OLLAMA_LLM_MODEL=llama3.2
```

### Levantar la base de datos

```sh
docker compose up -d db        # o el nombre del servicio del contenedor pgvector
```

---

## Ejecución (backend/run.sh)

```sh
cd backend
./run.sh serve       # API en http://127.0.0.1:8000 (Swagger en /docs)
./run.sh test        # Ejecuta los 4 smoke tests integrales (python -m)
./run.sh pytest      # Idem pero con pytest (pytest-asyncio)
./run.sh migrate     # Aplica migraciones pendientes de Alembic
./run.sh seeds       # Verifica la semilla de estados de cita (idempotente)
./run.sh routes      # Lista todas las rutas de la API
```

> **Nota**: el script invoca módulos con `venv/bin/python -m` porque los shebangs de los binarios del venv están rotos. También carga el `.env` automáticamente.

---

## Migraciones (Alembic)

El esquema se crea inicialmente desde `script_BD/init.sql` y se "sella" con una baseline; los cambios posteriores (incluidos seeds de datos) se gestionan con versiones versionadas:

```sh
cd backend
./run.sh migrate             # upgrade head
venv/bin/python -m alembic revision -m "descripcion"   # nueva migración
venv/bin/python -m alembic history                      # historial
```

> Advertencia: no usar `alembic revision --autogenerate` sobre la baseline, ya que detecta tablas no modeladas como "eliminadas" y las borraría.

---

## Endpoints

Autenticación (Bearer JWT):
- `POST /api/v1/login/access-token`

Catálogos:
- `GET|POST /api/v1/specialties/` · `GET|PUT|DELETE /api/v1/specialties/{id}`
- `GET|POST /api/v1/medicos/` · `GET|PUT|DELETE /api/v1/medicos/{id}`
- `GET|POST /api/v1/pacientes/` · `GET|PUT|DELETE /api/v1/pacientes/{id}`
- `GET /api/v1/estados-cita/`

Núcleo de negocio (citas y notas):
- `GET|POST /api/v1/citas/` — listar/filtrar y **agendar** (detección de conflictos de horario → 409)
- `GET|PUT|DELETE /api/v1/citas/{id}` — **reagendar** (transiciona a `REAGENDADA`)
- `PATCH /api/v1/citas/{id}/estado` — **cambiar estado** (máquina de transiciones válidas)
- `GET|POST /api/v1/notas/` · `GET|PUT|DELETE /api/v1/notas/{id}` — notas médicas (1 por cita)

RAG / AI Agent:
- `GET /api/v1/rag/health` — estado de Ollama + nº de vectores
- `POST /api/v1/rag/ingest` — ingesta de un documento vectorial
- `POST /api/v1/rag/ingest-nota/{cita_id}` — indexa una nota médica existente
- `POST /api/v1/rag/search` — búsqueda semántica por embedding
- `POST /api/v1/rag/chat` — conversación con el agente MedAssist

---

## Agente MedAssist (RAG + Tool Calling)

El endpoint `POST /api/v1/rag/chat` recibe:

```json
{
  "message": "¿Qué citas tiene el médico Rosa Vega?",
  "historial": [{"role": "user", "content": "..."}]
}
```

El agente usa **tool calling** con las herramientas:

| Herramienta | Acción |
|---|---|
| `buscar_en_documentos` | Búsqueda semántica sobre `documentos_vectoriales` |
| `consultar_citas_paciente` / `consultar_citas_medico` | Citas por nombre completo |
| `buscar_pacientes` / `buscar_medicos` | Alta de catálogos por nombre |
| `contar_registros` | Totales de pacientes, médicos, citas, etc. |
| `sugerir_reagendamiento` | Propone reagendar (pide confirmación, no ejecuta) |
| `ejecutar_reagendamiento` | **Ejecuta** el reagendamiento (requiere `confirmado=true`) |
| `cancelar_cita` | **Cancela** la cita (requiere `confirmado=true`) |

Las herramientas de ejecución exigen confirmación explícita del usuario y respetan la máquina de estados (no se puede cancelar/reagendar una cita ya `CANCELADA`/`COMPLETADA`).

---

## Tests

Smoke tests integrales ejecutados contra la BD **real** (no requieren mocks), crean y limpian sus propios datos con sufijos únicos por corrida.

```sh
cd backend
./run.sh test
# o individualmente:
./run.sh test test_citas
# o con pytest (pytest-asyncio, loop de sesión compartido):
./run.sh pytest
```

- `test_specialties.py` — CRUD + auth (401 sin token)
- `test_medicos_pacientes.py` — CRUD + validación FK y unicidad
- `test_citas.py` — agendar/conflicto/reagendar/estados/notas
- `test_rag.py` — RAG, embeddings, búsqueda semántica, chat y herramientas de ejecución

Requisitos de test: BD levantada + Ollama con los modelos descargados.

---

## Estado de las tablas de negocio

Se crean desde `script_BD/init.sql` y quedan selladas en migración. La semilla de `estados_cita` (PENDIENTE, CONFIRMADA, COMPLETADA, CANCELADA, SUSPENDIDA, REAGENDADA) se inserta vía migración.

*Proyecto desarrollado en `develop/python/med-appointments`; hay una rama git `conf/init_backend_appointment`.*
