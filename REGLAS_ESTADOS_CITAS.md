# Máquina de Estados - Citas Médicas (MedAgenda)

## Estados Definidos

| Código | Nombre | Descripción |
|--------|--------|-------------|
| `PENDIENTE` | Pendiente | Cita creada, pendiente de confirmación |
| `CONFIRMADA` | Confirmada | Cita confirmada por paciente/secretaría |
| `REAGENDADA` | Reagendada | Cita movida a nueva fecha/hora |
| `ATENDIDA` | Atendida | Médico terminó la consulta |
| `SUSPENDIDA` | Suspendida | Cita pausada temporalmente |
| `CANCELADA` | Cancelada | Cita anulada antes de su fecha |

---

## Transiciones Permitidas

```
PENDIENTE ─────────────────────────────────────────────┐
    │                                                  │
    ├──► CONFIRMADA          (paciente/secretaría)    │
    ├──► REAGENDADA          (médico/secretaría)      │
    ├──► CANCELADA           (paciente/secretaría)    │
    └──► SUSPENDIDA          (médico/secretaría)      │
                                                         │
CONFIRMADA ────────────────────────────────────────────┤
    │                                                  │
    ├──► REAGENDADA          (médico/secretaría)      │
    ├──► ATENDIDA            (médico)                 │
    ├──► CANCELADA           (paciente/secretaría)    │
    ├──► SUSPENDIDA          (médico/secretaría)      │
    └──► PENDIENTE           (reversión admin)        │
                                                         │
REAGENDADA ────────────────────────────────────────────┤
    │                                                  │
    ├──► CONFIRMADA          (auto tras reagendar)    │
    ├──► ATENDIDA            (médico)                 │
    ├──► CANCELADA           (paciente/secretaría)    │
    ├──► SUSPENDIDA          (médico/secretaría)      │
    └──► PENDIENTE           (reversión admin)        │
                                                         │
ATENDIDA ──────────────────────────────────────────────┤
    │                                                  │
    └──► (estado terminal - NO hay transiciones)      │
                                                         │
SUSPENDIDA ───────────────────────────────────────────┤
    │                                                  │
    ├──► CONFIRMADA          (reactivación)           │
    ├──► REAGENDADA          (nueva fecha)            │
    ├──► CANCELADA           (paciente/secretaría)    │
    └──► PENDIENTE           (reversión admin)        │
                                                         │
CANCELADA ────────────────────────────────────────────┤
    │                                                  │
    ├──► PENDIENTE           (reversión si fecha > hoy)│
    └──► (estado terminal si fecha ≤ hoy)             │
                                                         │
```

---

## Reglas Detalladas por Transición

### 1. PENDIENTE → CONFIRMADA
- **Quién**: Paciente (portal), Secretaría, Médico
- **Cuándo**: Paciente confirma asistencia, secretaría valida
- **Validación**: Fecha/hora futura
- **Notificación**: Sí (confirmación al paciente)

### 2. PENDIENTE → REAGENDADA
- **Quién**: Médico, Secretaría
- **Cuándo**: Cambio de fecha/hora solicitado
- **Validación**: Nuevo slot disponible, sin conflictos
- **Notificación**: Sí (nueva fecha al paciente)
- **Auto**: Tras reagendar → **CONFIRMADA** automáticamente

### 3. PENDIENTE → CANCELADA
- **Quién**: Paciente, Secretaría
- **Cuándo**: Paciente no puede asistir
- **Validación**: Fecha > ahora (no se cancela cita pasada)
- **Notificación**: Sí (cancelación al paciente/médico)

### 4. PENDIENTE → SUSPENDIDA
- **Quién**: Médico, Secretaría
- **Cuándo**: Paciente no llega, se espera, o imprevisto
- **Validación**: Fecha/hora actual ≤ fecha cita
- **Notificación**: Opcional

### 5. CONFIRMADA → REAGENDADA
- **Quién**: Médico, Secretaría
- **Validación**: Nuevo slot disponible, sin conflictos
- **Auto**: Tras reagendar → **CONFIRMADA** automáticamente

### 5b. CONFIRMADA → ATENDIDA
- **Quién**: **Solo Médico** (botón "Marcar como atendida")
- **Cuándo**: Terminó la consulta
- **Validación**: Fecha/hora cita ≤ ahora + tolerancia (ej. 30 min)
- **Registro**: Timestamp de atención, notas médicas obligatorias
- **Notificación**: Sí (resumen al paciente)

### 6. CONFIRMADA → CANCELADA
- **Quién**: Paciente, Secretaría
- **Validación**: Fecha > ahora (si ya pasó → no se cancela, se atiende o suspende)
- **Notificación**: Sí

### 7. CONFIRMADA → SUSPENDIDA
- **Quién**: Médico, Secretaría
- **Cuándo**: Paciente no llega (no-show), imprevisto médico
- **Notificación**: Sí (al paciente para reprogramar)

### 8. REAGENDADA → CONFIRMADA (Auto)
- **Trigger**: Inmediato tras guardar nueva fecha/hora
- **Regla**: Toda cita reagendada queda **CONFIRMADA** por defecto

### 9. ATENDIDA → (Terminal)
- **No hay transiciones salientes**
- **Excepción**: Solo admin puede revertir con justificación + auditoría

### 10. SUSPENDIDA → CONFIRMADA / REAGENDADA / CANCELADA
- **Quién**: Médico, Secretaría
- **Validación**: Fecha nueva > ahora (si REAGENDADA)

### 11. CANCELADA → PENDIENTE (Reversión)
- **Quién**: Secretaría, Admin
- **Condición**: `cita.fecha_hora > now()` (fecha futura)
- **Validación**: Slot original disponible o nuevo slot
- **Notificación**: Sí (reactivación)

