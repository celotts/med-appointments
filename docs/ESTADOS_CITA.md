# Máquina de estados de citas

Fuente de verdad del ciclo de vida de una cita. Este archivo reemplaza a
`REGLAS_ESTADOS_CITAS.md` (raíz), que estaba desactualizado y mezclaba el
vocabulario antiguo.

> ⚠️ **Este proyecto tuvo tres vocabularios de estados en conflicto.**
> Se resolvió el 2026-09-30. El vocabulario canónico es el de abajo y ya no
> debe cambiar sin actualizar, en el mismo commit, los seis archivos listados
> en [Invariantes](#invariantes-a-verificar).

---

## Los 8 estados canónicos

| Código | Nombre | Significado |
|---|---|---|
| `PENDIENTE` | Pendiente | Creada, sin confirmar |
| `CONFIRMADA` | Confirmada | El paciente confirmó asistencia |
| `EN ESPERA` | En espera | El paciente llegó y espera su turno |
| `EN PROCESO` | En proceso | El médico está atendiendo |
| `ATENDIDA` | Atendida | Consulta finalizada · **terminal** |
| `CANCELADA` | Cancelada | Anulada · **terminal** |
| `SUSPENDIDA` | Suspendida | Pausada, se puede reactivar |
| `REAGENDADA` | Reagendada | Movida a nueva fecha |

Definidos en:
- Enum `AppointmentStatusCode` — `backend/app/schemas/appointment.py`
- Grafo `VALID_TRANSITIONS` — mismo archivo
- Semilla SQL — `script_BD/seeds/seed_catalogs.sql`
- Migraciones — `c9d2a1e6f304` (estados) y `d4e1b2f7a915` (roles)

---

## Transiciones permitidas

```text
PENDIENTE ──► CONFIRMADA · CANCELADA · SUSPENDIDA · REAGENDADA

CONFIRMADA ──► EN ESPERA · CANCELADA · SUSPENDIDA · REAGENDADA

EN ESPERA ──► EN PROCESO · CANCELADA · SUSPENDIDA

EN PROCESO ──► ATENDIDA · CANCELADA · SUSPENDIDA

REAGENDADA ──► CONFIRMADA · EN ESPERA · CANCELADA · SUSPENDIDA

SUSPENDIDA ──► CONFIRMADA · EN ESPERA · CANCELADA

ATENDIDA ──► (terminal, sin salida)
CANCELADA ──► (terminal, sin salida)
```

### Endpoint asociado a cada transición

| Transición | Endpoint | Nota |
|---|---|---|
| → `CONFIRMADA` | `POST /appointments/{id}/confirm` | Desde `PENDIENTE` |
| → `EN ESPERA` | `POST /appointments/{id}/wait` | El paciente llegó |
| → `EN PROCESO` | `POST /appointments/{id}/start` | Empieza la consulta |
| → `ATENDIDA` | `POST /appointments/{id}/attend` | Crea la nota médica |
| → `SUSPENDIDA` | `POST /appointments/{id}/suspend` | **`reason` obligatorio** |
| → `CANCELADA` | `POST /appointments/{id}/cancel` | **`reason` obligatorio** |
| → `REAGENDADA` | `PUT /appointments/{id}` | Cambia `start_datetime` |
| → `PENDIENTE` | `POST /appointments/{id}/reactivate` | Solo desde `CANCELADA` |
| genérica | `PATCH /appointments/{id}/status` | Valida contra `VALID_TRANSITIONS` |

---

## Estados que ocupan agenda

Definido en `STATUSES_THAT_OCCUPY` (`core/crud_visual_indicator.py`):

```python
STATUSES_THAT_OCCUPY = {"PENDIENTE", "CONFIRMADA", "REAGENDADA"}
```

Bloquean el horario: al agendar sobre una cita con uno de estos estados, se
detecta el conflicto. `EN ESPERA` y `EN PROCESO` **no** bloquean (ya están
dentro del turno).

Estados terminales (`TERMINAL_STATUSES`): `ATENDIDA`, `CANCELADA`. Desde ellos no
se reagenda ni se cancela.

---

## Permisos por rol

Comparar siempre con `has_role()` de `core/rbac.py`. **Nunca** con
`user.role.name == "..."` a mano: hubo cuatro vocabularios distintos y por eso
el chequeo nunca funcionaba.

| Transición | ADMIN | DOCTOR | ASSISTANT | PATIENT |
|---|:---:|:---:|:---:|:---:|
| → `CONFIRMADA` | ✅ | ✅ | ✅ | ✅ (propia) |
| → `EN ESPERA` | ✅ | ✅ | ✅ | ❌ |
| → `EN PROCESO` | ✅ | ✅ | ✅ | ❌ |
| → `ATENDIDA` | ✅ | ✅ | ❌ | ❌ |
| → `SUSPENDIDA` | ✅ | ✅ | ✅ | ❌ |
| → `CANCELADA` | ✅ | ✅ | ✅ | ✅ (propia) |
| → `REAGENDADA` | ✅ | ✅ | ✅ | ❌ |
| → `PENDIENTE` (reactivar) | ✅ | ✅ | ✅ | ❌ |

---

## Invariantes a verificar

Toda transición debe cumplir:

1. El estado destino está en `VALID_TRANSITIONS[estado_actual]`.
2. El estado destino existe en la tabla `appointment_statuses`.
3. El usuario tiene el rol que la matriz anterior exige.
4. Si el usuario no es `ADMIN`/`DOCTOR`/`ASSISTANT`, la cita le pertenece
   (`appointments.user_id == current_user.id`).
5. Los estados terminales no tienen salida.

> **El invariante 2 es el que se rompió.** La migración `ff5e6bd85bff` sembraba
> `COMPLETADA` en vez de `ATENDIDA`, y ni siquiera existían `EN ESPERA` ni
> `EN PROCESO`. Los endpoints `/wait`, `/start` y `/attend` fallaban con
> *"Status EN ESPERA does not exist"*. La migración `c9d2a1e6f304` lo corrige.

---

## Al cambiar un estado

Estos seis archivos están acoplados. Un cambio debe tocar todos:

| # | Archivo | Qué contiene |
|---|---|---|
| 1 | `backend/app/schemas/appointment.py` | `AppointmentStatusCode`, `VALID_TRANSITIONS` |
| 2 | `script_BD/seeds/seed_catalogs.sql` | Semilla SQL idempotente |
| 3 | `backend/alembic/versions/c9d2a1e6f304_*.py` | Mapa de remapeo |
| 4 | `backend/app/core/crud_visual_indicator.py` | `STATUSES_THAT_OCCUPY`, `TERMINAL_STATUSES` |
| 5 | `front/src/components/common/AppointmentActions.tsx` | Qué botones se muestran |
| 6 | `front/src/pages/AppointmentStatusPage.tsx` | Etiquetas en la UI |

```bash
make verify-docs    # falla si la documentación quedó desfasada
make test           # incluye test_catalogo_estados_de_cita
```

---

## Nombres que ya NO deben usarse

| Nombre viejo | Usar en su lugar | Dónde sobrevivió |
|---|---|---|
| `COMPLETADA` | `ATENDIDA` | Doc antigua, `agent.py` (corregido) |
| `SCHEDULED`, `CONFIRMED`, `COMPLETED`, `CANCELLED`, `NO_SHOW`, `WAITING`, `IN_PROGRESS` | Equivalente en español | `seed_large_dataset.py` (corregido) |
| `/appointments/ai-reschedule-bulk` | `POST /appointments/bulk-reschedule` | `REGLAS_ESTADOS_CITAS.md` (eliminado) |

---

## Reglas de negocio

### Tolerancias

| Acción | Tolerancia |
|---|---|
| Marcar `ATENDIDA` | +30 min tras el fin previsto |
| `DEFAULT_DELAY_TOLERANCE_MINUTES` | 15 min (indicador visual de demora) |
| Reagendar | hasta 2 h antes |
| Cancelar | hasta 1 h antes |

### Cancelación automática por no-show

`POST /appointments/auto-cancel-no-show` implementa el batch nocturno descrito en
la especificación original. Hoy se invoca **manualmente**: no hay cron ni
scheduler en el proyecto. Ver `docs/PENDIENTES.md`.

### Reagendamiento masivo

`POST /appointments/bulk-reschedule` con `{doctor_id, date, criteria}` donde
`criteria` es `"earliest_first"` o `"priority"`. Aplica todo-o-nada dentro de una
transacción.

---

## Registro de auditoría

El modelo `AuditLog` (`backend/app/models/audit.py`) y la tabla `audit_logs`
existen, pero **ningún endpoint de transición escribe en ella**. Es una deuda
conocida: ver `docs/PENDIENTES.md`. Para datos clínicos con requisitos de
trazabilidad es un requisito, no una mejora.