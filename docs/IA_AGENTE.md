# Módulo de IA — Agente MedAssist

Documentación del subsistema de IA: **RAG** (recuperación aumentada) y un agente
conversacional con *tool calling*. Este archivo reemplaza a `IA.md` y
`docs/AI_EXAMPLES.md`, que estaban desactualizados (documentaban 9 herramientas
cuando hay 40, y un endpoint SSE inexistente).

> **Regla de este documento:** todo lo que aparece aquí está verificado contra el
> código. Si algo no está listado, no existe. Verifica con
> `make verify-docs`.

---

## Arquitectura

```text
                    Frontend (React + Vite)
                            │  HTTP + JWT
                            ▼
        ┌──────────────────────────────────────────┐
        │  FastAPI  ·  /api/v1/rag/*  ·  rag.py    │
        └───────────┬──────────────────┬───────────┘
                    │                  │
        ┌───────────▼────────┐  ┌──────▼──────────────────┐
        │  Agente MedAssist │  │  Módulo RAG             │
        │  core/agent.py    │◄─┤  core/rag.py            │
        │  ReAct · 40 tools │  │  ingesta + búsqueda     │
        └───────────┬────────┘  └──────┬──────────────────┘
                    │                   │
        ┌───────────▼────────┐  ┌──────▼──────────────────┐
        │  Ollama (local)   │  │  PostgreSQL + pgvector  │
        │  llama3.2         │  │  tabla `vector_documents`│
        │  nomic-embed-text │  │  índice HNSW coseno      │
        └────────────────────┘  └─────────────────────────┘
```

**Privacidad:** el LLM y los embeddings corren en Ollama local. Ningún dato
clínico sale de la máquina.

---

## Dos sistemas distintos, no los confundas

| | RAG | Medasist |
|---|---|---|
| Ruta | `/api/v1/rag/*` | `/api/v1/medasist/*` |
| Archivo | `core/rag.py` + `core/agent.py` | `api/endpoints/medasist.py` |
| Naturaleza | Búsqueda semántica + agente LLM | Lógica de agenda **determinista** (sin LLM) |
| Usa Ollama | Sí | No |

`/api/v1/medasist/*` **no** es el agente: es lógica de agenda en Python puro.
Úsalo para sugerencias de horario; usa `/rag/chat` para conversación.

---

## Configuración

```env
OLLAMA_BASE_URL=http://localhost:11434   # en Docker: http://host.containers.internal:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text  # 768 dimensiones
OLLAMA_LLM_MODEL=llama3.2
EMBEDDING_DIM=768
```

Modelos requeridos:

```bash
ollama pull nomic-embed-text
ollama pull llama3.2
```

---

## Base de datos vectorial

Tabla real: **`vector_documents`** (no `documentos_vectoriales` — el nombre que
decía la documentación anterior nunca existió). Definida en
`script_BD/init.sql`.

```sql
CREATE TABLE vector_documents (
    id SERIAL PRIMARY KEY,
    reference_type VARCHAR(50) NOT NULL,   -- 'MEDICAL_NOTE', 'DOCUMENTO', ...
    reference_id INT,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vector_documents_embedding
ON vector_documents USING hnsw (embedding vector_cosine_ops);
```

---

## Las 40 herramientas del agente

Definidas en `backend/app/core/agent.py`, cada una decorada con `@tool`.

### Lectura — datos del paciente

| # | Herramienta | Qué hace |
|---|---|---|
| 1 | `buscar_en_documentos` | Búsqueda semántica sobre `vector_documents`; filtro opcional por `reference_type` |
| 2 | `consultar_citas_paciente` | Citas de un paciente por nombre (`ILIKE`) |
| 3 | `consultar_citas_medico` | Calendario de un médico |
| 4 | `buscar_pacientes` | Búsqueda parcial en el catálogo de pacientes |
| 5 | `buscar_medicos` | Búsqueda parcial de médicos y especialidad |
| 6 | `contar_registros` | Totales globales de pacientes, médicos, citas y notas |

### Agenda y disponibilidad

| # | Herramienta | Qué hace |
|---|---|---|
| 7 | `sugerir_horarios_disponibles` | Slots libres de un médico en una fecha |
| 8 | `detectar_conflictos` | Citas superpuestas en un rango de fechas |
| 9 | `analizar_carga_medico` | Ocupación y ocupación libre por día |
| 10 | `encontrar_horario_compartido` | Ventanas donde dos médicos coinciden |
| 11 | `detectar_anomalias` | Patrones anómalos en la agenda |
| 12 | `predecir_demanda` | Estimación de demanda futura |
| 13 | `optimizar_agenda` | Sugerencias de optimización de agenda |
| 14 | `scheduling_adaptativo` | Ajuste de agenda según carga |
| 15 | `resolver_conflicto_cirugia` | Resolution de conflictos quirúrgicos |

### Mutación — requieren confirmación

