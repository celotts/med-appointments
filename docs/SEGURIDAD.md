# Seguridad

Autenticación, autorización y riesgos abiertos. Verificado el 2026-09-30.

---

## Autenticación

JWT Bearer, OAuth2 password flow.

```http
POST /api/v1/login/access-token
Content-Type: application/x-www-form-urlencoded

username=admin@medapp.com&password=...
```

```json
{ "access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer" }
```

Cadena de validación (`get_current_user` en `backend/app/dependencies.py`):

1. El JWT decodifica con `SECRET_KEY`.
2. El `sub` es un UUID válido.
3. El usuario existe.
4. `user.is_active` es verdadero.

**No** valida rol. Eso lo hace `require_admin` / `require_roles`.

Sin token → `401`. Token válido sin permiso → `403`.

### Endpoints sin protección

Solo dos:

| Ruta | Por qué |
|---|---|
| `GET /` | Health check |
| `GET /me` | Requiere token pero no rol |

---

## Autorización: RBAC

Fuente de verdad: **`backend/app/core/rbac.py`**, espejada en
`front/src/auth/roles.ts`.

### Los 6 roles

| Rol | Alcance |
|---|---|
| `SUPER_ADMIN` | Todo |
| `ADMIN` | Administración de la clínica |
| `DOCTOR` | Sus propias citas |
| `SPECIALIST` | Médico especialista |
| `ASSISTANT` | Agenda y pacientes |
| `PATIENT` | Solo sus propias citas y notas |

### Uso correcto

```python
from core import rbac
from dependencies import require_admin, require_roles, get_current_user

@router.get("/branches")
async def list_branches(current_user = Depends(require_admin)):
    ...

@router.post("/x")
async def crear(current_user = Depends(require_roles(rbac.DOCTOR, rbac.SPECIALIST)):
    ...

# Verificación condicional
if not rbac.has_role(user, rbac.CLINICAL_ROLES):
    raise HTTPException(403)
```

```python
# sets disponibles
rbac.ADMIN_ROLES      # {SUPER_ADMIN, ADMIN}
rbac.CLINICAL_ROLES   # {SUPER_ADMIN, ADMIN, DOCTOR, SPECIALIST, ASSISTANT}
```

### Por qué existe `normalize_role()`

Había **cuatro vocabularios de roles** incompatibles:

| Dónde | Valor | Resultado |
|---|---|---|
| `init.sql` | `SUPER_ADMIN` | — |
| `assistants.py` | `("admin", "super_admin")` | **Nunca coincidía → 403 siempre** |
| Frontend | `'admin'`, `'super-admin'` | **Nunca reconocía admins** |
| `seed_large_dataset.py` | `"SUPER_ADMIN"` o `"ADMIN"` | A veces |

`normalize_role()` acepta cualquier variante:

```python
normalize_role("super-admin")   # -> "SUPER_ADMIN"
normalize_role("super_admin")   # -> "SUPER_ADMIN"
normalize_role("SuperAdmin")    # -> "SUPER_ADMIN"
normalize_role("medico")        # -> "DOCTOR"
normalize_role(None)            # -> ""  (nunca pasa ningún chequeo)
```

---

## Reglas para datos clínicos

1. Filtra por propietario (`user_id`) en lectura, escritura y borrado.
2. Ante un recurso de otro usuario, responde **`404`**, no `403`. Un `403`
   confirma que el recurso existe.
3. Los motivos de cancelación y suspensión son obligatorios.
4. `DELETE /appointments/{id}` es destructivo: borra la fila. Para anular una
   cita, usa el flujo de estados (`/cancel`), que deja historial. **La UI no
   expone el borrado**, a propósito.

---

## Corregido el 2026-09-30

| # | Vulnerabilidad | Corrección |
|---|---|---|
| 1 | **Escalada de privilegios**: `POST /api/v1/` era público y aceptaba `role_id` del body → cualquiera creaba un `super_admin` sin token | `Depends(require_admin)` |
| 2 | **IDOR en notas médicas**: `GET/PUT/DELETE /api/v1/notes/{id}` sin filtro de propietario → cualquier token leía y modificaba notas de cualquier paciente | `_assert_note_accessible()` |
| 3 | **DoS de datos**: `GET /api/v1/notes/` devolvía las 100 primeras notas globales a cualquier usuario | Filtrado por `appointments.user_id` |
| 4 | **Fuga de PII**: `GET /users/{id}/permissions` devolvía email, nombre y rol de cualquier usuario | Restringido a propio o admin |
| 5 | **RBAC roto**: `assistants.py` comparaba `("admin", "super_admin")` contra un rol `SUPER_ADMIN` | `require_admin` + `normalize_role()` |
| 6 | **Secreto versionado**: `.env` estaba en git con `SECRET_KEY` y contraseña de la BD | `git rm --cached .env`, `.env.develop` completo |
| 7 | **Ruta duplicada**: `GET /api/v1/roles` definida dos veces con respuestas distintas; la segunda ocultaba a la primera | Eliminada la de `users.py` |
| 8 | **Endpoints administrativos abiertos**: branches, roles, users, assistants sin filtro de rol | `require_admin` |

