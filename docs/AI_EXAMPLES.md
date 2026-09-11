# MedAssist AI - Ejemplos de Uso

## Ejemplos de Conversación con el Agente

### 1. Crear Cita por Lenguaje Natural

```Usuario: "Agenda una cita con el Dr. López para María García"
Agente: Busca automáticamente el paciente y médico, luego solicita fecha/hora o sugiere horarios disponibles.
```

### 2. Reagendamiento Inteligente

```Usuario: "¿Cuál es el mejor horario para reagendar la cita #5?"
Agente: Analiza patrones del paciente y disponibilidad del médico, sugiere los mejores horarios.
```

### 3. Lista de Espera

```Usuario: "No hay citas disponibles, agrégame a la lista de espera"
Agente: Agrega a la cola y notificará cuando se libere un slot.
```

### 4. Predicción de No-Show

```Usuario: "¿Qué probabilidad tiene Juan de no asistir?"
Agente: Analiza historial y predice riesgo de inasistencia con recomendaciones.
```

### 5. Seguimiento Automático

```Usuario: "¿Cuándo debería hacer seguimiento la cita #12?"
Agente: Revisa diagnóstico y sugiere tiempo y especialidad de seguimiento.
```

### 6. Coordinación Multi-Doctor

```Usuario: "¿Qué horarios tienen juntos el Dr. García y el Dr. Martínez el lunes?"
Agente: Encuentra slots donde ambos doctores estén disponibles.
```

### 7. Triaje por Síntomas

```Usuario: "Tengo dolor de cabeza y mareos desde hace 2 días"
Agente: Evalúa urgencia (MEDIA), sugiere Medicina General en 3-5 días.
```

## Herramientas IA Disponibles

| Herramienta | Descripción |
| ------------- | ------------- |
| `sugerir_horarios_disponibles` | Slots vacíos para un médico en fecha específica |
| `analizar_carga_medico` | Estadísticas de ocupación por día |
| `detectar_conflictos` | Citas superpuestas con soluciones |
| `analizar_patrones_paciente` | Preferencias y tasa de cancelaciones |
| `crear_cita_por_lenguaje` | Crear citas desde descripción natural |
| `reagendamiento_inteligente` | Mejores horarios automáticamente |
| `agregar_a_lista_espera` | Gestión de cola de espera |
| `predecir_no_show` | Probabilidad de inasistencia |
| `sugerir_seguimiento` | Recomendación de seguimiento |
| `encontrar_horario_compartido` | Disponibilidad multi-doctor |
| `triagar_por_sintomas` | Evaluación de urgencia |

---

## Endpoint de Chat

### Normal

```http
POST /api/v1/rag/chat
Content-Type: application/json
Authorization: Bearer <token>

{
  "message": "¿Qué horarios tiene disponibles el Dr. García el lunes?",
  "historial": []
}
```

### Streaming (SSE)

```http
POST /api/v1/rag/chat/stream
Content-Type: application/json
Authorization: Bearer <token>

{
  "message": "Analiza la carga del médico #1 esta semana"
}
```

---

## Arquitectura AI

```Frontend → FastAPI → Agent (ReAct) → Tools (21) → PostgreSQL + pgvector
                        ↓
                   LLM (Ollama/llama3.2)
                        ↓
                   Embeddings (nomic-embed-text)
```
