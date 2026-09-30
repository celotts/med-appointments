# AGENTS.md

**Punto de entrada para cualquier IA que trabaje en este repositorio.**

Este proyecto tuvo documentación desactualizada durante meses: los `.md`
describían endpoints que no existían, 9 herramientas del agente cuando había 40,
y una máquina de estados con tres vocabularios incompatibles. La IA que leyó esa
documentación falló repetidamente.

**Regla #0: si un documento y el código discrepan, el código gana.** Y si no
puedes verificar algo leyendo el código, no lo afirmes en ninguna respuesta.

---

## Orden de lectura

| # | Documento | Cuándo |
|---|---|---|
| 1 | `TRABAJO_ACUERDO.md` | **Siempre primero.** Reglas obligatorias |
| 2 | `docs/ARQUITECTURA.md` | Cómo está organizado el sistema |
| 3 | El `docs/` del área que toques | Antes de tocar código |
| 4 | `docs/CONVENCIONES.md` | Cómo se escribe código aquí |
| 5 | `docs/CHECKLIST_ENTREGA.md` | Antes de decir "terminado" |

---

## Stack real

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 async · asyncpg · Alembic |
| Base de datos | PostgreSQL 16 + pgvector |
| Frontend | React 18 · TypeScript · Vite 5 · Tailwind 3 · react-router 6 |
| Estado | Context + hooks (sin Redux/Zustand/react-query) |
| IA | Ollama local · `llama3.2` + `nomic-embed-text` · LangChain |
| Auth | JWT (OAuth2 password flow) |

**No hay** Redux, Zustand, react-query, Jest, vitest, Playwright, ESLint ni
Sentry. No los introduzcas sin pedirlo.

---

## Comandos

```bash
# Frontend
make test-front            # tsc --noEmit en contenedor Node 20
cd front && npm run dev    # servidor de desarrollo

# Backend
make test-back             # pytest dentro del contenedor
cd backend && ./run.sh serve
cd backend && ./run.sh routes

# Calidad (ejecutar SIEMPRE antes de entregar)
make verify-docs           # docs vs código: 9 grupos de chequeos
make lint                  # ruff

# Infraestructura
make up                    # postgres + api + frontend
make seed                  # catálogos + datos de ejemplo
make logs / make ps
```

---

## Vocabulario canónico

La IA anterior inventó nombres. Estas son las únicas formas válidas:

### Estados de cita — exactamente 8

```
PENDIENTE · CONFIRMADA · EN ESPERA · EN PROCESO · ATENDIDA · CANCELADA · SUSPENDIDA · REAGENDADA
```

- Fuente: `backend/app/schemas/appointment.py` (enum + `VALID_TRANSITIONS`)
- **Prohibido** `COMPLETADA`, `SCHEDULED`, `CONFIRMED`, `COMPLETED`,
  `CANCELLED`, `NO_SHOW`.
- Detalles: `docs/ESTADOS_CITA.md`

### Roles — exactamente 6

```
SUPER_ADMIN · ADMIN · DOCTOR · SPECIALIST · ASSISTANT · PATIENT
```

```python
# Backend — SIEMPRE así
from core import rbac
from dependencies import require_admin, require_roles

@router.get("/branches", current_user=Depends(require_admin))
def list_branches(...): ...

if rbac.has_role(user, rbac.CLINICAL_ROLES): ...
```

```typescript
// Frontend — SIEMPRE así
import { isAdmin, hasRole, DOCTOR, SPECIALIST } from '../auth/roles';

const admin = isAdmin(user?.role);
```

- **Nunca** `user.role.name == "..."` ni `user?.role === 'admin'`.
- Detalles: `docs/SEGURIDAD.md`

### Nombres de rutas

El backend usa inglés (`/api/v1/appointments`), el dominio usa español
(`citas`, `pacientes`). **No traduzcas rutas existentes.** Ver `docs/API.md`.

### Nombres obsoletos que NO debes reintroducir

| Obsoleto | Correcto |
|---|---|
| `COMPLETADA` | `ATENDIDA` |
| `super_admin` / `admin` (minúsculas) | `SUPER_ADMIN` / `ADMIN` |
| `auth_token` (localStorage) | `access_token` (ver `api/tokenStorage.ts`) |
| `documentos_vectoriales` | `vector_documents` |
| `axiosInstance` con baseURL absoluta | `baseURL: '/api/v1'` |
| `/appointments/ai-reschedule-bulk` | `/appointments/bulk-reschedule` |

---

## Reglas inviolables

1. **Verificar antes de afirmar.** ¿Existe este endpoint? ¿Está en `docs/API.md`?
   Graba el nombre real del archivo, no lo que crees que es.
2. **Nada de secretos en git.** `.env` está en `.gitignore`. Si ves un
   `SECRET_KEY` o una contraseña en un archivo versionado, dilo.
3. **Los datos clínicos solo los ve quien tiene derecho.** Filtra por
   propietario; devuelve `404` en vez de `403` para no revelar existencia.
4. **Toda transición de estado pasa por `VALID_TRANSITIONS`.** No agregues
   transiciones ni endpoints que salten la máquina.
5. **Máximo 250 líneas por módulo nuevo.** Si te pasas, divídelo.
6. **Nada de código muerto.** Si lo escribes, úsalo o bórralo.
7. **`make verify-docs` en verde antes de entregar.** Si falla, el trabajo no
   está terminado.
8. **No inventes features.** Si sobra tiempo, documenta en `docs/PENDIENTES.md`.

---

## Cómo trabajar en cada área

| Área | Lee antes | Recuerda |
|---|---|---|
| Citas / estados | `docs/ESTADOS_CITA.md` | 6 archivos acoplados se actualizan juntos |
| Endpoints | `docs/API.md` | Regenerar con `scripts/gen_api_docs.py` |
| IA / agente | `docs/IA_AGENTE.md` | 40 herramientas, todas en `core/agent.py` |
| Frontend | `docs/FRONTEND.md` | Tokens Tailwind, sin hex sueltos |
| Seguridad | `docs/SEGURIDAD.md` | `require_admin`, nunca comparación manual |

---

## Errores yaPagados

No repetirlos:

- ❌ Introducir un estado sin actualizar enum + semilla + migración + frontend.
- ❌ Comparar roles con literales.
- ❌ `alembic revision --autogenerate` sobre el baseline: borra tablas no
  modeladas (`audit_logs`, `waitlist`, `vector_documents`).
- ❌ Usar `COMPLETADA` en vez de `ATENDIDA`.
- ❌ Crear clases `medical-*` inexistentes en `tailwind.config.js`.
- ❌ Confiar en el `.env` versionado.
- ❌ Escribir documentación sin verificarla contra el código.

---

## Cuando termines

```bash
make verify-docs    # debe salir TODO CORRECTO
make test           # backend + frontend
```

Si `make test` no puede correr porque no hay BD u Ollama, **dilo explícitamente**
en vez de afirmar que funciona. Documentado en `docs/CHECKLIST_ENTREGA.md`.