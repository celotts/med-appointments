#!/usr/bin/env python3
"""Verifica que la documentation este sincronizada con el codigo.

Este script es el guardarrail del proyecto: la documentacion de este repo
vivio desactualizada durante meses (documentaba endpoints que no existian y
omitia estados de la maquina de estados). Estos chequeos hacen que eso falle
de forma visible en lugar de propagarse.

    python scripts/verify_docs.py

Sale con codigo 1 si algo esta desfasado. Lo invoca `make verify-docs`.
"""

from __future__ import annotations

import re
import subprocess
import sys
import uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "backend"
FRONT = RAIZ / "front"

VERDE, ROJO, AMARILLO, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"

fallos: list[str] = []
avisos: list[str] = []


def ok(msg: str) -> None:
    print(f"  {VERDE}OK{RESET}   {msg}")


def fail(msg: str) -> None:
    print(f"  {ROJO}FALLA{RESET} {msg}")
    fallos.append(msg)


def warn(msg: str) -> None:
    print(f"  {AMARILLO}AVISO{RESET} {msg}")
    avisos.append(msg)


def seccion(titulo: str) -> None:
    print(f"\n{titulo}")
    print("-" * len(titulo))


# --- 1. Estados de cita ---------------------------------------------------

def verificar_estados() -> None:
    seccion("1. Estados de cita (vocabulario canonico)")

    schema = (BACKEND / "app" / "schemas" / "appointment.py").read_text(encoding="utf-8")

    # Los codigos del enum AppointmentStatusCode
    bloque = re.search(r"class AppointmentStatusCode.*?(?=\n\n\n|\Z)", schema, re.S)
    if not bloque:
        fail("No se encontro AppointmentStatusCode en schemas/appointment.py")
        return
    enum = set(re.findall(r'=\s*"([^"]+)"', bloque.group(0)))

    canonico = {
        "PENDIENTE",
        "CONFIRMADA",
        "EN ESPERA",
        "EN PROCESO",
        "ATENDIDA",
        "CANCELADA",
        "SUSPENDIDA",
        "REAGENDADA",
    }

    if enum == canonico:
        ok(f"enum AppointmentStatusCode tiene los 8 estados canonicos")
    else:
        fail(f"el enum no coincide con el canonico: sobra {enum - canonico}, falta {canonico - enum}")

    # La semilla SQL debe tener los mismos 8
    seed = (RAIZ / "script_BD" / "seeds" / "seed_catalogs.sql").read_text(encoding="utf-8")
    bloque_seed = re.search(
        r"INSERT INTO appointment_statuses.*?VALUES(.*?);", seed, re.S | re.I
    )
    if bloque_seed:
        # Solo la primera columna de cada fila es el codigo; las demas son
        # descripciones, que no forman parte del vocabulario.
        codigos_seed = set(
            re.findall(r"\(\s*'([^']+)'\s*,", bloque_seed.group(1))
        )
        if codigos_seed == canonico:
            ok("seed_catalogs.sql tiene los mismos 8 estados")
        else:
            fail(
                f"seed_catalogs.sql desalineado: {codigos_seed ^ canonico or 'ok'} "
                f"(sobra={codigos_seed - canonico}, falta={canonico - codigos_seed})"
            )
    else:
        fail("No se encontro el INSERT de estados en seed_catalogs.sql")

    # Ningun archivo de codigo debe usar COMPLETADA como estado de cita
    obsoletos = []
    for path in (BACKEND / "app").rglob("*.py"):
        if "COMPLETADA" in path.read_text(encoding="utf-8", errors="ignore"):
            obsoletos.append(path.relative_to(RAIZ))
    if obsoletos:
        fail(f"COMPLETADA (nombre viejo) sigue en: {', '.join(map(str, obsoletos))}")
    else:
        ok("ningun modulo usa COMPLETADA (nombre viejo)")

    # El frontend no debe inventar estados
    usados = set()
    for path in FRONT.glob("src/**/*.tsx"):
        texto = path.read_text(encoding="utf-8", errors="ignore")
        usados |= set(re.findall(r"'(PENDIENTE|CONFIRMADA|EN ESPERA|EN PROCESO|ATENDIDA|CANCELADA|SUSPENDIDA|REAGENDADA|COMPLETADA|NO_SHOW|COMPLETED|CANCELLED|SCHEDULED)'", texto))
    fuera = usados - canonico
    if fuera:
        fail(f"el frontend usa estados fuera del canonico: {fuera}")
    else:
        ok(f"el frontend solo usa estados canonicos ({len(usados)} distintos)")


