# Arquitectura

Mapa del sistema: qué vive dónde, cómo fluye una petición y qué tocar para
cambiar algo.

> Verificado contra el código el 2026-09-30. Si algo no está aquí, no existe.
> `make verify-docs` falla si el documento se desincroniza.

---

## Vista general

```text
┌────────────────────────────────────────────────────────────┐
│  front/  React 18 + TS + Vite + Tailwind + react-router   │
│  15 páginas · sin librería de estado global               │
└───────────────────────┬────────────────────────────────────┘
                        │  HTTP  ·  JWT Bearer
                        │  dev: proxy /api → :5435
                        ▼
┌────────────────────────────────────────────────────────────┐
│  backend/  Python 3.12 · FastAPI (async)                   │
│  18 routers · 104 operaciones · SQLAlchemy AsyncSession    │
└──────┬──────────────┬───────────────┬──────────────────────┘
       │              │               │
       ▼              ▼               ▼
┌────────────┐ ┌────────────┐ ┌──────────────────┐
│ PostgreSQL │ │  Ollama    │ │ Notificaciones   │
│ 16 + pgvec │ │ llama3.2   │ │ (en BD, sin cola)│
└────────────┘ │ nomic-embed│ └──────────────────┘
               └────────────┘
```

Puertos: BD `5433`, API `5435`, front `3000`, Ollama `11434`.

---

## Backend

```
backend/
├── app/
│   ├── main.py                  # FastAPI app; registra los routers
│   ├── initial_data.py          # crea el superusuario en el arranque
│   ├── dependencies.py          # get_db, get_current_user, require_admin
│   ├── api/endpoints/           # routers  (ver docs/API.md)
│   ├── core/
│   │   ├── config.py            # Settings (BaseSettings, lee ../.env)
│   │   ├── db.py                # engine async + SessionLocal
│   │   ├── security.py          # hash de contraseñas, ALGORITHM JWT
│   │   ├── rbac.py              # ★ roles canónicos (ver docs/SEGURIDAD.md)
│   │   ├── crud_*.py            # acceso a datos por entidad
│   │   ├── crud_audit.py        # ★ registro de auditoría
│   │   ├── crud_appointment_audit.py  # ★ transiciones de cita
│   │   ├── rag.py               # ingesta + búsqueda vectorial
│   │   └── agent.py             # agente MedAssist: 40 tools
│   ├── models/                  # ORM SQLAlchemy
│   ├── schemas/                 # Pydantic (validación + respuesta)
│   └── services/                # notifications, prediction, scheduling
├── alembic/versions/            # 10 migraciones, 1 solo head
├── tests/                       # pytest (legacy/ excluido)
├── run.sh                       # serve · test · pytest · migrate · routes
└── requirements.txt
```

### Puntos de entrada

| Archivo | Responsabilidad |
|---|---|
| `main.py` | Registra routers, CORS, startup |
| `dependencies.py` | `get_db`, `get_current_user`, `require_roles` |
| `core/rbac.py` | Vocabulario de roles y comparación normalizada |
| `core/crud_audit.py` | Escritura del registro de auditoría |
| `initial_data.py` | Crea `FIRST_SUPERUSER` al arrancar (idempotente) |

### Capa de datos

- **ORM**: SQLAlchemy 2.x async (`AsyncSession`), driver `asyncpg`.
- **Esquema**: `script_BD/init.sql` crea las tablas; `alembic/versions/` sella el
  baseline y luego evolves.
- **Booleanos en SQL**: ojo. `init.sql` usa `BOOLEAN` pero hay columnas `is_active`
  escritas como `'TRUE'` (texto). Si agregas una consulta, compara contra el tipo
  correcto.

---

## Frontend

```
front/src/
├── main.tsx                 # punto de montage
├── App.tsx                  # BrowserRouter + Toaster
├── routes/AppRoutes.tsx     # 15 rutas bajo ProtectedRoute
├── pages/                   # una página por módulo
├── components/
│   ├── common/              # DataTable, Modal, FilterButtons, Skeleton...
│   └── layout/              # MainLayout, Sidebar, Header, ProtectedRoute
├── api/                     # 17 módulos `xxxApi.ts` + axiosInstance
├── contexts/                # AuthContext, UnsavedChangesContext
├── auth/roles.ts            # ★ roles canónicos (espejo de core/rbac.py)
└── styles/index.css
```

Ver `docs/FRONTEND.md` para convenciones.

---

## Base de datos

