"""Control de acceso por rol (RBAC).

Este modulo es la UNICA fuente de verdad sobre roles del proyecto.
Antes existian cuatro vocabularios incompatibles:

  - BD / init.sql .......... SYSTEM_ROLE, SUPER_ADMIN, ASSISTANT (mayusculas)
  - api/endpoints/assistants  comparaba contra "admin", "super_admin" (minusculas)
  - frontend ............... comparaba contra 'admin', 'super-admin'
  - seed_large_dataset ..... buscaba "SUPER_ADMIN" o "ADMIN"

Como `init.sql` solo crea SUPER_ADMIN, el chequeo de assistants.py nunca
coincidia (403 siempre) y el frontend nunca reconocia a un admin.

Regla: usa SIEMPRE `has_role()` / `require_roles()` y los sets de este
modulo. Nunca compares `user.role.name == "..."` a mano.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable

# --- Vocabulario canonico -------------------------------------------------
# Nombres exactos que se guardan en la tabla `roles` de la BD.
SUPER_ADMIN = "SUPER_ADMIN"
ADMIN = "ADMIN"
DOCTOR = "DOCTOR"
SPECIALIST = "SPECIALIST"
ASSISTANT = "ASSISTANT"
PATIENT = "PATIENT"

# Roles con permiso de administracion de la clinica.
ADMIN_ROLES: frozenset[str] = frozenset({SUPER_ADMIN, ADMIN})

# Roles que gestionan la agenda clinica (operan sobre citas de otros).
CLINICAL_ROLES: frozenset[str] = frozenset({SUPER_ADMIN, ADMIN, DOCTOR, SPECIALIST, ASSISTANT})

# Alias historicos que se aceptan al comparar, por compatibilidad con
# datos ya sembrados y con codigo existente que aun no migra.
_ALIASES: dict[str, str] = {
    "SUPERADMIN": SUPER_ADMIN,
    "ROOT": SUPER_ADMIN,
    "SUPERUSUARIO": SUPER_ADMIN,
    "SECRETARIA": ASSISTANT,
    "RECEPCION": ASSISTANT,
    "RECEPCIONISTA": ASSISTANT,
    "MEDICO": DOCTOR,
}

_NON_ALNUM = re.compile(r"[^A-Z0-9]+")


def normalize_role(role: object) -> str:
    """Normaliza un nombre de rol a su forma canonica en mayusculas.

    Acepta cualquier variante historica:

        normalize_role("super-admin")  -> "SUPER_ADMIN"
        normalize_role("super_admin")  -> "SUPER_ADMIN"
        normalize_role("SuperAdmin")   -> "SUPER_ADMIN"
        normalize_role("medico")       -> "DOCTOR"
        normalize_role(None)           -> ""
    """
    if role is None:
        return ""
    raw = _NON_ALNUM.sub("_", str(role).strip().upper()).strip("_")
    if not raw:
        return ""
    return _ALIASES.get(raw, raw)


def has_role(user: object, allowed: Iterable[str]) -> bool:
    """Devuelve True si el usuario tiene alguno de los roles permitidos.

    `user` puede ser un modelo User, un dict o cualquier objeto con
    atributo `role`. Un rol `None` (usuario sin role asignado) nunca pasa.
    """
    role = getattr(user, "role", None)
    if role is None and isinstance(user, dict):
        role = user.get("role")
    # `role` puede ser un objeto Role (con .name) o un string suelto.
    name = getattr(role, "name", role)
    actual = normalize_role(name)
    if not actual:
        return False
    permitidos = {normalize_role(r) for r in allowed}
    return actual in permitidos


# --- UUIDs deterministas de los roles canonicos ---------------------------
# Necesarios para.seedear roles de forma idempotente sin depender del orden
# de insercion. El prefijo conserva el rango reservado que usa init.sql.
_ROLE_UUID_PREFIX = "00000000-0000-0000-0000-00000000"
ROLE_IDS: dict[str, uuid.UUID] = {
    SUPER_ADMIN: uuid.UUID(f"{_ROLE_UUID_PREFIX}0002"),
    ADMIN: uuid.UUID(f"{_ROLE_UUID_PREFIX}0003"),
    ASSISTANT: uuid.UUID(f"{_ROLE_UUID_PREFIX}0004"),
    DOCTOR: uuid.UUID(f"{_ROLE_UUID_PREFIX}0005"),
    SPECIALIST: uuid.UUID(f"{_ROLE_UUID_PREFIX}0006"),
    PATIENT: uuid.UUID(f"{_ROLE_UUID_PREFIX}0007"),
}

# Descripciones de los roles canonicos (para los seeds).
ROLES_CANONICOS: list[tuple[str, str, str]] = [
    (str(ROLE_IDS[SUPER_ADMIN]), SUPER_ADMIN, "Acceso total al sistema"),
    (str(ROLE_IDS[ADMIN]), ADMIN, "Administracion de la clinica"),
    (str(ROLE_IDS[ASSISTANT]), ASSISTANT, "Asistente: agenda y pacientes"),
    (str(ROLE_IDS[DOCTOR]), DOCTOR, "Medico responsable de sus citas"),
    (str(ROLE_IDS[SPECIALIST]), SPECIALIST, "Medico especialista"),
    (str(ROLE_IDS[PATIENT]), PATIENT, "Paciente: solo sus propias citas"),
]
