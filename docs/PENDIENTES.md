# Deuda técnica

Trabajo conocido, priorizado. Actualizado 2026-09-30.

Severidad: **P0** bloquea producción · **P1** alto · **P2** medio · **P3** bajo.

---

## P0 — Bloqueante para producción

### 1. `/rag/chat` ejecuta SQL para cualquier usuario autenticado

**Dónde**: `backend/app/core/agent.py`, `api/endpoints/rag.py`

El agente expone 40 herramientas con tool-calling. Varias ejecutan SQL
arbitrario e incluso `CREATE TABLE`. El endpoint solo valida el JWT, sin
distinguir roles: un usuario con rol `PATIENT` puede operar sobre datos de la
clínica vía lenguaje natural.

**Por qué importa**: es la vía más amplia de escalación de privilegios del
proyecto.

**Trabajo**:
1. Separar las herramientas en lectura (`READ_TOOLS`) y escritura (`WRITE_TOOLS`).
2. Restringir `/rag/chat` y `/rag/chat/stream` a `rbac.CLINICAL_ROLES`.
3. Marcar cada herramienta de escritura con el rol mínimo que la puede usar, y
   validarlo en el dispatch en vez de confiar en el LLM.
4. Registrar toda invocación de herramienta de escritura en `audit_logs`.
5. Auditar el SQL de las 40 herramientas y parametrizar lo que quede interpolado.

**Ver**: `docs/IA_AGENTE.md`, `docs/SEGURIDAD.md`.

---

### 2. Premium sin filtro de rol

**Dónde**: `backend/app/api/endpoints/premium.py`

Siete endpoints que solo exigen JWT. Cualquier usuario autenticado, incluido un
`PATIENT`, puede:

- `POST /api/v1/prescriptions` — emitir recetas
- `POST /api/v1/billing/invoice` — generar facturas
- `POST /api/v1/telemedicine/session` — abrir sesiones de telemedicina

**Trabajo**: aplicar `require_roles(...)` según el caso. Recetas, al menos
`DOCTOR`/`SPECIALIST`. Facturación, `ADMIN`.

---

### 3. ~~Sin auditoría~~ — Parcialmente resuelto (2026-09-30)

**Resuelto**: toda transición de cita, el reagendamiento, la edición, el borrado,
la auto-cancelación por no-show y los intentos de login (éxito **y** fallo)
dejan registro con estado origen, destino, actor, motivo y timestamp, en la
misma transacción que el cambio. Endpoint de consulta restringido a
administradores. Ver `docs/AUDITORIA.md`.

**Pendiente**:

| Gap | Por qué importa |
|---|---|
| Notas médicas sin auditar | Crear, editar o borrar una nota clínica es más sensible que cambiar un estado |
| Alta de usuarios y cambios de rol sin auditar | Un privilege escalation no deja rastro |
| No se audita la **lectura** de datos clínicos | Se sabe quién modifica, no quién consulta |
| Sin política de retención | Nada impide borrar `audit_logs`; un rastro borrable no es un rastro |

---

## P1 — Alto

### 4. Sin rate limiting

`POST /login/access-token` admite fuerza bruta ilimitada. `/rag/chat` no tiene
límite de peticiones y cada una puede ejecutar varias herramientas.

**Trabajo**: añadir `slowapi` o un middleware equivalente. Límite estricto en
login (por IP y por email) y uno más alto en los endpoints de IA.

---

### 5. CORS permisivo

`main.py`:

```python
allow_origins=settings.CORS_ORIGINS,
allow_credentials=True,
allow_methods=["*"],
allow_headers=["*"],
```

Con `allow_credentials=True`, un origen malicioso autenticado puede hacer
peticiones con las credenciales de la sesión.

**Trabajo**: restringir `allow_methods` a `GET, POST, PUT, PATCH, DELETE` y
`allow_headers` a `Authorization, Content-Type`.

---

### 6. Expiración de token demasiado larga

`ACCESS_TOKEN_EXPIRE_SECONDS=90000` (25 horas) para datos clínicos.

**Trabajo**: acceso corto (15-30 min) con refresh token. El frontend ya tiene
`refresh_token` implementado en `api/api.ts`.

---

### 7. Endpoints `medasist` sin scoping de propietario

**Dónde**: `backend/app/api/endpoints/medasist.py`

| Ruta | Problema |
|---|---|
| `POST /medasist/reschedule` | No verifica propiedad de la cita |
| `POST /medasist/check-conflict` | Acepta cualquier `doctor_id` |
| `POST /medasist/available-slots` | Acepta cualquier `doctor_id` |

