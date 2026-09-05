# 🤖 Módulo de Inteligencia Artificial & Agente MedAssist

Documentación completa de la arquitectura, configuración, endpoints y herramientas del subsistema de **IA y Búsqueda Aumentada por Generación (RAG)** en el proyecto `med-appointments`.

---

## 🏛️ Arquitectura General

El módulo de IA combina modelos de lenguaje locales con almacenamiento vectorial en PostgreSQL para ofrecer consultas en lenguaje natural y asistencia en la gestión médica con estricta privacidad de datos.

```text
                  ┌───────────────────────────────┐
                  │      Cliente / Frontend       │
                  └──────────────┬────────────────┘
                                 │ HTTP (JWT)
                                 ▼
                  ┌───────────────────────────────┐
                  │       FastAPI Endpoints       │
                  │    (/api/v1/rag/* en rag.py)  │
                  └──────┬─────────────────┬──────┘
                         │                 │
            Chat / Tools │                 │ Ingesta / Búsqueda
                         ▼                 ▼
                  ┌────────────────────────┐     ┌─────────────────────────┐
                  │  Agente Conversacional │     │        Módulo RAG       │
                  │    (core/agent.py)     │◄───┤    (core/rag.py)        │
                  └──────────┬─────────────┘     └────────────┬────────────┘
                             │                                │
                Tool Calling │                                │ Embeddings / Búsqueda
                             ▼                                ▼
                  ┌───────────────────────────┐     ┌───────────────────────────┐
                  │       Ollama Local        │     │  PostgreSQL + pgvector    │
                  │ - LLM: llama3.2           │     │ - Tabla: docs vectoriales │
                  │ - Embed: nomic-embed-text │     │ - Índice: HNSW Coseno     │
                  └───────────────────────────┘     └───────────────────────────┘
```

* **Privacidad Total (On-Premise / HIPAA):** Tanto el LLM como el modelo de embeddings corren en un servidor local **Ollama**. La información confidencial del paciente nunca se envía a servicios en la nube (OpenAI, Anthropic, etc.).
* **Framework:** LangChain (`langchain-ollama`, `langchain-core`).
* **Base Vectorial:** Extensión `pgvector` sobre PostgreSQL 16 con índice HNSW (`vector_cosine_ops`).

---

## ⚙️ Requisitos y Configuración de Ollama

El backend se conecta por defecto a Ollama en `http://localhost:11434` (o `http://host.containers.internal:11434` en Docker/Podman).

### 1. Descargar los modelos necesarios en Ollama

```bash
ollama pull nomic-embed-text
ollama pull llama3.2
```

### 2. Variables de entorno (.env)

```env
# Ollama / RAG
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=llama3.2
EMBEDDING_DIM=768
```

---

## 🗄️ Base de Datos Vectorial

Definida en `script_BD/init.sql`:

```sql
CREATE TABLE documentos_vectoriales (
    id SERIAL PRIMARY KEY,
    ref_tipo VARCHAR(50) NOT NULL, -- Ej: 'NOTA_MEDICA', 'DOCUMENTO', 'GUIA_CLINICA'
    ref_id INT,                    -- ID del registro origen (ej: notas_medicas.id)
    titulo VARCHAR(255) NOT NULL,
    contenido TEXT NOT NULL,
    embedding VECTOR(768),         -- Vector generado por nomic-embed-text
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índice HNSW para búsqueda rápida por similitud coseno
CREATE INDEX idx_documentos_vectoriales_embedding 
ON documentos_vectoriales 
USING hnsw (embedding vector_cosine_ops);
```

---

## 🛠️ Agente Conversacional: MedAssist

El agente está definido en `backend/app/core/agent.py`. Utiliza el ciclo **ReAct** (Reasoning + Acting) con capacidad de ejecutar hasta 6 llamadas a herramientas por turno.

### Las 9 Herramientas (Tools) del Agente

