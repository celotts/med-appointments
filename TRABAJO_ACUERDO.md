# Plan de trabajo — Agenda Sana

> Documento de gobierno del proyecto. Las **reglas obligatorias** de la
> sección 2 no se negocian. El estado actual está en la sección 4.

---

## 1. Qué es este proyecto

Agenda de citas médicas con asistente de IA local. FastAPI + PostgreSQL/pgvector
en el backend, React + Vite en el frontend, Ollama para el LLM y los embeddings
(sin datos clínicos fuera de la máquina).

Definición de "terminado": los flujos de agendar → confirmar → atender → cerrar
funcionan de punta a punta, con datos de prueba, sin errores en consola.

---

## 2. Reglas obligatorias (nunca romper)

### 2.1 Vocabulario canónico

**Los estados de cita son exactamente estos 8.** No hay más.

```
PENDIENTE · CONFIRMADA · EN ESPERA · EN PROCESO · ATENDIDA · CANCELADA · SUSPENDIDA · REAGENDADA
```

- Fuente de verdad: `backend/app/schemas/appointment.py`.
- **Prohibido** `COMPLETADA` (nombre viejo), `SCHEDULED`, `CONFIRMED`,
  `COMPLETED`, `CANCELLED`, `NO_SHOW` o cualquier código en inglés.
- Toda transición pasa por `VALID_TRANSITIONS`. No se agregan transiciones.

### 2.2 Roles canónicos

```
SUPER_ADMIN · ADMIN · DOCTOR · SPECIALIST · ASSISTANT · PATIENT
```

- Fuente de verdad: `backend/app/core/rbac.py` (backend) y
  `front/src/auth/roles.ts` (frontend).
- **Prohibido** comparar `user.role.name == "..."` a mano. Usa `has_role()` /
  `require_roles()` / `require_admin` en el backend, `hasRole()` / `isAdmin()` en
  el front. Hubo cuatro vocabularios incompatibles y por eso los chequeos de
  rol nunca funcionaron.

### 2.3 Seguridad

- Toda ruta de escritura exige JWT. Las administrativas exigen rol admin.
- Los datos clínicos se filtran por propietario. Notas y citas de otro usuario
  devuelven `404`, no `403` (no revelamos existencia).
- Nada de secretos en el repositorio. `.env` está en `.gitignore`.
- Nada de `eval`, SQL interpolado ni `innerHTML` con datos del usuario.

### 2.4 Calidad

- **Ningún módulo nuevo supera 250 líneas.** Si lo hace, divídelo por
  responsabilidad. (Referencia histórica: el archivo original pedía 8 líneas por
  componente; las 15 páginas del frontend violaban esa regla, con
  `AppointmentsPage.tsx` en 793 líneas. El límite real del proyecto es 250.)
- Nada de imports sin usar: `tsc --noEmit` y `ruff` deben pasar limpios.
- Sin código muerto: nada de funciones exports que nadie llama.
- Comentarios en español, explicando **por qué**, no qué hace el código.

### 2.5 Flujo

- Regla de datos: primero `make test`, y si pasa, entregar.
- Todo `.md` debe ser cierto. `make verify-docs` falla si la documentación se
  desincroniza del código.
- No agregar features fuera del alcance de la tarea. Si sobra tiempo, se
  documenta en `docs/PENDIENTES.md`, no se implementa.

### 2.6 Documentación

- Ningún `.md` se escribe a mano si puede generarse: `docs/API.md` viene de
  `scripts/gen_api_docs.py`.
- Los documentos de referencia viven en `docs/`. Este archivo y `AGENTS.md` son
  los puntos de entrada.

---

## 3. Paleta de color (obligatoria)

| Uso | Hex | Token Tailwind |
|---|---|---|
| Consultas | `#2C5AA0` | `bg-medical-primary` |
| Operaciones | `#D22B2B` | `bg-medical-operation` |
| Visitas post-operatorio | `#F57C00` | `bg-medical-visit` |
| Personal / vacaciones | `#2E7D32` | `bg-medical-personal` |

Definidos en `front/tailwind.config.js`. **Usar los tokens, no hex sueltos.**
(Antes 130+ estilos usaban clases que el tema no definía y se perdían en
silencio; ya está corregido y `make verify-docs` lo vigila.)

---

## 4. Estado actual

**Última actualización: 2026-09-30**

### Completado

- Backend FastAPI con 104 endpoints en 18 routers.
- Máquina de estados de 8 estados unificada entre enum, semilla, migración,
  `agent.py`, seed de Docker y frontend.
- RBAC: 6 roles canónicos, `require_admin` aplicado a users, branches, roles,
  permissions y assistants.
- Corregidos: escalada de privilegios en alta de usuarios, IDOR en notas
  médicas, checker de roles que siempre daba 403, head duplicado de Alembic,
  tokens del frontend, clases Tailwind inexistentes.
- Frontend: 15 páginas, `tsc --noEmit` limpio, build correcto.
- Documentación: `AGENTS.md` + 9 documentos en `docs/`.
- `scripts/verify_docs.py` con 9 grupos de chequeos; `make verify-docs` en verde.

### Pendiente

Priorizado en `docs/PENDIENTES.md`. Lo bloqueante para producción:

1. `/rag/chat` ejecuta SQL para cualquier usuario autenticado.
2. Premium (recetas, facturas) sin filtro de rol.
3. Sin auditoría: `audit_logs` existe pero nadie escribe.

---

## 5. Siguiente paso

Leer `docs/PENDIENTES.md` y tomar el P0 más alto. Cada tarea sigue el flujo de
`docs/CHECKLIST_ENTREGA.md`.

---

## 6. Errores yaevitados

No repetir. Cada uno costó tiempo:

- ❌ Introducir un estado nuevo sin actualizar los 6 archivos acoplados
  (ver `docs/ESTADOS_CITA.md`).
- ❌ Comparar roles con literales en vez de `has_role()`.
- ❌ `alembic revision --autogenerate` sobre el baseline: detecta tablas no
  modeladas como eliminadas y las borra.
- ❌ Usar `COMPLETADA` en lugar de `ATENDIDA`.
- ❌ Crear clases `medical-*` que no existan en `tailwind.config.js`.
- ❌ Confiar en el `.env` versionado.
- ❌ Escribir un `.md` describing endpoints sin verificarlos.

---

## 7. Prompt de retoma

Para continuar en una sesión nueva, copiar este bloque y pegar:

```
SOY AGENTE — AGENDA SANA

Lee AGENTS.md primero: es el punto de entrada con las reglas obligatorias.

Despues:
1. Lee docs/PENDIENTES.md y elige el P0 mas alto sin tocar.
2. Lee el documento de docs/ que corresponda a esa area.
3. Sigue docs/CHECKLIST_ENTREGA.md al implementar.
4. Antes de decir "terminado": make test y make verify-docs en verde.

CONSTRAINTS (no negociables):
- Solo los 8 estados canonicos de cita
- Solo los 6 roles canonicos, siempre via has_role()/require_admin
- Maximo 250 lineas por modulo nuevo
- Nada de secretos en git
- Ningun .md afirma nada que no hayas verificado en el codigo

ULTIMA ACCION COMPLETADA: [describir]
SIGUIENTE PASO: [accion especifica]
```