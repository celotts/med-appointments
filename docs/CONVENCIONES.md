# Convenciones de código

Cómo se escribe en este repositorio. Si algo aquí contradice tu instinto,
gana esto: el proyecto tiene convenciones informales y una IA que las ignora
introduce inconsistencias.

---

## Reglas que no se negocian

| # | Regla | Dónde se verifica |
|---|---|---|
| 1 | Solo los 8 estados canónicos de cita | `make verify-docs` |
| 2 | Solo los 6 roles canónicos, vía `has_role()` | `make verify-docs` |
| 3 | Máximo **250 líneas** por módulo nuevo | Revisión |
| 4 | Cero imports sin usar | `tsc --noEmit`, `ruff` |
| 5 | Cero código muerto | Revisión |
| 6 | Sin secretos en git | `make verify-docs` |
| 7 | Todo `.md` verificado contra el código | `make verify-docs` |
| 8 | Toda transición pasa por `VALID_TRANSITIONS` | Tests |

---

## Backend

### Estructura

```
core/crud_<entidad>.py   # acceso a datos
schemas/<entidad>.py     # Pydantic: entrada y salida
models/<entidad>.py      # ORM
api/endpoints/<nombre>.py # rutas
services/                # lógica que no es CRUD ni ruta
```

Una capa, una responsabilidad. Si un CRUD empieza a decidir reglas de negocio,
muévelo a `services/`.

### Async

Todo es async. No introduzcas llamadas bloqueantes en el event loop.

```python
async def get_appointments(db: AsyncSession) -> list[Appointment]:
    result = await db.execute(select(Appointment))
    return list(result.scalars().all())
```

### Imports

`backend/app` está en el `sys.path` (lo hace `main.py`), así que los imports
son absolutos desde `app/`:

```python
from core import crud_appointment, rbac
from models.user import User as UserModel
from schemas.appointment import AppointmentOut
from dependencies import get_db, require_admin
```

Cuando ejecutas fuera de Docker, el import raíz es `app.*`:

```python
from app.core import rbac          # en tests, scripts, seed_large_dataset
```

### Autorización

```python
from core import rbac
from dependencies import require_admin, require_roles

@router.get("/branches")
async def list_branches(current_user: UserModel = Depends(require_admin)):
    ...

@router.post("/citas")
async def crear(current_user: UserModel = Depends(require_roles(rbac.DOCTOR))):
    ...
```

**Nunca** escribas `if user.role.name == "admin"`. Hubo cuatro vocabularios
incompatibles y por eso los chequeos nunca funcionaron.

Para lógica condicional dentro de la función:

```python
if not rbac.has_role(user, rbac.CLINICAL_ROLES):
    raise HTTPException(status_code=403, detail="No autorizado")
```

### Errores

```python
raise HTTPException(status_code=404, detail="Cita no encontrada")
```

- `404` para un recurso de otro usuario (no reveles que existe).
- `400` para validación de negocio.
- `409` para conflictos (horario ocupado, duplicados).
- `422` lo genera Pydantic automáticamente; no lo lances a mano.

### Módulos nuevos

```python
"""Una línea de qué hace el módulo.

Explica el porqué de las decisiones que no sean obvias.
"""

from __future__ import annotations

import uuid
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core import rbac


async def obtener(db: AsyncSession, id: int) -> Modelo | None:
    """Devuelve el registro o None si no existe."""
    return await db.get(Modelo, id)
```

- `from __future__ import annotations` al principio.
- Docstring en el módulo de una línea.
- Comentarios solo cuando explican **por qué**.

---

## Frontend

### Imports y estructura

Imports relativos (no hay alias `@/` configurado):

```tsx
import { useAuth } from '../contexts/AuthContext';
import { patientApi, Patient } from '../api/patientApi';
import DataTable from '../components/common/DataTable';
import { isAdmin } from '../auth/roles';
```

### Roles

```tsx
const admin = isAdmin(user?.role);
const esMedico = hasRole(user?.role, [DOCTOR, SPECIALIST]);
```

### Tokens

```tsx
className="bg-medical-primary text-white rounded-lg px-4 py-2"
```

Nunca hex sueltos. Si el color no existe, agrégalo a `tailwind.config.js`.

### Colores de estado

Las paletas de `FilterButtons.tsx` usan hex directos
(`#D97706`, `#2563EB`, `#059669`). Es deuda: centralízalas. No copies ese patrón
en código nuevo.

### Tokens de autenticación

```ts
import { getAccessToken, setTokens, clearTokens } from '../api/tokenStorage';
```