`medical_histories`, `consulting_rooms` y `doctor_schedules` sí filtran por
`user_id`. Aquí no.

**Trabajo**: aplicar el mismo criterio que en `appointments.py`, reutilizando el
helper de propiedad.

---

## P2 — Medio

### 8. Cero tests en el frontend

No hay framework de tests, ni archivos de prueba. `make test-front` solo corre
`tsc --noEmit`, que detecta errores de tipos, no de lógica.

**Trabajo**: introducir Vitest + Testing Library. Prioridad a `AppointmentActions`
(la lógica de permisos por estado es crítica y no está cubierta por ningún test).

---

### 9. Sin componentes `Button` / `Input` / `Card` compartidos

El botón primario está duplicado en 5 archivos, el input en ~30. Cualquier
cambio de estilo requiere editar decenas de sitios.

**Trabajo**: extraer a `components/ui/`, migrando por fases empezando por los
más usados.

---

### 10. `AppointmentsPage.tsx` con 793 líneas

Mezcla lista, formulario, modal de reagendamiento y filtros de IA en un archivo.

**Trabajo**: extraer `AppointmentForm`, `RescheduleModal` y `useAppointments`
(hook). Objetivo: por debajo de 250 líneas, el límite que fija `TRABAJO_ACUERDO.md`.

---

### 11. i18n configurado pero muerto

`i18n.ts` inicializa i18next con 13 claves; ningún componente llama a
`useTranslation()`. Todo el texto está hardcodeado en español.

Dos caminos: traducir de verdad (mover claves a archivos JSON y extraer los
textos), o borrar la dependencia. Dejarla a medias es lo peor.

---

### 12. Código muerto

| Archivo | Estado |
|---|---|
| `front/src/api/cache.ts` | Implementa caché con TTL, nadie lo importa |
| `front/src/components/common/Skeleton.tsx` | Nadie lo importa |
| `backend/app/users.py` | Router duplicado, nunca registrado |
| `backend/app/login.py` | Router duplicado, nunca registrado |
| `backend/app/modules/*/router.py` | Routers duplicados, nunca registrados |
| `backend/app/api/endpoints/premium.py` | 7 endpoints sin consumer en el front |

**Trabajo**: borrar lo muerto o conectar lo que debería usarse. Documentar la
decisión en `docs/DECISIONES.md`.

---

### 13. Remover `DELETE /appointments/{id}`

Es destructivo y sin historial. La UI correctamente no lo expone. Mantenerlo
expuesto en la API es un riesgo: cualquier `PATIENT` autenticado que se salte
la UI puede borrar citas ajenas.

**Trabajo**: restringirlo a `ADMIN` con razón obligatoria, o eliminarlo y dejar
solo el flujo de estados.

---

### 14. SQL dinámico en `integrations.py`

```python
assignments = ", ".join(f"{key} = :{key}" for key in values)
```

Las claves están limitadas por el schema Pydantic, así que no es inyectable hoy.
Pero el patrón es frágil: cualquier campo nuevo sin restringir abre la puerta.

**Trabajo**: construir el `SET` con una allowlist explícita.

---

### 15. Job de no-show sin programador

`POST /appointments/auto-cancel-no-show` existe y funciona, pero se invoca
manualmente. La especificación original pedía un cron a las 02:00.

**Trabajo**: decidir entre un worker externo (cron del sistema), APScheduler en
el backend, o dejarlo manual documentándolo.

---

## P3 — Bajo

### 16. 430 errores de `ruff` preexistentes

Principalmente imports sin usar y formato. No bloquear el trabajo por esto:
arreglarlos de forma masiva ensuciaría el historial. Plan: un commit dedicado
cuando el proyecto esté estable.

### 17. Bundle del frontend de 552 kB

168 kB gzip, por encima del umbral de Vite (500 kB).

**Trabajo**: `manualChunks` para separar `react` / `axios` / `lucide-react` de
el código de aplicación, y `React.lazy` para las 15 páginas.

### 18. Falta `.nvmrc` / `engines`

Node 20 está implícito en `Dockerfile.front`, pero no declarado en
`package.json`. Añadir `engines` y `.nvmrc`.

---

## Métricas

| Métrica | Valor |
|---|---|
| Endpoints | 104 en 71 rutas |
| Herramientas del agente | 40 |
| Estados de cita | 8 (un solo vocabulario) |
| Roles | 6 (un solo vocabulario) |
| Migraciones | 10, un solo head |
| Tests backend | 2 archivos (`test_api_contract.py`, `test_visual_indicator.py`) |
| Tests frontend | 0 |
| `.md` verificados | 10 |
| Chequeos de `make verify-docs` | 9 grupos, ~20 aserciones |