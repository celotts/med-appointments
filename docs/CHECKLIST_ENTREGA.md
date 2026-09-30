# Checklist de entrega

Antes de decir "terminado", pasa esto. Un ítem sin verificar no cuenta como
cumplido: **si no puedes correr el comando, dilo explícitamente**.

---

## 1. Verificación automática (obligatoria)

```bash
make verify-docs
```

Debe terminar con `TODO CORRECTO`. Cubre 9 grupos:

| Grupo | Qué detecta |
|---|---|
| Estados de cita | Enum, semilla y frontend desalineados; uso de `COMPLETADA` |
| Roles | Comparaciones manuales; literales de rol en el front |
| Referencia de API | Rutas del código ausentes en `docs/API.md` |
| Herramientas del agente | `@tool` sin documentar; nombres inventados |
| Conflictos de merge | Marcadores `<<<<<<<` en cualquier `.md` |
| Enlaces internos | Links a documentos que no existen |
| Migraciones | Más de un head (rompe `alembic upgrade head`) |
| Secretos | `.env` versionado; falta `.env.develop` |
| Frontend | Errores de TypeScript; clases Tailwind inexistentes |

```bash
make test           # backend (pytest) + frontend (tsc)
```

Si `make test` falla porque no hay BD u Ollama, **no afirmes que funciona**.
Reporta exactamente qué no pudiste ejecutar.

---

## 2. Lo que cambiaste

- [ ] ¿Funciona el flujo afectado de punta a punta?
- [ ] ¿Probaste el caso de error, no solo el feliz?
- [ ] ¿El mensaje de error es útil para quien lo lee?

---

## 3. Backend

- [ ] Sin imports sin usar (`ruff`)
- [ ] Todo endpoint nuevo con `response_model`
- [ ] Endpoints administrativos con `Depends(require_admin)`
- [ ] Endpoints que tocan datos clínicos filtrando por propietario
- [ ] `404` (no `403`) para recursos ajenos
- [ ] Ninguna comparación de rol a mano
- [ ] Ningún estado de cita fuera de los 8 canónicos
- [ ] Ninguna transición fuera de `VALID_TRANSITIONS`
- [ ] Módulo nuevo ≤ 250 líneas
- [ ] Sin código muerto

```bash
cd backend && venv/bin/python -m ruff check app/ alembic/ tests/
cd backend && venv/bin/python -m pytest -q
```

> El proyecto arrastra ~430 errores de `ruff` preexistentes. No los arregles de
> paso: verifica que **tus** archivos están limpios.

---

## 4. Frontend

- [ ] `tsc --noEmit` sin errores
- [ ] Build completo
- [ ] Sin imports sin usar (rompe la compilación: `noUnusedLocals` está activo)
- [ ] Colores con tokens, no hex sueltos
- [ ] Roles con `hasRole()` / `isAdmin()`, no literales
- [ ] Tokens con `api/tokenStorage.ts`, no `localStorage` directo
- [ ] Errores mostrados con `toast.error(...)`
- [ ] Componente nuevo ≤ 250 líneas

```bash
cd front && npm run typecheck
cd front && npm run build
```

---

## 5. Base de datos

Si tocaste el esquema o los catálogos:

- [ ] La migración es idempotente
- [ ] `downgrade()` existe
- [ ] `alembic heads` muestra **un solo** head
- [ ] La semilla SQL corre dos veces sin error
- [ ] Actualizaste los archivos acoplados (ver `docs/ESTADOS_CITA.md`)

```bash
cd backend && venv/bin/python -m alembic heads
docker exec -i medical_pgvector psql -U postgres -d appointment < script_BD/seeds/seed_catalogs.sql
docker exec -i medical_pgvector psql -U postgres -d appointment < script_BD/seeds/seed_catalogs.sql   # idempotente
```

---

## 6. Documentación

- [ ] Todo `.md` que escribiste está en `docs/` (o es `AGENTS.md` / `TRABAJO_ACUERDO.md`)
- [ ] `docs/API.md` regenerado si tocaste rutas
- [ ] Nada afirmado que no hayas verificado leyendo el código
- [ ] Enlaces internos resuelven
- [ ] Comentarios en español

```bash
python scripts/gen_api_docs.py    # si tocaste endpoints
```

---

## 7. Seguridad

- [ ] Sin secretos en archivos versionados
- [ ] Sin datos de pacientes en logs ni errores
- [ ] Consultas parametrizadas (sin f-strings en SQL)
- [ ] Nada de `eval`, `exec` ni SQL interpolado

---

## Errores frecuentes

| Síntoma | Causa habitual |
|---|---|
| *"Status EN ESPERA does not exist"* | Falta correr migraciones o la semilla |
| `403` en un endpoint que debería funcionar | Comparación de rol a mano; usa `require_admin` |
| Un color no se aplica | Clase `medical-*` inexistente en el tema |
| Un estado no aparece en el catálogo | Seed desactualizado; corre `make seed` |
| `alembic upgrade head` falla | Más de un head; revisa `alembic heads` |
| `tsc` se queja de un import "no usado" | `noUnusedLocals` está activo; bórralo |
| El agente responde con datos inventados | El store vectorial está vacío; indexa documentos |

---

## Reporte final

Cuando entregues, incluye:

1. **Qué cambiaste**, en una frase por archivo.
2. **Qué verificaste** y con qué comando.
3. **Qué no pudiste verificar** y por qué (BD apagada, Ollama ausente, etc.).
4. **Qué queda pendiente**, si algo.

Nunca declares algo terminado sin el comando que lo demuestra.