| Herramienta | Tipo | Descripción |
| --- | :---: | --- |
| `buscar_en_documentos` | Lectura / RAG | Búsqueda semántica sobre `documentos_vectoriales` usando similitud coseno. Permite filtrar opcionalmente por `ref_tipo` (p.ej., 'NOTA_MEDICA', 'DOCUMENTO'). |
| `consultar_citas_paciente` | Lectura | Busca las citas activas o históricas de un paciente por nombre/apellido (`ILIKE`). |
| `consultar_citas_medico` | Lectura | Consulta el calendario de citas de un médico específico. |
| `buscar_pacientes` | Lectura | Búsqueda parcial de pacientes en el catálogo. |
| `buscar_medicos` | Lectura | Búsqueda parcial de médicos y su especialidad asociada. |
| `contar_registros` | Lectura | Resumen global (total de pacientes, médicos, citas y notas). |
| `sugerir_reagendamiento` | Propuesta | Arma la propuesta de reagendamiento sin aplicarla en la BD. |
| `ejecutar_reagendamiento` | **Acción** | Cambia la fecha de la cita a estado `REAGENDADA`. **Requiere `confirmado=True`**. |
| `cancelar_cita` | **Acción** | Transiciona la cita a estado `CANCELADA`. **Requiere `confirmado=True`**. |

### 🔒 Reglas de Seguridad (Human-in-the-Loop)

1. **Confirmación obligatoria:** Las herramientas que modifican la base de datos (`ejecutar_reagendamiento` y `cancelar_cita`) devuelven un mensaje de advertencia si se invocan con `confirmado=False`.
2. **Respeto a la máquina de estados:** No se permite reagendar ni cancelar citas que ya se encuentren en estados terminales (`CANCELADA`, `COMPLETADA`).

---

## 📡 Endpoints de la API

Todos los endpoints están bajo `/api/v1` y requieren autenticación mediante encabezado `Authorization: Bearer <TOKEN>`.

### 1. Estado del servicio

* **`GET /api/v1/rag/health`**
  Verifica la conexión con Ollama y cuenta los documentos vectorizados.

  ```json
  {
    "ollama": "ok",
    "embedding_model": "nomic-embed-text",
    "llm_model": "llama3.2",
    "vector_count": 12
  }
  ```

### 2. Ingesta manual de documentos

* **`POST /api/v1/rag/ingest`**

  ```json
  {
    "ref_tipo": "DOCUMENTO",
    "ref_id": null,
    "titulo": "Guía de manejo de Hipertensión",
    "contenido": "Criterios diagnósticos y tratamiento farmacológico de primera línea..."
  }
  ```

### 3. Ingesta de nota médica

* **`POST /api/v1/rag/ingest-nota/{cita_id}`**
  Extrae el diagnóstico, tratamiento y observaciones de la nota médica de una cita y genera su vector automáticamente.

### 4. Búsqueda semántica directa

* **`POST /api/v1/rag/search`**

  ```json
  {
    "query": "tratamiento para dolor de cabeza crónico",
    "ref_tipo": "NOTA_MEDICA",
    "k": 3
  }
  ```

### 5. Chat con el Agente MedAssist

* **`POST /api/v1/rag/chat`**

  ```json
  {
    "message": "¿Qué citas tiene programadas el Dr. Méndez para esta semana?",
    "historial": [
      {"role": "user", "content": "Hola"},
      {"role": "assistant", "content": "Hola, soy MedAssist. ¿En qué puedo ayudarte hoy?"}
    ]
  }
  ```

  **Respuesta:**

  ```json
  {
    "respuesta": "El Dr. Carlos Méndez tiene 2 citas programadas:\n1. Cita #14 con el paciente Lucía Fernández el 12 de septiembre a las 11:00 AM..."
  }
  ```

---

## 🧪 Pruebas Automatizadas

El proyecto incluye una suite de smoke tests integral contra la base de datos real y Ollama:

```bash
cd backend
./run.sh test test_rag
```

Esta prueba valida automáticamente:

1. Conexión y health check con Ollama.
2. Ingesta y generación de embeddings.
3. Búsqueda semántica con cálculo de score de similitud.
4. Consulta y respuestas conversacionales del agente con Tool Calling.
5. Intento de mutación sin confirmación (bloqueado) y con confirmación (ejecutado).
6. Limpieza posterior de los datos de prueba.