| # | Herramienta | Efecto |
|---|---|---|
| 16 | `sugerir_reagendamiento` | **Solo propone**. No escribe en la BD |
| 17 | `ejecutar_reagendamiento` | Cambia la fecha → estado `REAGENDADA`. Exige `confirmado=True` |
| 18 | `cancelar_cita` | Transiciona a `CANCELADA`. Exige `confirmado=True` |
| 19 | `crear_cita_por_lenguaje` | Crea una cita desde descripción natural |
| 20 | `reagendamiento_inteligente` | Reagenda sugiriendo el mejor horario |
| 21 | `cancelar_citas_masivo` | Cancelación masiva |
| 22 | `replanificar_citas` | Replanificación de un conjunto de citas |
| 23 | `duracion_inteligente` | Estima la duración según motivo y médico |
| 24 | `optimizar_ingresos` | Optimiza el horario de ingresos |

### Clínicas y análisis

| # | Herramienta | Qué hace |
|---|---|---|
| 25 | `analizar_patrones_paciente` | Preferencias y tasa de cancelaciones |
| 26 | `predecir_no_show` | Probabilidad de inasistencia |
| 27 | `sugerir_seguimiento` | Recomendación de seguimiento clínico |
| 28 | `resumen_clinico_paciente` | Resumen del historial del paciente |
| 29 | `matching_paciente_medico` | Sugiere el médico más adecuado |
| 30 | `score_satisfaccion` | Puntaje de satisfacción del paciente |
| 31 | `triagar_por_sintomas` | Evalúa urgencia por síntomas |
| 32 | `teletriaje_ia` | Triaje remoto por IA |
| 33 | `ai_scribe` | Transcripción/resumen de consulta |
| 34 | `analisis_sentimiento` | Análisis de sentimiento en notas |

### Operación y comunicación

| # | Herramienta | Qué hace |
|---|---|---|
| 35 | `agregar_a_lista_espera` | Añade paciente a `waitlist` |
| 36 | `notificar_lista_espera` | Avisa a la lista de espera de unslot libre |
| 37 | `generar_recordatorio` | Genera el texto de un recordatorio |
| 38 | `protocolo_emergencia` | Aplica el protocolo de emergencia |
| 39 | `coordinacion_familiar` | Coordina citas de una familia |
| 40 | `verificacion_seguros` | Verifica cobertura de seguro |

---

## Reglas de seguridad (human-in-the-loop)

1. **Confirmación obligatoria.** Las herramientas que escriben en la BD devuelven
   un aviso y **no ejecutan** si se invocan con `confirmado=False`.
2. **Máquina de estados respetada.** No se reagenda ni cancela una cita en estado
   terminal (`ATENDIDA`, `CANCELADA`). Ver `docs/ESTADOS_CITA.md`.
3. **Filtro de inyección de prompts.** `_detect_injection()` en `core/agent.py`
   inspecciona la entrada del usuario antes de dársela al modelo.

> **Pendiente de cerrar:** `/api/v1/rag/chat` ejecuta SQL arbitrario vía
> tool-calling y está disponible para **cualquier** usuario autenticado, sin
> distinción de rol. Está documentado en `docs/SEGURIDAD.md` como pendiente
> prioritario. Si añades herramientas nuevas que escriban en la BD, aplica el
> mismo patrón `confirmado=True`.

---

## Endpoints

Todos bajo `/api/v1`, todos requieren `Authorization: Bearer <token>`.

### RAG

| Método | Ruta | Propósito |
|---|---|---|
| `GET` | `/rag/health` | Estado de Ollama + nº de vectores |
| `POST` | `/rag/ingest` | Ingesta un documento al store vectorial |
| `POST` | `/rag/ingest-nota/{appointment_id}` | Vectoriza la nota de una cita |
| `POST` | `/rag/search` | Búsqueda semántica directa |
| `POST` | `/rag/chat` | Conversación con el agente |
| `POST` | `/rag/chat/stream` | Ídem, respuesta en streaming SSE |

### Medasist (determinista, sin LLM)

| Método | Ruta | Propósito |
|---|---|---|
| `POST` | `/medasist/reschedule` | Sugiere nueva fecha |
| `POST` | `/medasist/check-conflict` | Verifica solapamiento |
| `POST` | `/medasist/available-slots` | Slots libres |
| `POST` | `/medasist/suggest-followup` | Sugiere seguimiento |

### Ejemplos

```http
GET /api/v1/rag/health
Authorization: Bearer <token>
```

```json
{
  "ollama": "ok",
  "embedding_model": "nomic-embed-text",
  "llm_model": "llama3.2",
  "vector_count": 12
}
```

```http
POST /api/v1/rag/chat
Content-Type: application/json

{
  "message": "¿Qué citas tiene el Dr. Méndez esta semana?",
  "historial": [
    {"role": "user", "content": "Hola"},
    {"role": "assistant", "content": "Hola, soy MedAssist."}
  ]
}
```

```json
{ "respuesta": "El Dr. Carlos Méndez tiene 2 citas programadas..." }
```

---

## Pruebas

```bash
cd backend
./run.sh test test_rag      # suite de integración
```

Requiere la BD levantada **y** Ollama con los modelos descargados. Crea y limpia
sus propios datos con un sufijo único por corrida.

Ver también `docs/CHECKLIST_ENTREGA.md`.