Tablas de negocio: `users`, `roles`, `patients`, `doctors`, `specialties`,
`branches`, `consulting_rooms`, `doctor_schedules`, `appointments`,
`appointment_statuses`, `medical_notes`, `medical_histories`, `notifications`,
`waitlist`, `assistant_specialists`, `audit_logs`, `visual_indicator_config`,
`vector_documents`.

Datos de auditoría: `created_at`, `updated_at`, `deleted_at` (soft delete) y
`created_by_user_id` / `updated_by_user_id` / `deleted_by_user_id`.

### Migraciones

```bash
cd backend
./run.sh migrate                      # upgrade head
venv/bin/python -m alembic history    # historial
```

Existe **un solo head** (`d4e1b2f7a915`). Antes había dos, y por eso
`docker-entrypoint.sh` usaba `upgrade heads` (con `s`) mientras el README decía
`upgrade head` (que fallaba).

> **No uses `alembic revision --autogenerate` sobre el baseline**: detecta tablas
> no modeladas (audit, waitlist, vector_documents) como eliminadas y las borra.
> Escribe las migraciones a mano.

---

## IA

Ver `docs/IA_AGENTE.md`. Resumen: Ollama local (`llama3.2` + `nomic-embed-text`),
pgvector para embeddings, agente ReAct con 40 herramientas en `core/agent.py`.

---

## Autenticación y autorización

JWT Bearer. `POST /api/v1/login/access-token` (OAuth2 password flow) →
`{access_token, refresh_token}`.

Cadena de validación: `get_current_user` → JWT válido → usuario existe →
`is_active`. Después, la autorización por rol con `require_admin` /
`require_roles(...)` de `core/rbac.py`.

```python
from core import rbac
from dependencies import require_admin

@router.get("/branches")
async def list_branches(current_user = Depends(require_admin)):
    ...
```

Ver `docs/SEGURIDAD.md`.

---

## Auditoría

Cada transición de cita deja registro en `audit_logs`: estado origen, destino,
actor, motivo y timestamp, en la **misma transacción** que el cambio.

```text
crud_appointment.py
      └── transiciones → crud_appointment_audit.transicionar()
                              ├── valida contra VALID_TRANSITIONS
                              ├── cambia el estado
                              └── crud_audit.registrar_transicion_cita()
                                        └── mismo commit
```

También se auditan reagendamientos, ediciones, borrados, la auto-cancelación por
no-show y los intentos de login (éxito y fallo). Consulta restringida a
administradores en `/api/v1/audit/*`.

Detalle, formato y la trampa de `MissingGreenlet`: `docs/AUDITORIA.md`.

---

## Despliegue

`docker compose up -d` levanta 3 servicios: `postgres-vector`, `medical-rag-api`,
`frontend`.

`backend/docker-entrypoint.sh` al arrancar:
1. Espera a PostgreSQL.
2. `alembic upgrade heads`.
3. Si hay menos de 5000 pacientes, corre `seed_large_dataset.py`.
4. `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

Alternativa con Podman: `make up-podman`. Ayuda: `make help`.

---

## Deuda técnica conocida

Todo en `docs/PENDIENTES.md`. Resumen:

| Área | Deuda |
|---|---|
| Seguridad | `/rag/chat` ejecuta SQL para cualquier usuario autenticado |
| Seguridad | Recetas y facturación sin filtro de rol |
| Auditoría | Cubre citas y login; faltan notas médicas, usuarios y lecturas |
| Tests | 0 tests en el frontend (solo `tsc --noEmit`) |
| Notificaciones | Se crean en la misma request, sin cola ni reintentos |
| i18n | 13 claves definidas, ninguna usada |
| UX | Botón/input sin componente compartido, ~30 duplicados |

---

## Documentos relacionados

| Documento | Contenido |
|---|---|
| `AGENTS.md` | **Punto de entrada para la IA.** Reglas obligatorias |
| `docs/API.md` | Los 107 endpoints |
| `docs/AUDITORIA.md` | Registro de quién hizo qué y cuándo |
| `docs/ESTADOS_CITA.md` | Máquina de estados |
| `docs/IA_AGENTE.md` | RAG y las 40 herramientas |
| `docs/FRONTEND.md` | Convenciones del frontend |
| `docs/SEGURIDAD.md` | Autenticación, roles, riesgos abiertos |
| `docs/CONVENCIONES.md` | Cómo escribir código aquí |
| `docs/CHECKLIST_ENTREGA.md` | Antes de decir "terminado" |
| `docs/PENDIENTES.md` | Deuda técnica priorizada |
| `docs/DECISIONES.md` | ADRs: decisiones ya tomadas |