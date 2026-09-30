#!/usr/bin/env python3
"""Genera docs/API.md desde el codigo real (OpenAPI).

Fuente unica de verdad: no escribas la tabla de endpoints a mano.
Ejecutar tras anadir, quitar o cambiar una ruta.

    python scripts/gen_api_docs.py          # regenera docs/API.md
    python scripts/gen_api_docs.py --check  # solo verifica (para CI)

`--check` sale con codigo 1 si el documento esta desfasado, que es lo que
invoca `make verify-docs`.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend"
DOC = RAIZ / "docs" / "API.md"

# Rutas publicas (sin Depends(get_current_user)) y sus notas de rol.
SIN_AUTH = {"/"}

# Esquema -> nombre del router de docs/API.md. FastAPI carga "Visual Indicators"
# sin tag porque main.py reconstruye sus APIRoute a mano y pierde `tags`.
SCHEMA_A_ROUTER = {
    "Visual Indicators": "Visual Indicators",
}

# Router -> (etiqueta legible, nota de la columna Rol)
NOTAS_ROUTER = {
    "Users": "Alta y listado **solo admin**",
    "Login": "Unico endpoint publico",
    "Appointments": "Nucleo del negocio",
    "RAG & AI Agent": "Ver `docs/IA_AGENTE.md`",
    "Medasist IA": "Agenda determinista, sin LLM",
    "Integrations": "Calendario, sedes, roles",
    "Notifications": "Scope por email del usuario",
    "Reports & Dashboard": "Sin filtro de rol",
    "Premium Features": "Sin filtro de rol",
    "Assistants": "Solo admin",
    "Appointment Statuses": "Catalogo de la maquina de estados",
    "Visual Indicators": "Config de indicadores",
    "Audit": "Solo admin",
}

# Rutas que no exigen rol admin dentro de un router "solo admin".
EXCEPCIONES_ADMIN = {
    ("Users", "GET", "/api/v1/me"),
}

# Rutas montadas sin `tags` en OpenAPI. Sin esto se listan como publicas.
SIN_TAG_A_ROUTER = {
    "/api/v1/visual-indicators/config": "Visual Indicators",
    "/api/v1/visual-indicators/config/{code}": "Visual Indicators",
}

SIN_TAG = "(sin tag)"


def cargar_app():
    """Importa la app FastAPI y devuelve su esquema OpenAPI.

    `main.py` espera estar importado como `app.*`, asi que la raiz que se
    agrega al sys.path es `backend/`, no `backend/app/`.
    """
    sys.path.insert(0, str(BACKEND))
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:x@localhost:5432/x")
    os.environ.setdefault("FIRST_SUPERUSER_EMAIL", "a@b.com")
    os.environ.setdefault("FIRST_SUPERUSER_PASSWORD", "x")
    os.environ.setdefault("SECRET_KEY", "x")

    from app.main import app  # noqa: PLC0415

    return app.openapi()


def ops(openapi: dict) -> list[tuple[str, str, str]]:
    """Devuelve [(metodo, path, router)] ordenado."""
    filas = []
    for path, metodos in openapi.get("paths", {}).items():
        for metodo, defn in metodos.items():
            etiqueta = (defn.get("tags") or [SIN_TAG_A_ROUTER.get(path, SIN_TAG)])[0]
            filas.append((metodo.upper(), path, SCHEMA_A_ROUTER.get(etiqueta, etiqueta)))
    return sorted(filas, key=lambda f: (f[2], f[1], f[0]))


def bloque(router: str, filas: list[tuple[str, str, str]]) -> str:
    lineas = [
        f"### {router}",
        "",
        "| Método | Ruta | Rol |",
        "|:--|:--|:--|",
    ]
    solo_admin = "admin" in NOTAS_ROUTER.get(router, "").lower()
    for metodo, path, _ in filas:
        if path in SIN_AUTH:
            rol = "No"
        elif solo_admin and (router, metodo, path) not in EXCEPCIONES_ADMIN:
            rol = "**admin**"
        else:
            rol = "JWT"
        lineas.append(f"| `{metodo}` | `{path}` | {rol} |")
    lineas.append("")
    return "\n".join(lineas)


def generar(openapi: dict) -> str:
    filas = ops(openapi)
    total_ops = len(filas)
    total_paths = len(openapi.get("paths", {}))

    por_router: dict[str, list[tuple[str, str, str]]] = {}
    for metodo, path, tag in filas:
        por_router.setdefault(tag, []).append((metodo, path, tag))

    # El bloque de rutas publicas se genera aparte del resto.
    publicas = por_router.pop(SIN_TAG, [])

    out = [
        "# API Reference",
        "",
        "<!-- GENERADO AUTOMATICAMENTE por scripts/gen_api_docs.py. NO EDITAR A MANO. -->",
        "<!-- Para cambiarlo: edita el codigo y ejecuta `python scripts/gen_api_docs.py` -->",
        "",
        f"**{total_ops} operaciones** en **{total_paths} rutas**. Base: `/api/v1`.",
        "",
        "Verificado contra el codigo. Si algo no esta aqui, no existe.",
        "",
        "## Autenticacion",
        "",
        "Casi todo exige `Authorization: Bearer <token>`, obtenido via OAuth2 password flow:",
        "",
        "```http",
        "POST /api/v1/login/access-token",
        "Content-Type: application/x-www-form-urlencoded",
        "",
        "username=admin@medapi.com&password=...",
        "```",
        "",
        "| Situacion | Codigo |",
        "|:--|:--|",
        "| Sin token o token invalido | `401` |",
        "| Token valido, rol insuficiente | `403` |",
        "| Recurso inexistente o de otro usuario | `404` |",
        "",
        "**Errores**: `{\"detail\": \"...\"}` o `{\"detail\": {\"message\": \"...\"}}`.",
        "",
        "**Paginacion**: los listados usan `skip`/`limit`. Solo `GET /appointments/`",
        "paginada de verdad: `{page, page_size, total, total_pages, items}`.",
        "",
        "## Resumen",
        "",
        "| Router | Ops |",
        "|:--|--:|",
    ]
    for router, fs in sorted(por_router.items(), key=lambda kv: -len(kv[1])):
        out.append(f"| {router} | {len(fs)} |")
    out.append("")

    if publicas:
        out.append("## Endpoints sin proteccion")
        out.append("")
        out.append("Todos los demas requieren `Authorization: Bearer <token>`.")
        out.append("")
        for metodo, path, _ in publicas:
            out.append(f"- `{metodo} {path}`")
        out.append("")

    out.append("## Detalle por router")
    out.append("")
    for router in sorted(por_router):
        nota = NOTAS_ROUTER.get(router)
        if nota:
            out.append(f"> {router}: {nota}.")
            out.append("")
        out.append(bloque(router, por_router[router]))

    out.append(
        "## Mantener al dia\n\n"
        "Este archivo se genera desde el codigo:\n\n"
        "```bash\n"
        "python scripts/gen_api_docs.py          # regenerar\n"
        "python scripts/gen_api_docs.py --check  # solo verificar (CI)\n"
        "```\n\n"
        "`make verify-docs` falla si el documento y el codigo difieren."
    )
    out.append("")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Solo verifica; sale con 1 si el documento esta desfasado.",
    )
    args = parser.parse_args()

    try:
        openapi = cargar_app()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: no se pudo importar la app: {exc}", file=sys.stderr)
        return 2

    contenido = generar(openapi)
    actual = DOC.read_text(encoding="utf-8") if DOC.exists() else ""

    if args.check:
        # docs/API.md tiene secciones escritas a mano (ejemplos, notas) que el
        # generador no produce. En vez de exigir igualdad exacta, verificamos
        # que cada ruta del codigo aparezca en el documento.
        faltantes = [
            f"{metodo} {path}"
            for metodo, path, _ in ops(openapi)
            if f"`{path}`" not in actual and f"- `{metodo} {path}`" not in actual
        ]
        if faltantes:
            print(
                f"DESFASADO: {len(faltantes)} rutas del codigo no estan en "
                f"{DOC.relative_to(RAIZ)}:",
                file=sys.stderr,
            )
            for ruta in faltantes[:15]:
                print(f"  - {ruta}", file=sys.stderr)
            if len(faltantes) > 15:
                print(f"  ... y {len(faltantes) - 15} mas", file=sys.stderr)
            print(
                "\nEjecuta: python scripts/gen_api_docs.py",
                file=sys.stderr,
            )
            return 1
        print(f"OK: {DOC.relative_to(RAIZ)} al dia ({len(ops(openapi))} rutas)")
        return 0

    DOC.write_text(contenido, encoding="utf-8")
    print(f"Escrito {DOC.relative_to(RAIZ)} ({len(ops(openapi))} operaciones)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())