# Auditoría

Registro de quién hizo qué y cuándo. Para datos clínicos no es una mejora: es
un requisito de trazabilidad.

Implementado el 2026-09-30. Antes, la tabla `audit_logs` existía desde el
esquema inicial pero **nada escribía en ella**.

---

## Qué se registra

| Evento | Dónde |
|---|---|
| Creación de cita | `create_appointment` |
| `PENDIENTE → CONFIRMADA` | `confirm_appointment` |
| `CONFIRMADA → EN ESPERA` | `wait_appointment` |
| `EN ESPERA → EN PROCESO` | `start_appointment` |
| `EN PROCESO → ATENDIDA` | `attend_appointment` |
| `→ SUSPENDIDA` | `suspend_appointment` |
| `→ CANCELADA` | `cancel_appointment` |
| `CANCELADA → PENDIENTE` | `reactivate_appointment` |
| Reagendamiento | `reschedule_appointment` |
| Edición de datos | `update_appointment` |
| Cambio genérico de estado | `change_status` (`PATCH /status`) |
| Borrado de cita | `delete_appointment` |
| Auto-cancelación por no-show | `auto_cancel_no_show_appointments` |
| Creación de nota clínica | `crud_medical_note.create_note` |
| Edición de nota clínica | `crud_medical_note.update_note` |
| Borrado de nota clínica | `crud_medical_note.delete_note` |
| Inicio de sesión (éxito y fallo) | `api/endpoints/login.py` |

Cada registro de cita incluye **estado origen, estado destino, actor, motivo y
timestamp**. Los de notas clínicas guardan además el contenido antes y después.

---

## Formato

Columnas en `audit_logs` (`script_BD/init.sql`). El contenido va como JSON en
`old_value` / `new_value`.

### Transición de estado

```json
{
  "from_state": "CONFIRMADA",
  "to_state": "ATENDIDA",
  "reason": "Consulta completada",
  "metadata": { "duration_min": 25, "atencion_tardia_min": 12 }
}
```

- `from_state: null` → la cita se acaba de crear.
- `metadata.automatica: true` → el cambio lo hizo un job, no una persona.

### Borrado

```json
{
  "status": "PENDIENTE",
  "start_datetime": "2026-10-06T09:00:00+00:00",
  "doctor_id": 43,
  "patient_id": 45
}
```

Se escribe **antes** del `DELETE` y se confirma en la misma transacción, para
que el rastro sobreviva al registro que describe.

### Intento de login

```json
{ "email": "admin@medapp.com", "resultado": "ok" }
{ "email": "no-existe@medapp.com", "resultado": "fallido" }
```

Los intentos fallidos también se registran: son los que delatan fuerza bruta.
Nunca se guarda la contraseña; hay un test que lo verifica.

### Notas clínicas

Las notas se auditan con el **contenido completo**, no solo con los campos
tocados. Un rastro que dice "cambió la nota" no permite reconstruir qué se
corrigió.

**Creación:**

```json
{
  "appointment_id": 26,
  "diagnosis": "Hipertension leve",
  "treatment": "Losartan 50mg",
  "observations": "Controlar tension semanal",
  "evento": "nota_creada",
  "motivo": "Nota clinica creada"
}
```

**Edición** — guarda el valor previo y el nuevo:

```json
{
  "antes":  { "diagnosis": "Hipertension leve", "treatment": "Losartan 50mg" },
  "despues": { "diagnosis": "Hipertension moderada", "treatment": "Losartan 100mg" },
  "campos_modificados": ["diagnosis", "treatment"],
  "evento": "nota_actualizada",
  "motivo": "Nota clinica modificada"
}
```

**Borrado** — conserva el contenido que se eliminó:

```json
{
  "diagnosis": "Diagnostico que debe sobrevivir al borrado",
  "treatment": "Tratamiento confidencial",
  "observations": "Observacion sensible",
  "evento": "nota_borrada",
  "motivo": "Nota clinica eliminada"
}
```

> **Por qué el contenido completo y no un hash.** Una primera versión guardaba
> solo `campos_modificados`. Es insuficiente: si una nota se corrige y alguien
> pregunta seis meses después qué decía, el hash no responde nada. El coste es
> duplicar datos clínicos en `audit_logs`, aceptable porque la tabla vive en la
> misma base y hereda su cifrado y control de acceso. Si el almacenamiento
> dejara de estar bajo control, habría que pasar a digest + depósito externo.

