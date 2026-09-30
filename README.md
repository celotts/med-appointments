# Agenda Sana

Gestión de citas médicas con asistente de IA **local**. FastAPI + PostgreSQL/pgvector
en el backend, React + Vite en el frontend, Ollama para el LLM y los embeddings.

Ningún dato clínico sale de la máquina.

---

## Empezar

### Con Docker

```bash
cp .env.develop .env          # ajusta SECRET_KEY y la contraseña
make up                       # postgres + api + frontend
make seed                     # catálogos + datos de ejemplo
```

| Servicio | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API | http://localhost:5435 |
| Swagger | http://localhost:5435/docs |
| BD | `localhost:5433` |

Alternativa con Podman: `make up-podman`. Ayuda: `make help`.

### Sin Docker

```bash
docker compose up -d postgres-vector      # solo la BD
cd backend && ./run.sh migrate && ./run.sh serve
cd front && npm install && npm run dev
```

Requiere Ollama con los modelos:

```bash
ollama pull nomic-embed-text
ollama pull llama3.2
```

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 async · asyncpg · Alembic |
| Base de datos | PostgreSQL 16 + pgvector |
| Frontend | React 18 · TypeScript · Vite · Tailwind · react-router |
| IA | Ollama local · `llama3.2` + `nomic-embed-text` · LangChain |
| Auth | JWT (OAuth2 password flow) |

**107 endpoints** en 74 rutas · **40 herramientas** de IA · **8 estados** de cita ·
**6 roles**.

---

## Documentación

**Si vienes a trabajar aquí, empieza por [`AGENTS.md`](AGENTS.md).**

| Documento | Contenido |
|---|---|
| [`AGENTS.md`](AGENTS.md) | **Punto de entrada.** Reglas obligatorias y vocabulario |
| [`TRABAJO_ACUERDO.md`](TRABAJO_ACUERDO.md) | Plan de trabajo y reglas del proyecto |
| [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) | Cómo está organizado el sistema |
| [`docs/API.md`](docs/API.md) | Los 107 endpoints (generado) |
| [`docs/AUDITORIA.md`](docs/AUDITORIA.md) | Registro de quién hizo qué y cuándo |
| [`docs/ESTADOS_CITA.md`](docs/ESTADOS_CITA.md) | Máquina de estados |
| [`docs/IA_AGENTE.md`](docs/IA_AGENTE.md) | RAG y las 40 herramientas |
| [`docs/FRONTEND.md`](docs/FRONTEND.md) | Convenciones del frontend |
| [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md) | Auth, roles y riesgos abiertos |
| [`docs/CONVENCIONES.md`](docs/CONVENCIONES.md) | Cómo se escribe código aquí |
| [`docs/CHECKLIST_ENTREGA.md`](docs/CHECKLIST_ENTREGA.md) | Antes de decir "terminado" |
| [`docs/PENDIENTES.md`](docs/PENDIENTES.md) | Deuda técnica priorizada |
| [`docs/DECISIONES.md`](docs/DECISIONES.md) | ADRs: decisiones ya tomadas |

---

## Comandos

```bash
# Calidad (no necesita Docker)
make verify-docs           # docs vs código: 9 grupos de chequeos
make gen-api-docs          # regenera docs/API.md desde OpenAPI

# Pruebas
make test                  # pytest (API) + typecheck (front)

# Infraestructura
make up / down / logs / ps / shell
make seed                  # datos de prueba
```

---

## Cómo funciona

### Agendar

1. `POST /api/v1/appointments/` crea la cita en `PENDIENTE`.
2. El sistema detecta conflictos de horario y devuelve `409` si el slot está ocupado.
3. Se notifica al paciente.

### Estados

El ciclo de vida es una máquina de estados explícita de 8 estados:

```
PENDIENTE → CONFIRMADA → EN ESPERA → EN PROCESO → ATENDIDA
    ↓           ↓           ↓            ↓
CANCELADA  REAGENDADA  SUSPENDIDA   CANCELADA
```

`ATENDIDA` y `CANCELADA` son terminales. Toda transición pasa por
`VALID_TRANSITIONS` (`backend/app/schemas/appointment.py`).
Detalle en [`docs/ESTADOS_CITA.md`](docs/ESTADOS_CITA.md).

### IA

Dos sistemas distintos:

| Sistema | Ruta | Qué es |
|---|---|---|
| **RAG** | `/api/v1/rag/*` | Búsqueda semántica + agente conversacional con 40 herramientas |
| **Medasist** | `/api/v1/medasist/*` | Lógica de agenda determinista, sin LLM |

Las herramientas que modifican la base de datos exigen confirmación explícita y
respetan la máquina de estados. Detalle en [`docs/IA_AGENTE.md`](docs/IA_AGENTE.md).

---

## Base de datos

El esquema se crea con `script_BD/init.sql` (source of truth) y queda sellado
con una migración baseline. Los cambios posteriores van en migraciones de
Alembic versionadas.

```bash
cd backend
./run.sh migrate                        # upgrade head
venv/bin/python -m alembic heads        # debe haber UN solo head
venv/bin/python -m alembic history
```

> No uses `alembic revision --autogenerate` sobre el baseline: detecta tablas
> no modeladas (`audit_logs`, `waitlist`, `vector_documents`) como eliminadas y
> las borra.

Catálogos en `script_BD/seeds/`:

| Archivo | Contenido |
|---|---|
| `seed_catalogs.sql` | Los 8 estados de cita + especialidades |
| `seed_sample.sql` | Datos de ejemplo |

---

## Estructura

```
.
├── AGENTS.md              # punto de entrada para la IA
├── TRABAJO_ACUERDO.md     # reglas del proyecto
├── backend/
│   ├── app/
│   │   ├── main.py        # FastAPI, 18 routers
│   │   ├── core/          # config, db, security, rbac, crud_*, rag, agent
│   │   ├── api/endpoints/ # 18 routers
│   │   ├── models/        # ORM
│   │   ├── schemas/       # Pydantic
│   │   └── services/      # notifications, prediction, scheduling
│   ├── alembic/versions/  # 10 migraciones, 1 head
│   ├── tests/             # pytest
│   └── run.sh
├── front/
│   └── src/
│       ├── pages/         # 15 páginas
│       ├── components/    # common/ + layout/
│       ├── api/           # 17 módulos + axiosInstance + tokenStorage
│       ├── auth/roles.ts  # roles canónicos
│       └── contexts/
├── script_BD/             # init.sql + seeds
├── scripts/               # verify_docs.py, gen_api_docs.py, seed.sh
└── docs/                  # documentación verificada
```

---

## Seguridad

Autenticación JWT + RBAC de 6 roles. Ver
[`docs/SEGURIDAD.md`](docs/SEGURIDAD.md) para lo corregido y lo pendiente.

**Antes de producción, atender los P0 de
[`docs/PENDIENTES.md`](docs/PENDIENTES.md)**: el endpoint de chat expone
herramientas de escritura SQL a cualquier usuario autenticado, el bloque de
facturación y recetas no filtra por rol, y no hay auditoría de cambios de
estado.

---

## Estado

Funcional: agendar, confirmar, máquina de estados completa, notas clínicas, RAG
con agente de 40 herramientas, notificaciones, reportes, multi-sede, roles.

En desarrollo: auditoría de cambios, rate limiting, tests de frontend, y
limpieza de código muerto. Detalle en [`docs/PENDIENTES.md`](docs/PENDIENTES.md).