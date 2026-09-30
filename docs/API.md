# API Reference

<!-- GENERADO AUTOMATICAMENTE por scripts/gen_api_docs.py. NO EDITAR A MANO. -->
<!-- Para cambiarlo: edita el codigo y ejecuta `python scripts/gen_api_docs.py` -->

**108 operaciones** en **75 rutas**. Base: `/api/v1`.

Verificado contra el codigo. Si algo no esta aqui, no existe.

## Autenticacion

Casi todo exige `Authorization: Bearer <token>`, obtenido via OAuth2 password flow:

```http
POST /api/v1/login/access-token
Content-Type: application/x-www-form-urlencoded

username=admin@medapi.com&password=...
```

| Situacion | Codigo |
|:--|:--|
| Sin token o token invalido | `401` |
| Token valido, rol insuficiente | `403` |
| Recurso inexistente o de otro usuario | `404` |

**Errores**: `{"detail": "..."}` o `{"detail": {"message": "..."}}`.

**Paginacion**: los listados usan `skip`/`limit`. Solo `GET /appointments/`
paginada de verdad: `{page, page_size, total, total_pages, items}`.

## Resumen

| Router | Ops |
|:--|--:|
| Appointments | 20 |
| Integrations | 9 |
| Premium Features | 7 |
| Assistants | 6 |
| RAG & AI Agent | 6 |
| Consulting Rooms | 5 |
| Doctor Schedules | 5 |
| Doctors | 5 |
| Medical Histories | 5 |
| Patients | 5 |
| Specialties | 5 |
| Visual Indicators | 5 |
| Appointment Statuses | 4 |
| Audit | 4 |
| Medasist IA | 4 |
| Reports & Dashboard | 4 |
| Notifications | 3 |
| Users | 3 |
| Login | 1 |

## Endpoints sin proteccion

Todos los demas requieren `Authorization: Bearer <token>`.

- `GET /`
- `GET /me`

## Detalle por router

> Appointment Statuses: Catalogo de la maquina de estados.

### Appointment Statuses

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/appointment-statuses/` | JWT |
| `POST` | `/api/v1/appointment-statuses/` | JWT |
| `DELETE` | `/api/v1/appointment-statuses/{status_id}` | JWT |
| `PATCH` | `/api/v1/appointment-statuses/{status_id}` | JWT |

> Appointments: Nucleo del negocio.

### Appointments

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/appointments/` | JWT |
| `POST` | `/api/v1/appointments/` | JWT |
| `POST` | `/api/v1/appointments/auto-cancel-no-show` | JWT |
| `POST` | `/api/v1/appointments/bulk-reschedule` | JWT |
| `DELETE` | `/api/v1/appointments/{appointment_id}` | JWT |
| `GET` | `/api/v1/appointments/{appointment_id}` | JWT |
| `PUT` | `/api/v1/appointments/{appointment_id}` | JWT |
| `POST` | `/api/v1/appointments/{appointment_id}/attend` | JWT |
| `POST` | `/api/v1/appointments/{appointment_id}/cancel` | JWT |
| `POST` | `/api/v1/appointments/{appointment_id}/confirm` | JWT |
| `POST` | `/api/v1/appointments/{appointment_id}/reactivate` | JWT |
| `POST` | `/api/v1/appointments/{appointment_id}/start` | JWT |
| `PATCH` | `/api/v1/appointments/{appointment_id}/status` | JWT |
| `POST` | `/api/v1/appointments/{appointment_id}/suspend` | JWT |
| `POST` | `/api/v1/appointments/{appointment_id}/wait` | JWT |
| `GET` | `/api/v1/notes/` | JWT |
| `POST` | `/api/v1/notes/` | JWT |
| `DELETE` | `/api/v1/notes/{note_id}` | JWT |
| `GET` | `/api/v1/notes/{note_id}` | JWT |
| `PUT` | `/api/v1/notes/{note_id}` | JWT |

> Assistants: Solo admin.

### Assistants

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/assistants/` | **admin** |
| `GET` | `/api/v1/assistants/specialists` | **admin** |
| `GET` | `/api/v1/assistants/{assistant_id}/specialists` | **admin** |
| `POST` | `/api/v1/assistants/{assistant_id}/specialists` | **admin** |
| `DELETE` | `/api/v1/assistants/{assistant_id}/specialists/{specialist_id}` | **admin** |
| `PATCH` | `/api/v1/assistants/{assistant_id}/toggle` | **admin** |

> Audit: Solo admin.

### Audit

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/audit/` | **admin** |
| `GET` | `/api/v1/audit/appointments/{appointment_id}` | **admin** |
| `GET` | `/api/v1/audit/notes/{note_id}` | **admin** |
| `GET` | `/api/v1/audit/summary` | **admin** |

### Consulting Rooms

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/consulting-rooms/` | JWT |
| `POST` | `/api/v1/consulting-rooms/` | JWT |
| `DELETE` | `/api/v1/consulting-rooms/{room_id}` | JWT |
| `GET` | `/api/v1/consulting-rooms/{room_id}` | JWT |
| `PUT` | `/api/v1/consulting-rooms/{room_id}` | JWT |

### Doctor Schedules

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/doctor-schedules/` | JWT |
| `POST` | `/api/v1/doctor-schedules/` | JWT |
| `DELETE` | `/api/v1/doctor-schedules/{schedule_id}` | JWT |
| `GET` | `/api/v1/doctor-schedules/{schedule_id}` | JWT |
| `PUT` | `/api/v1/doctor-schedules/{schedule_id}` | JWT |