### `motivo`

La tabla `audit_logs` no tiene columna para el motivo. `registrar(reason=...)`
lo guarda dentro de `new_value` bajo la clave `"motivo"`.

---

## La misma transacción

El registro y el cambio de estado se confirman juntos. Si se confirmaran por
separado, un fallo intermedio dejaría un estado cambiado sin rastro, que es
justo lo que la auditoría debe impedir.

```python
# crud_appointment_audit.py
db_appointment.status_id = status_destino.id
await crud_audit.registrar_transicion_cita(...)   # mismo commit
await db.commit()
```

---

## `record_id`: UUID derivado

`audit_logs.record_id` es `UUID`, pero las tablas de negocio usan `SERIAL`
(`appointments.id` es `INTEGER`). Se deriva un UUID v5 determinista:

```python
normalizar_record_id(1) == normalizar_record_id(1)   # estable
normalizar_record_id(1) != normalizar_record_id(2)   # sin colisiones
```

Un registro conserva su `record_id` aunque la cita ya no exista.

---

## Trampa de SQLAlchemy async: `MissingGreenlet`

**Toda lectura de atributo ORM va antes del flush de la auditoría.** Después de
un flush la sesión expira los objetos, y volver a consultar
`db_appointment.status` o `actor.id` lanza:

```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called;
can't call await_only() here
```

Por eso cada función captura primero en variables locales:

```python
# Correcto
status_origen = db_appointment.status.code
actor_id = getattr(actor, "id", None)
appointment_id = db_appointment.id
# ... luego auditar, luego commit

# Incorrecto: leer despues del flush
await crud_audit.registrar(...)
estado = db_appointment.status.code   # MissingGreenlet
```

Si añades una transición nueva, copia el patrón.

---

## La auditoría nunca rompe la operación

Si la escritura del registro falla, se registra un warning y la transición
continúa. Perderse una transición de estado es peor que perderse su rastro, y un
`raise` desde aquí dejaría al usuario sin poder trabajar.

```python
except Exception:
    logger.warning("No se pudo escribir el registro de auditoria ...")
    return None
```

---

## Consultar

Solo administradores (`require_admin`): el registro contiene motivos clínicos
y datos de personal.

| Método | Ruta | Para qué |
|---|---|---|
| `GET` | `/api/v1/audit/` | Listado, con filtros `table_name`, `record_id`, `user_id` |
| `GET` | `/api/v1/audit/appointments/{id}` | Historial completo de una cita |
| `GET` | `/api/v1/audit/notes/{id}` | Historial de una nota clínica, con contenido antes/después |
| `GET` | `/api/v1/audit/summary` | Totales por acción y tabla |

```bash
# Rastro de una cita
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5435/api/v1/audit/appointments/42

# Historial de una nota clínica: qué decía antes de cada corrección
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:5435/api/v1/audit/notes/7

# Todos los cambios de estado
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:5435/api/v1/audit/?table_name=appointments&limit=50"
```

---

## Verificación

```bash
cd backend && venv/bin/python -m pytest -q tests/test_audit.py
make verify-docs   # grupo 10: comprueba que toda transicion audita
```

El grupo 10 de `verify_docs.py` falla si:

- falta `core/crud_audit.py`
- `init.sql` ya no crea `audit_logs`
- alguna función de transición no escribe registro
- `api/endpoints/audit.py` no exige `require_admin`

---

## Lo que falta

- [ ] Auditar **alta y modificación de usuarios** y la asignación de roles. Hoy
      una escalada de privilegios no deja rastro.
- [ ] Auditoría **en lectura de datos clínicos**: se registra quién *modifica*,
      no quién *consulta*. Algunas jurisdicciones exigen también lo segundo, pero
      el volumen es mucho mayor y tiene implicaciones de privacidad propias:
      es una decisión de política, no solo de código.
- [ ] **Política de retención**: nada impide borrar `audit_logs`. Un rastro que
      se puede eliminar no es un rastro. Necesita tabla de retenciones,
      particionado y control de borrado.
- [ ] **Notas de `medical_histories`**: la tabla existe con su API y, a diferencia
      de `medical_notes`, no está auditada.