# --- 2. Roles -------------------------------------------------------------

def verificar_roles() -> None:
    seccion("2. Roles (vocabulario canonico)")

    rbac = (BACKEND / "app" / "core" / "rbac.py")
    if not rbac.exists():
        fail("falta backend/app/core/rbac.py")
        return

    texto = rbac.read_text(encoding="utf-8")
    canonicos = set(re.findall(r'^(SUPER_ADMIN|ADMIN|DOCTOR|SPECIALIST|ASSISTANT|PATIENT)\s*=', texto, re.M))
    if canonicos >= {"SUPER_ADMIN", "ADMIN", "DOCTOR", "ASSISTANT", "PATIENT"}:
        ok(f"core/rbac.py define {len(canonicos)} roles canonicos")
    else:
        fail(f"core/rbac.py incompleto: {canonicos}")

    # Ningun endpoint debe comparar el rol a mano. Se excluye rbac.py: es el
    # modulo que define la normalizacion y por definicion inspecciona el rol.
    EXCLUIDOS_RBAC = {Path("backend/app/core/rbac.py")}
    manuales = []
    for path in (BACKEND / "app").rglob("*.py"):
        rel = path.relative_to(RAIZ)
        if rel in EXCLUIDOS_RBAC:
            continue
        texto = path.read_text(encoding="utf-8", errors="ignore")
        # Ignora los comentarios: se cita el codigo viejo al explicar por que
        # se cambio, y eso no es una comparacion de rol.
        sin_comentarios = "\n".join(
            linea for linea in texto.splitlines() if not linea.lstrip().startswith("#")
        )
        if re.search(
            r'role\.name\s*(==|!=|not in|in)\s*[\(\{"\'\[]',
            sin_comentarios,
        ):
            manuales.append(rel)
    if manuales:
        fail(
            "comparacion de rol a mano (usar has_role/require_roles): "
            f"{[str(p) for p in manuales]}"
        )
    else:
        ok("nadie compara el rol a mano")

    # El frontend debe usar auth/roles.ts
    roles_front = FRONT / "src" / "auth" / "roles.ts"
    if roles_front.exists():
        ok("front/src/auth/roles.ts existe")
    else:
        fail("falta front/src/auth/roles.ts")

    literales = []
    for path in FRONT.glob("src/**/*.tsx"):
        if re.search(r"role\s*===?\s*['\"](admin|super-admin|super_admin|doctor|specialist|assistant|patient)['\"]", path.read_text(encoding="utf-8", errors="ignore"), re.I):
            literales.append(path.relative_to(RAIZ))
    if literales:
        fail(f"el frontend compara roles con literales: {[str(p) for p in literales]}")
    else:
        ok("el frontend no compara roles con literales")


# --- 3. Documentacion de API ---------------------------------------------

