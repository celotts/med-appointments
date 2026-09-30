# Decisiones (ADRs)

Decisiones ya tomadas y por qué. **No las re-litigues sin un motivo nuevo**; si
cambias una, reemplaza el ADR correspondiente y explica qué cambió.

Formato: contexto → decisión → consecuencia.

---

## ADR-001 · Base de datos: PostgreSQL + pgvector

**Estado**: aceptada

**Contexto**: El agente necesita búsqueda semántica sobre documentos clínicos,
con la opción de migrar a un vector store dedicado (Qdrant, Milvus, Pinecone).

**Decisión**: PostgreSQL 16 con la extensión `pgvector`. Índice HNSW con
`vector_cosine_ops`.

**Consecuencia**: una sola base de datos, una sola transacción, un solo backup.
Postgres vectorial escala bien hasta el orden de millones de vectores con HNSW;
más allá habría que medir. Añade una dependencia de infraestructura: la imagen
debe ser `pgvector/pgvector:pg16`, no `postgres`.

---

## ADR-002 · IA local con Ollama

**Estado**: aceptada

**Contexto**: Los documentos del agente incluyen notas médicas, diagnósticos y
tratamientos. Es información de salud: en muchas jurisdicciones enviarla a una
API de terceros es ilegal sin consentimiento.

**Decisión**: Todo el stack de IA corre en local. `llama3.2` como LLM,
`nomic-embed-text` (768 dims) como embedder. Sin proveedor cloud.

**Consecuencia**: privacidad garantizada por construcción. A cambio: hace falta
una máquina con recursos y Ollama debe estar disponible para que los tests del
agente corran. La calidad del razonamiento es inferior a un modelo frontier;
para las tareas de agenda es suficiente.

---

## ADR-003 · Sin servicios gestionados

**Estado**: aceptada

**Contexto**: El proyecto podría usar RDS, un cluster de Kubernetes o servicios
de/auth externos. Eso reduciría el trabajo operativo a costa de introducir
infraestructura y, en el caso de la IA, enviar datos clínicos fuera de la
máquina (contradice ADR-002).

**Decisión**: todo el stack se despliega con `docker compose`: PostgreSQL +
pgvector, la API FastAPI y el frontend detrás de nginx. Sin servicios
gestionados, sin cluster.

**Consecuencia**: el proyecto se levanta con `make up` en una máquina, sin
depender de proveedores. A cambio, backups, alta disponibilidad y escalado
quedan como responsabilidad del operador.

---

## ADR-004 · Nombres de ruta en inglés, dominio en español

**Estado**: aceptada

**Contexto**: El dominio se llama "citas" en español, pero el esquema de la base
de datos usa `appointments`, y el código original mezclaba ambos.

**Decisión**: Los identificadores técnicos (rutas, tablas, columnas, funciones,
clases) van en inglés. Los textos de interfaz, comentarios, docstrings y
mensajes de error van en español.

**Ejemplo**: `POST /api/v1/appointments/{id}/cancel` que responde
`{"detail": "Cita cancelada"}`.

**Consecuencia**: es lo estándar en la industria y no requiere traducción para
documentación externa. Mezclar los dos idiomas en el mismo identificador es lo
que se evita.

---

## ADR-005 · Un solo vocabulario de estados de cita

**Estado**: aceptada (2026-09-30)

**Contexto**: La máquina de estados tenía **tres** vocabularios incompatibles:

| Fuente | Estados |
|---|---|
| Enum de la app | PENDIENTE, CONFIRMADA, EN ESPERA, EN PROCESO, ATENDIDA, CANCELADA, SUSPENDIDA, REAGENDADA |
| Migración Alembic | usaba `COMPLETADA`; faltaban EN ESPERA, EN PROCESO, ATENDIDA |
| Seed de Docker | 10 códigos en inglés: SCHEDULED, CONFIRMED, COMPLETED, CANCELLED, NO_SHOW… |

Consecuencia: sobre una base limpia, `/wait`, `/start` y `/attend` fallaban con
*"Status EN ESPERA does not exist"*, y 10 queries del agente filtraban por
`COMPLETADA` sin devolver nunca filas.

**Decisión**: los 8 estados del enum son la única forma válida. El enum es la
fuente de verdad; la semilla SQL y las migraciones lo replican.

**Consecuencia**: `make verify-docs` falla si el enum, la semilla o el frontend
se desalinean, o si alguien usa `COMPLETADA`. Añadir un estado obliga a tocar
6 archivos acoplados, documentados en `docs/ESTADOS_CITA.md`.

---

## ADR-006 · Un solo vocabulario de roles, con normalización

**Estado**: aceptada (2026-09-30)

**Contexto**: Cuatro vocabularios de roles incompatibles. El más grave:
`assistants.py` comparaba `("admin", "super_admin")` en minúsculas contra el rol
real `SUPER_ADMIN`, así que **devolvía 403 siempre**, incluso al superusuario.
El frontend comparaba `'admin'` y `'super-admin'`, así que nunca reconocía a un
administrador.

**Decisión**: seis roles canónicos (`SUPER_ADMIN`, `ADMIN`, `DOCTOR`,
`SPECIALIST`, `ASSISTANT`, `PATIENT`) definidos en `core/rbac.py`, con
`normalize_role()` para aceptar cualquier variante. Toda comparación pasa por
`has_role()` / `require_roles()`; prohibido comparar a mano.

**Consecuencia**: el chequeo de roles por fin funciona. `make verify-docs` falla
si alguien vuelve a comparar literales, en backend o frontend.

---


## ADR-007 · 250 líneas por módulo, no 8

**Estado**: aceptada (2026-09-30)