---

## Reglas de Negocio Especiales

### Auto-Cancelación No-Show (Batch Nocturno)
```
Cron: 02:00 diario
Para cada cita donde:
  - estado IN (CONFIRMADA, REAGENDADA, PENDIENTE)
  - fecha_hora < inicio_día_actual (ayer o antes)
  - NO tiene registro de atención
Acción: Cambiar a CANCELADA con reason "Auto-cancelada por no-show"
Notificar: Paciente + Médico
```

### Reversión de CANCELADA
```
Permitida SI: cita.start_datetime > now()
Denegada SI: cita.start_datetime <= now() (cita ya pasó)
```

### Conflicto al Reagendar
```
Si slot solicitado OCUPADO:
  - Si es REAGENDAR toda la agenda del día → priorizar por orden de llegada/hora original
  - Si es cita individual → rechazar con 409 Conflict, sugerir slots libres
```

### IA - Reagendar Masivo (Especialista)
```
Endpoint: POST /api/v1/appointments/ai-reschedule-bulk
Input: { doctor_id, date, criteria: "earliest_first" | "priority" }
Lógica:
  1. Obtener todas las citas PENDIENTE/CONFIRMADA del día
  2. Ordenar por criteria
  3. Para cada cita, buscar siguiente slot libre
  4. Aplicar en transacción (todo o nada)
  5. Notificar a todos los pacientes afectados
```

### Tolerancias de Tiempo
| Acción | Tolerancia |
|--------|------------|
| Marcar ATENDIDA | +30 min post fin cita |
| Cancelar cita | Hasta 1 hora antes |
| Reagendar | Hasta 2 horas antes |
| Confirmar | Hasta 15 min antes |

---

## Matriz de Permisos por Rol

| Transición | Paciente | Médico | Secretaría | Admin |
|------------|:--------:|:------:|:----------:|:-----:|
| PENDIENTE → CONFIRMADA | ✅ | ✅ | ✅ | ✅ |
| PENDIENTE → REAGENDADA | ❌ | ✅ | ✅ | ✅ |
| PENDIENTE → CANCELADA | ✅ | ❌ | ✅ | ✅ |
| PENDIENTE → SUSPENDIDA | ❌ | ✅ | ✅ | ✅ |
| CONFIRMADA → ATENDIDA | ❌ | ✅ | ❌ | ✅ |
| CONFIRMADA → REAGENDADA | ❌ | ✅ | ✅ | ✅ |
| CONFIRMADA → CANCELADA | ✅ | ❌ | ✅ | ✅ |
| CONFIRMADA → SUSPENDIDA | ❌ | ✅ | ✅ | ✅ |
| SUSPENDIDA → CONFIRMADA | ❌ | ✅ | ✅ | ✅ |
| SUSPENDIDA → REAGENDADA | ❌ | ✅ | ✅ | ✅ |
| CANCELADA → PENDIENTE | ❌ | ❌ | ✅ | ✅ |
| ATENDIDA → (reversión) | ❌ | ❌ | ❌ | ✅* |

*Solo con justificación y auditoría

---

## Eventos de Auditoría Requeridos

Toda transición registra:
```json
{
  "appointment_id": 123,
  "from_state": "CONFIRMADA",
  "to_state": "ATENDIDA",
  "changed_by": "user_id",
  "changed_by_role": "medico",
  "reason": "Consulta completada",
  "metadata": { "notes": "Paciente estable...", "duration_min": 25 },
  "timestamp": "2026-09-23T14:30:00Z"
}
```

---

## Validaciones de UI (Frontend)

| Estado Actual | Botones Visibles |
|---------------|------------------|
| PENDIENTE | [Confirmar] [Reagendar] [Cancelar] [Suspender] |
| CONFIRMADA | [Atender] [Reagendar] [Cancelar] [Suspender] |
| REAGENDADA | [Atender] [Reagendar] [Cancelar] [Suspender] |
| ATENDIDA | [Ver detalles] (solo lectura) |
| SUSPENDIDA | [Reactivar] [Reagendar] [Cancelar] |
| CANCELADA | [Reactivar] (si fecha > hoy) / [Ver detalles] |

---

## Endpoints API Sugeridos

```
PATCH /api/v1/appointments/{id}/confirm
PATCH /api/v1/appointments/{id}/reschedule    { new_start, new_end }
PATCH /api/v1/appointments/{id}/attend        { notes, duration }
PATCH /api/v1/appointments/{id}/suspend
PATCH /api/v1/appointments/{id}/cancel        { reason }
PATCH /api/v1/appointments/{id}/reactivate
POST  /api/v1/appointments/ai-reschedule-bulk { doctor_id, date, criteria }
GET   /api/v1/appointments/{id}/transitions   (historial de estados)
```

---

## Preguntas para Validar Contigo

1. **Auto-confirmación tras reagendar**: ¿Confirmado automáticamente o queda en REAGENDADA hasta que paciente confirme?
2. **Tolerancia ATENDIDA**: ¿30 min post-fin es correcto o más/menos?
3. **Cancelación por paciente**: ¿Hasta cuántas horas antes? (propongo 1h)
4. **SUSPENDIDA → CONFIRMADA**: ¿Requiere notificación al paciente?
5. **Batch nocturno**: ¿02:00 OK? ¿Zona horaria America/Mexico_City?
6. **Reversión ATENDIDA**: Solo admin con justificación, ¿requiere segunda firma?
7. **IA reagendar masivo**: ¿Criterio por defecto "earliest_first" o "priority"?
8. **Notificaciones**: ¿Todas por email + push? ¿SMS para urgentes?