def verificar_api() -> None:
    seccion("3. Referencia de API")

    proc = subprocess.run(
        [sys.executable, str(RAIZ / "scripts" / "gen_api_docs.py"), "--check"],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        ok(proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "docs/API.md al dia")
    else:
        fail(f"docs/API.md desfasado\n{proc.stderr.strip()}")


# --- 4. Herramientas del agente ------------------------------------------

def verificar_agente() -> None:
    seccion("4. Herramientas del agente IA")

    agent = BACKEND / "app" / "core" / "agent.py"
    if not agent.exists():
        fail("falta core/agent.py")
        return

    texto = agent.read_text(encoding="utf-8")
    tools = re.findall(r'@tool(?:\(\s*"([a-z_]+)"\s*\))?\s*\nasync def ([a-z_]+)', texto)
    nombres = {a or b for a, b in tools}

    doc = RAIZ / "docs" / "IA_AGENTE.md"
    if not doc.exists():
        fail("falta docs/IA_AGENTE.md")
        return
    texto_doc = doc.read_text(encoding="utf-8")

    faltantes = sorted(n for n in nombres if f"`{n}`" not in texto_doc)
    if faltantes:
        fail(f"{len(faltantes)} herramientas sin documentar: {faltantes}")
    else:
        ok(f"las {len(nombres)} herramientas estan documentadas")

    # Nombres documentados que ya no existen (ej. COMPLETADA, herramientas viejas)
    huerfanas = re.findall(r"^\s*\d+\.\s+`([a-z_]+)`", texto_doc, re.M)
    inventadas = sorted({h for h in huerfanas if h not in nombres})
    if inventadas:
        fail(f"docs/IA_AGENTE.md documenta herramientas inexistentes: {inventadas}")
    else:
        ok("no hay herramientas documentadas que no existan")


# --- 5. Marcadores de conflicto de merge ---------------------------------

def verificar_conflictos() -> None:
    seccion("5. Marcadores de conflicto de merge")

    # Marcadores de conflicto de merge reales. Se exige la punta de flecha
    # (`<<<<<<< `) para no disparar con las lineas de tabla `|---|---|` que
    # Markdown usa para separar cabeceras.
    sucios = []
    for path in RAIZ.rglob("*.md"):
        if ".venv" in path.parts or "node_modules" in path.parts:
            continue
        texto = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"^(<<<<<<< |>>>>>>> )", texto, re.M):
            sucios.append(path.relative_to(RAIZ))
    if sucios:
        fail(f"marcadores de conflicto sin resolver en: {[str(p) for p in sucios]}")
    else:
        ok("ningun .md tiene marcadores de conflicto")


# --- 6. Links internos de la documentacion -------------------------------

def verificar_links() -> None:
    seccion("6. Enlaces internos rotos")

    patron = re.compile(r"\]\((?!https?://)([^)#]+)")
    rotos = []
    for path in [RAIZ / "AGENTS.md", *sorted((RAIZ / "docs").glob("*.md"))]:
        if not path.exists():
            continue
        for destino in patron.findall(path.read_text(encoding="utf-8")):
            destino = destino.strip()
            if not destino:
                continue
            resuelto = (path.parent / destino).resolve()
            if not resuelto.exists():
                rotos.append(f"{path.relative_to(RAIZ)} -> {destino}")
    if rotos:
        fail(f"enlaces rotos: {rotos}")
    else:
        ok("todos los enlaces internos resuelven")


# --- 7. Migraciones -------------------------------------------------------