**Contexto**: `TRABAJO_ACUERDO.md` exigía "máximo 8 líneas de código por
componente". Las 15 páginas del frontend violaban esa regla, y `AppointmentsPage.tsx`
tenía 793 líneas. Una regla que todo el código viola no es una regla: es ruido
que entrena a la IA a ignorar las restricciones.

**Decisión**: el límite es 250 líneas por módulo nuevo. Lo que importa no es el
número, sino la responsabilidad única: un archivo que hace dos cosas se divide.

**Consecuencia**: `AppointmentsPage.tsx` (793 líneas) es la deuda más visible;
está priorizada en `docs/PENDIENTES.md` #10.

---

## ADR-008 · Documentación generada cuando puede generarse

**Estado**: aceptada (2026-09-30)

**Contexto**: la documentaciónMentía sobre el código. Documentaba 9
herramientas del agente cuando había 40, y endpoints que nunca existieron
(`/appointments/ai-reschedule-bulk`). Una IA que la leyó construyó sobre arena.

**Decisión**: `docs/API.md` se genera desde el esquema OpenAPI con
`scripts/gen_api_docs.py`. `make verify-docs` compara la documentación con el
código en 9 grupos y falla ante cualquier desincronización.

**Consecuencia**: la referencia de API no puede quedar obsoleta. Las notas de
comportamiento que el generador no produce siguenbeingeditables a mano; el
checker solo exige que toda ruta del código aparezca en el documento.

---

## ADR-009 · 404 en vez de 403 para recursos ajenos

**Estado**: aceptada (2026-09-30)

**Contexto**: al corregir el IDOR de notas médicas, la opción natural era
`403 Forbidden`. Pero un `403` confirma que el recurso existe: un atacante puede
enumerar IDs válidos probando `GET /notes/1`, `GET /notes/2`… y quedarse con
todos los que dan `403`.

**Decisión**: si el recurso existe pero pertenece a otro usuario, responder
`404`. Indistinguible de "no existe".

**Consecuencia**: `_assert_note_accessible()` en `appointments.py` aplica el
criterio. Debe replicarse en `medasist.py` (ver `docs/PENDIENTES.md` #7).

---

## ADR-010 · Migración de merge en lugar de reescribir el historial

**Estado**: aceptada (2026-09-30)

**Contexto**: dos migraciones declaraban `down_revision = None`, dejando **dos
heads**. `alembic upgrade head` fallaba, y por eso `docker-entrypoint.sh` usaba
`upgrade heads` (con `s`) mientras el README decía `head`.

**Decisión**: agregar una migración de merge (`b1f4c7e92a00`) que una ambas
ramas. No reescribir migraciones ya aplicadas ni hacer `rebase` de historia
publicada.

**Consecuencia**: un solo head (`d4e1b2f7a915`); `alembic upgrade head` vuelve a
funcionar. `make verify-docs` falla si reaparece un segundo head.

---

## ADR-011 · Frontend sin librería de estado global

**Estado**: aceptada

**Contexto**: React Query o Zustand aportarían caché, reintentos y
desinvalidación. El proyecto tiene 15 páginas con `useState` + `useEffect`.

**Decisión**: mantener Context + hooks. `react-hook-form` para formularios,
`react-hot-toast` para avisos.

**Consecuencia**: sin caché compartida; cada página carga sus datos al montar.
Adecuado al volumen actual. Si aparece el problema (refetch manual, estados de
carga inconsistentes), la introducción de TanStack Query sería el camino
natural, pero es un cambio de arquitectura, no una mejora incremental.

---

## ADR-012 · Borrar en vez de eliminar citas

**Estado**: aceptada (2026-09-30)

**Contexto**: `DELETE /api/v1/appointments/{id}` borra la fila sin dejar
rastro. Para una agenda médica, una cita anulada es información de negocio y a
veces clínica.

**Decisión**: la vía canónica para anular una cita es el flujo de estados
(`/cancel` con `reason` obligatorio). La UI no expone el borrado. El `DELETE`
sigue en la API por compatibilidad.

**Consecuencia**: pendiente restringirlo a `ADMIN` (`docs/PENDIENTES.md` #13).

---

## ADR-013 · `verify_docs.py` como puerta de calidad

**Estado**: aceptada (2026-09-30)

**Contexto**: los errores que aparecieron (vocabularios divergentes, `COMPLETADA`
en el agente, RBAC roto, `.env` versionado) eran todos detectables con un
análisis estático. No hacía falta un humano para verlos.

**Decisión**: un script que compara documentación, código, esquema, seeds,
migraciones y secretos. Corre en `make verify-docs`, sin Docker ni base de datos.

**Consecuencia**: la documentación no puede volver a mentir en silencio. El
script corre en <2 s porque solo analiza archivos y el esquema OpenAPI, que se
construye sin conexión.

## ADR-014 · No reescribir migraciones ya aplicadas

**Estado**: aceptada (2026-09-30)

**Contexto**: `ff5e6bd85bff` sembraba `COMPLETADA`, y las ramas divergentes
produjeron dos heads. La corrección ingenua consiste en reescribir esos archivos.

**Decisión**: **no tocar migraciones ya aplicadas**. Se agregan migraciones
nuevas que corrigen los datos (`c9d2a1e6f304` normaliza estados, `d4e1b2f7a915`
inserta roles) y una de merge (`b1f4c7e92a00`) que une las ramas.

**Consecuencia**: el historial refleja lo que realmente pasó, y una base ya
sembrada se corrige al hacer upgrade. Reescribir migraciones aplicadas genera
drift silencioso entre desarrollo y producción: el archivo dice una cosa y la
base otra.

---