No uses `localStorage` para tokens.

### Errores

```tsx
try {
  await patientApi.getAll();
} catch (error: any) {
  toast.error(error.response?.data?.detail?.message || error.response?.data?.detail || 'Error al cargar');
}
```

El manejo de errores vive en quien llama, no en la capa API.

### Tamaño

Máximo **250 líneas**. Si te pasas, extrae:

- Un hook (`use<Cosa>.ts` en el mismo directorio)
- Un componente en `components/`
- Constantes a un módulo aparte

`AppointmentsPage.tsx` tiene 793 líneas y mezcla lista, formulario, modal de
reagendamiento y filtros de IA. Es el ejemplo de lo que hay que evitar.

---

## Comentarios y texto

**En español.** Siempre. Comentarios que expliquen el porqué:

```python
# La migración ff5e6bd85bff sembraba COMPLETADA en vez de ATENDIDA, por eso
# /wait, /start y /attend fallaban: el estado no existia en la BD.
```

```python
# Mal: vuelve a explicar la línea siguiente
# Asigna el total
total_items = response.total
```

---

## Comentarios que explican decisiones no obvias

Cuando arregles algo, deja el porqué en el código. El historial de git no es
consultable desde el archivo, y estos proyectos se mantienen años:

```python
# Nota: el tema de Tailwind definia `medicalText.main` (que genera
# `text-medicalText-main`) mientras el codigo usa `text-medical-textMain`.
# Tailwind no emitia las clases y 130+ estilos se perdian en silencio.
```

---

## Nombres

| Idioma | Qué |
|---|---|
| Inglés | Rutas, tablas, funciones, clases, variables |
| Español | Textos de UI, comentarios, docstrings, mensajes de `detail` |

`/api/v1/appointments` con `"Cita no encontrada"`. No traduzcas las rutas
existentes.

---

## Git

- Commits en inglés, formatoConventional Commits: `feat:`, `fix:`, `refact:`,
  `docs:`, `test:`, `chore:`.
- Un cambio, un commit. No mezcles refactor con feature.
- Antes de commitear: `make verify-docs` y `make test`.

```
feat: add bulk reschedule endpoint
fix: correct appointment status vocabulary
docs: replace IA.md with verified IA_AGENTE.md
refact: extract token storage into single module
```

---

## Migraciones

- **Escríbelas a mano.** No uses `--autogenerate` sobre el baseline: detecta
  tablas no modeladas (`audit_logs`, `waitlist`, `vector_documents`) como
  eliminadas y las borra.
- Deben ser **idempotentes** (`IF NOT EXISTS`, `ON CONFLICT DO NOTHING`).
- `downgrade()` debe existir aunque solo documente que no se revierte.
- Si cambian datos de negocio, el `downgrade` debe explicar por qué no se puede
  revertir.
- Ejecuta `alembic heads`: debe haber **un solo** head.

---

## Al agregar un estado de cita

Seis archivos, en el mismo commit:

1. `backend/app/schemas/appointment.py` — enum y `VALID_TRANSITIONS`
2. `script_BD/seeds/seed_catalogs.sql`
3. La migración de normalización (`c9d2a1e6f304`)
4. `backend/app/core/crud_visual_indicator.py` — `STATUSES_THAT_OCCUPY`, `TERMINAL_STATUSES`
5. `front/src/components/common/AppointmentActions.tsx` — qué botones se muestran
6. `front/src/pages/AppointmentStatusPage.tsx` — etiquetas

`make verify-docs` falla si te saltas el 1 o el 2.

---

## Al agregar un endpoint

1. Ruta en inglés, bajo `/api/v1`.
2. Schema Pydantic para entrada **y** salida.
3. Lógica en `core/crud_*` o `services/`, no en el endpoint.
4. `Depends(require_admin)` si es administrativo.
5. Filtrar por propietario si toca datos clínicos.
6. `response_model` siempre.
7. Docstring con el porqué.
8. Regenerar docs: `python scripts/gen_api_docs.py`.
9. `make verify-docs`.

---

## Al agregar una herramienta del agente

1. Decorador `@tool` en `core/agent.py`.
2. Docstring con descripción y parámetros (LangChain la usa como schema).
3. Si escribe en la BD: parámetro `confirmado: bool = False` y no ejecutar si es
   `False`.
4. Respetar la máquina de estados en las herramientas de transición.
5. Documentarla en `docs/IA_AGENTE.md`.

`make verify-docs` falla si queda sin documentar.