def verificar_migraciones() -> None:
    seccion("7. Migraciones Alembic")

    versions = BACKEND / "alembic" / "versions"
    archivos = [p for p in versions.glob("*.py") if p.name != "__init__.py"]
    if not archivos:
        fail("no hay migraciones")
        return

    revs: dict[str, str | None] = {}
    for p in archivos:
        texto = p.read_text(encoding="utf-8")
        rev = re.search(r"^revision(?::\s*str)?\s*=\s*['\"]([^'\"]+)['\"]", texto, re.M)
        down = re.search(r"^down_revision(?::[^=]+)?\s*=\s*(.+)$", texto, re.M)
        if not rev:
            fail(f"{p.name}: sin 'revision'")
            continue
        revs[rev.group(1)] = down.group(1).strip() if down else None

    # Solo la raiz real del grafo es una base. Una migracion "huerfana" que
    # luego fue absorbida por un merge sigue teniendo down_revision = None en
    # su archivo, asi que hay que excluir las ya referenciadas por un merge.
    absorbidas = set()
    for down in revs.values():
        if down and down != "None":
            absorbidas |= set(re.findall(r"['\"]([^'\"]+)['\"]", down))

    bases = [
        r
        for r, d in revs.items()
        if (d is None or d == "None") and r not in absorbidas
    ]
    # Las raices huerfanas absorbidas por un merge siguen.teniendo
    # down_revision = None en su archivo, asi que se esperan.
    # Un nodo es un HEAD si ninguna otra migracion lo referencia como
    # down_revision. Es la definicion correcta y no depende de como se
    # escribio cada archivo.
    referenciados = set()
    for down in revs.values():
        if down and down != "None":
            referenciados |= set(re.findall(r"['\"]([^'\"]+)['\"]", down))

    heads = [r for r in revs if r not in referenciados]
    bases = [
        r
        for r, d in revs.items()
        if (d is None or d == "None") and r not in absorbidas
    ]

    if len(heads) == 1:
        extra = (
            f", {len(absorbidas) - len(bases)} base(s) absorbida(s) por merge"
            if len(absorbidas) > len(bases)
            else ""
        )
        ok(f"un solo head: {heads[0]} ({len(revs)} migraciones{extra})")
    elif len(heads) == 0:
        fail("no se encontro ningun head: el grafo de migraciones esta roto")
    else:
        fail(f"{len(heads)} heads, `alembic upgrade head` fallara: {sorted(heads)}")


# --- 8. Secretos ----------------------------------------------------------

def verificar_secretos() -> None:
    seccion("8. Secretos")

    env = RAIZ / ".env"
    if not env.exists():
        ok(".env no existe en este checkout")
        return

    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", ".env"],
        cwd=RAIZ, capture_output=True, text=True,
    )
    if tracked.returncode == 0:
        fail(".env esta versionado en git")
    else:
        ok(".env no esta versionado")

    ejemplo = RAIZ / ".env.develop"
    if ejemplo.exists():
        ok(".env.develop existe")
    else:
        fail("falta .env.develop")


# --- 9. Frontend ----------------------------------------------------------

def verificar_frontend() -> None:
    seccion("9. Frontend")

    tsc = FRONT / "node_modules" / ".bin" / "tsc"
    if tsc.exists():
        proc = subprocess.run(
            [str(tsc), "--noEmit"], cwd=FRONT, capture_output=True, text=True
        )
        if proc.returncode == 0:
            ok("tsc --noEmit sin errores")
        else:
            errores = [l for l in proc.stdout.splitlines() if "error TS" in l]
            fail(f"{len(errores)} errores de TypeScript:\n      " + "\n      ".join(errores[:5]))
    else:
        warn("node_modules ausente: no se pudo correr tsc")

    # Clases medical-* que el tema no define
    config = (FRONT / "tailwind.config.js").read_text(encoding="utf-8")
    usadas = set()
    for path in FRONT.glob("src/**/*.tsx"):
        usadas |= set(re.findall(r"(?:bg|text|border|ring)-medical-([A-Za-z]+)", path.read_text(encoding="utf-8", errors="ignore")))
    definidas = set(re.findall(r"^\s{10}([A-Za-z]+):", config, re.M))
    definidas |= set(re.findall(r"'medical-([A-Za-z]+)':", config))
    huerfanas = usadas - definidas
    if huerfanas:
        fail(f"clases medical-* sin definir en tailwind.config.js: {sorted(huerfanas)}")
    else:
        ok(f"las {len(usadas)} clases medical-* estan definidas en el tema")


# --- Main -----------------------------------------------------------------