### Doctors

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/doctors/` | JWT |
| `POST` | `/api/v1/doctors/` | JWT |
| `DELETE` | `/api/v1/doctors/{doctor_id}` | JWT |
| `GET` | `/api/v1/doctors/{doctor_id}` | JWT |
| `PUT` | `/api/v1/doctors/{doctor_id}` | JWT |

> Integrations: Calendario, sedes, roles.

### Integrations

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/branches` | JWT |
| `POST` | `/api/v1/branches` | JWT |
| `DELETE` | `/api/v1/branches/{branch_id}` | JWT |
| `PUT` | `/api/v1/branches/{branch_id}` | JWT |
| `GET` | `/api/v1/branches/{branch_id}/doctors` | JWT |
| `GET` | `/api/v1/calendar/ical/{doctor_id}` | JWT |
| `GET` | `/api/v1/calendar/sync/{doctor_id}` | JWT |
| `GET` | `/api/v1/roles` | JWT |
| `GET` | `/api/v1/users/{user_id}/permissions` | JWT |

> Login: Unico endpoint publico.

### Login

| Método | Ruta | Rol |
|:--|:--|:--|
| `POST` | `/api/v1/login/access-token` | JWT |

> Medasist IA: Agenda determinista, sin LLM.

### Medasist IA

| Método | Ruta | Rol |
|:--|:--|:--|
| `POST` | `/api/v1/medasist/available-slots` | JWT |
| `POST` | `/api/v1/medasist/check-conflict` | JWT |
| `POST` | `/api/v1/medasist/reschedule` | JWT |
| `POST` | `/api/v1/medasist/suggest-followup` | JWT |

### Medical Histories

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/medical-histories/` | JWT |
| `POST` | `/api/v1/medical-histories/` | JWT |
| `DELETE` | `/api/v1/medical-histories/{history_id}` | JWT |
| `GET` | `/api/v1/medical-histories/{history_id}` | JWT |
| `PUT` | `/api/v1/medical-histories/{history_id}` | JWT |

> Notifications: Scope por email del usuario.

### Notifications

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/notifications/` | JWT |
| `GET` | `/api/v1/notifications/unread-count` | JWT |
| `PATCH` | `/api/v1/notifications/{notification_id}` | JWT |

### Patients

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/patients/` | JWT |
| `POST` | `/api/v1/patients/` | JWT |
| `DELETE` | `/api/v1/patients/{patient_id}` | JWT |
| `GET` | `/api/v1/patients/{patient_id}` | JWT |
| `PUT` | `/api/v1/patients/{patient_id}` | JWT |

> Premium Features: Sin filtro de rol.

### Premium Features

| Método | Ruta | Rol |
|:--|:--|:--|
| `POST` | `/api/v1/billing/invoice` | JWT |
| `GET` | `/api/v1/billing/invoice/{invoice_number}` | JWT |
| `GET` | `/api/v1/billing/summary` | JWT |
| `POST` | `/api/v1/prescriptions` | JWT |
| `GET` | `/api/v1/prescriptions/{prescription_id}` | JWT |
| `POST` | `/api/v1/telemedicine/session` | JWT |
| `GET` | `/api/v1/telemedicine/session/{session_id}` | JWT |

> RAG & AI Agent: Ver `docs/IA_AGENTE.md`.

### RAG & AI Agent

| Método | Ruta | Rol |
|:--|:--|:--|
| `POST` | `/api/v1/rag/chat` | JWT |
| `POST` | `/api/v1/rag/chat/stream` | JWT |
| `GET` | `/api/v1/rag/health` | JWT |
| `POST` | `/api/v1/rag/ingest` | JWT |
| `POST` | `/api/v1/rag/ingest-note/{appointment_id}` | JWT |
| `POST` | `/api/v1/rag/search` | JWT |

> Reports & Dashboard: Sin filtro de rol.

### Reports & Dashboard

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/reports/appointments-by-day` | JWT |
| `GET` | `/api/v1/reports/appointments-by-doctor` | JWT |
| `GET` | `/api/v1/reports/dashboard/summary` | JWT |
| `GET` | `/api/v1/reports/no-show-rate` | JWT |

### Specialties

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/specialties/` | JWT |
| `POST` | `/api/v1/specialties/` | JWT |
| `DELETE` | `/api/v1/specialties/{specialty_id}` | JWT |
| `GET` | `/api/v1/specialties/{specialty_id}` | JWT |
| `PUT` | `/api/v1/specialties/{specialty_id}` | JWT |

> Users: Alta y listado **solo admin**.

### Users

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/` | **admin** |
| `POST` | `/api/v1/` | **admin** |
| `GET` | `/api/v1/me` | JWT |

> Visual Indicators: Config de indicadores.

### Visual Indicators

| Método | Ruta | Rol |
|:--|:--|:--|
| `GET` | `/api/v1/visual-indicators/config` | JWT |
| `POST` | `/api/v1/visual-indicators/config` | JWT |
| `DELETE` | `/api/v1/visual-indicators/config/{code}` | JWT |
| `GET` | `/api/v1/visual-indicators/config/{code}` | JWT |
| `PUT` | `/api/v1/visual-indicators/config/{code}` | JWT |

## Mantener al dia

Este archivo se genera desde el codigo:

```bash
python scripts/gen_api_docs.py          # regenerar
python scripts/gen_api_docs.py --check  # solo verificar (CI)
```

`make verify-docs` falla si el documento y el codigo difieren.