> ⚠️ **El secreto ya estaba en el historial de git.** `git rm --cached` lo saca
> del próximo commit, pero sigue en commits anteriores. Si el repositorio fue
> público, hay que **rotar `SECRET_KEY` y la contraseña de la BD**.

---

## Riesgos abiertos

Ordenados por severidad. Detalle en `docs/PENDIENTES.md`.

### P0 — antes de producción

**1. `/rag/chat` ejecuta SQL para cualquier usuario autenticado**

`core/agent.py` expone 40 herramientas con tool-calling; varias ejecutan SQL
arbitrario e incluso `CREATE TABLE`. El endpoint solo valida el JWT, sin
distinguir roles. Un usuario con rol `PATIENT` puede, vía lenguaje natural,
operar sobre datos de la clínica.

Mitigación pendiente: separar las herramientas de lectura de las de escritura,
restringir `/rag/chat` a `CLINICAL_ROLES` y auditar cada tool que escriba.

**2. Premium sin filtro de rol**

`POST /api/v1/prescriptions`, `POST /api/v1/billing/invoice` y el resto de
`premium.py` solo exigen JWT. Cualquier usuario autenticado puede emitir recetas
y facturas.

### P1

**3. Sin auditoría.** La tabla `audit_logs` y el modelo existen; **ningún
endpoint escribe en ella**. No hay trazabilidad de cambios de estado, que es un
requisito para datos clínicos, no una mejora.

**4. Sin rate limiting.** `/login/access-token` permite fuerza bruta. No hay
límite de peticiones en `/rag/chat`.

**5. CORS permisivo.** `allow_methods=["*"]`, `allow_headers=["*"]`,
`allow_credentials=True`. Restringir a los orígenes y métodos necesarios.

**6. `ACCESS_TOKEN_EXPIRE_SECONDS=90000`** (25 h). Para datos clínicos conviene
refresh token con expiración corta.

### P2

**7. Endpoints sin scoping de propietario**

| Ruta | Problema |
|---|---|
| `GET /api/v1/medasist/available-slots` | Acepta cualquier `doctor_id` |
| `POST /api/v1/medasist/reschedule` | No verifica propiedad de la cita |
| `POST /api/v1/medasist/check-conflict` | Acepta cualquier `doctor_id` |

`medical_histories`, `consulting_rooms` y `doctor_schedules` sí filtran por
`user_id`. `medasist.py` no.

**8. SQL dinámico en `integrations.py`.** El `UPDATE` de branches construye el
`SET` con un f-string. Las claves están limitadas por el schema Pydantic, así que
no es inyectable hoy, pero es frágil.

**9. Secretos en `.env.develop`.** Ahora solo hay valores de ejemplo, pero
conviene un check en CI que rechace valores que parezcan reales.

---

## Variables de entorno

Definidas en `backend/app/core/config.py` (lee `../.env`).

| Variable | Obligatoria | Default |
|---|---|---|
| `DATABASE_URL` | Sí | — |
| `FIRST_SUPERUSER_EMAIL` | Sí | — |
| `FIRST_SUPERUSER_PASSWORD` | Sí | — |
| `SECRET_KEY` | Sí | — |
| `ACCESS_TOKEN_EXPIRE_SECONDS` | No | `90000` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `1440` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` |
| `DEBUG` | No | `False` |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` |
| `OLLAMA_EMBEDDING_MODEL` | No | `nomic-embed-text` |
| `OLLAMA_LLM_MODEL` | No | `llama3.2` |
| `EMBEDDING_DIM` | No | `768` |
| `CORS_ORIGINS` | No | localhost 3000/5173/8080 |

`SECRET_KEY` de ejemplo para desarrollo:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`.env` está en `.gitignore` y `make verify-docs` falla si alguien lo versiona.

---

## Verificación

```bash
make verify-docs    # incluye chequeos de secretos y RBAC
```

El script `scripts/verify_docs.py` detecta:
- Comparaciones de rol a mano fuera de `rbac.py`
- Literales de rol en el frontend
- `.env` versionado en git
- Clases `medical-*` sin definir en el tema Tailwind