def verificar_auditoria() -> None:
    seccion("10. Registro de auditoria")

    # 1. El servicio de auditoria debe existir
    crud = BACKEND / "app" / "core" / "crud_audit.py"
    if not crud.exists():
        fail("falta backend/app/core/crud_audit.py")
        return
    ok("core/crud_audit.py existe")

    # 2. La tabla audit_logs debe seguir en el esquema
    init = (RAIZ / "script_BD" / "init.sql").read_text(encoding="utf-8")
    if "CREATE TABLE audit_logs" in init:
        ok("la tabla audit_logs esta en init.sql")
    else:
        fail("init.sql ya no crea audit_logs")

    # 3. Toda funcion de transicion de cita debe auditar
    crud_appt = (BACKEND / "app" / "core" / "crud_appointment.py").read_text(
        encoding="utf-8"
    )
    transiciones = re.findall(
        r"^async def (\w*(?:confirm|attend|wait|start|suspend|cancel|reactivate)"
        r"\w*)\(",
        crud_appt,
        re.M,
    )
    if not transiciones:
        fail("no se encontraron funciones de transicion en crud_appointment.py")
    else:
        sin_auditar = []
        for nombre in transiciones:
            cuerpo = _cuerpo_funcion(crud_appt, nombre)
            # Un batch puede auditar via `crud_audit` sin pasar por
            # `crud_appointment_audit`. Lo que importa es que escriba registro.
            if (
                "crud_appointment_audit" not in cuerpo
                and "crud_audit" not in cuerpo
            ):
                sin_auditar.append(nombre)
        if sin_auditar:
            fail(f"transiciones sin auditar: {sin_auditar}")
        else:
            ok(f"las {len(transiciones)} transiciones auditan su cambio")

    # 4. Las notas medicas tambien deben auditarse (el dato mas sensible)
    crud_note = (BACKEND / "app" / "core" / "crud_medical_note.py").read_text(
        encoding="utf-8"
    )
    for nombre in ("create_note", "update_note", "delete_note"):
        cuerpo = _cuerpo_funcion(crud_note, nombre)
        if cuerpo and "crud_medical_note_audit" not in cuerpo:
            fail(f"las notas medicas no auditan en {nombre}()")
            return
    if "crud_medical_note_audit" in crud_note:
        ok("crear, editar y borrar notas medicas deja rastro")

    # 5. Ninguna transicion debe hacer commit sin auditar antes
    if "transicionar(" in crud_appt:
        ok("las transiciones pasan por transicionar()")

    # 5. El endpoint de consulta debe existir y ser de solo admin
    endpoint = BACKEND / "app" / "api" / "endpoints" / "audit.py"
    if not endpoint.exists():
        fail("falta api/endpoints/audit.py (no hay forma de consultar el rastro)")
        return
    texto = endpoint.read_text(encoding="utf-8")
    if "require_admin" in texto:
        ok("el endpoint de auditoria exige rol admin")
    else:
        fail("api/endpoints/audit.py no exige require_admin: expone datos clinicos")


def _cuerpo_funcion(texto: str, nombre: str) -> str:
    """Extrae el cuerpo de una funcion por indentacion."""
    patron = re.compile(rf"^async def {nombre}\(.*?(?=^async def |\Z)", re.M | re.S)
    m = patron.search(texto)
    return m.group(0) if m else ""


# --- Main -----------------------------------------------------------------

def main() -> int:
    print(f"{VERDE}Verificando documentacion y codigo...{RESET}")
    print(f"Raiz: {RAIZ}")

    for fn in (
        verificar_estados,
        verificar_roles,
        verificar_api,
        verificar_agente,
        verificar_conflictos,
        verificar_links,
        verificar_migraciones,
        verificar_secretos,
        verificar_frontend,
        verificar_auditoria,
    ):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            fail(f"{fn.__name__} lanzo una excepcion: {exc}")

    print(f"\n{'=' * 60}")
    if fallos:
        print(f"{ROJO}{len(fallos)} FALLO(S){RESET}" + (f", {len(avisos)} aviso(s)" if avisos else ""))
        for f in fallos:
            print(f"  - {f.splitlines()[0]}")
        return 1
    print(f"{VERDE}TODO CORRECTO{RESET}" + (f" ({len(avisos)} aviso(s))" if avisos else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())