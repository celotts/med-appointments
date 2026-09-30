"""Auditoria de las notas medicas.

Las notas clinicas son el dato mas sensible del sistema: contienen
diagnostico, tratamiento y observaciones. A diferencia del estado de una cita,
que es un dato de agenda, cambiarlos altera lo que se sabe del paciente. Por eso
toda escritura sobre `medical_notes` queda registrada, y el contenido va
completo en el registro: un rastro que solo dice "cambió la nota" no sirve para
investigar nada.

## Por qué el contenido completo y no un hash

La primera version de este modulo guardaba solo `campos_modificados`. Es
insuficiente: si una nota se corrige y alguien pregunta seis meses despues que
decia antes, el hash no responde nada. Guardar el texto previo y el nuevo hace
la auditoría realmente utilizable.

El coste es duplicar datos clínicos en `audit_logs`. Es aceptable porque la
tabla vive en la misma base de datos y hereda su cifrado y su control de
acceso. Si el almacenamiento dejara de estar bajo control, habria que pasar a
un digest + deposito externo.

## Trampa de SQLAlchemy async

Igual que en `crud_appointment_audit.py`: toda lectura de atributo ORM va
ANTES del flush de la auditoria, o lanza `MissingGreenlet`.

Ver `docs/AUDITORIA.md`.
"""

from __future__ import annotations

import logging
from typing import Any

from core import crud_audit
from models.audit import AuditAction
from models.medical_note import MedicalNote as MedicalNoteModel
from models.user import User as UserModel
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

TABLA_NOTAS = "medical_notes"

CAMPOS_CLINICOS = ("diagnosis", "treatment", "observations")


def _contenido(nota: MedicalNoteModel) -> dict[str, Any]:
    """Snapshot del contenido clínico de una nota."""
    return {campo: getattr(nota, campo, None) for campo in CAMPOS_CLINICOS}


async def registrar_creacion(
    db: AsyncSession,
    db_note: MedicalNoteModel,
    *,
    actor: UserModel | None = None,
) -> None:
    """Audita la creacion de una nota.

    `from_state` es None: la nota no existia.
    """
    # Captura previa: despues del flush la sesion expira los objetos.
    note_id = db_note.id
    appointment_id = db_note.appointment_id
    actor_id = getattr(actor, "id", None)
    contenido = _contenido(db_note)

    await crud_audit.registrar(
        db,
        action=AuditAction.INSERT,
        table_name=TABLA_NOTAS,
        record_id=note_id,
        user_id=actor_id,
        old_value=None,
        new_value={
            "appointment_id": appointment_id,
            **contenido,
            "evento": "nota_creada",
        },
        reason="Nota clinica creada",
    )


async def registrar_actualizacion(
    db: AsyncSession,
    db_note: MedicalNoteModel,
    *,
    campos: dict[str, Any],
    valores_previos: dict[str, Any],
    actor: UserModel | None = None,
) -> None:
    """Audita la edicion de una nota, guardando antes y despues.

    `campos_modificados` solo lista las claves tocadas; `antes` y `despues`
    llevan el valor previo y el nuevo de cada una, para que el rastro sea
    utilizable en una investigacion.
    """
    # Captura previa obligatoria (ver nota de MissingGreenlet).
    note_id = db_note.id
    appointment_id = db_note.appointment_id
    actor_id = getattr(actor, "id", None)

    await crud_audit.registrar(
        db,
        action=AuditAction.UPDATE,
        table_name=TABLA_NOTAS,
        record_id=note_id,
        user_id=actor_id,
        old_value={
            "appointment_id": appointment_id,
            "antes": valores_previos,
        },
        new_value={
            "appointment_id": appointment_id,
            "despues": campos,
            "campos_modificados": sorted(campos),
            "evento": "nota_actualizada",
        },
        reason="Nota clinica modificada",
    )


async def registrar_borrado(
    db: AsyncSession,
    db_note: MedicalNoteModel,
    *,
    actor: UserModel | None = None,
) -> None:
    """Audita el borrado de una nota clinica.

    Se escribe antes del DELETE y se confirma con el: si se escribiera despues,
    el registro desapareceria junto con la nota que describe.
    """
    # Captura previa obligatoria (ver nota de MissingGreenlet).
    note_id = db_note.id
    appointment_id = db_note.appointment_id
    actor_id = getattr(actor, "id", None)
    contenido = _contenido(db_note)

    await crud_audit.registrar(
        db,
        action=AuditAction.DELETE,
        table_name=TABLA_NOTAS,
        record_id=note_id,
        user_id=actor_id,
        old_value={
            "appointment_id": appointment_id,
            **contenido,
        },
        new_value={"evento": "nota_borrada"},
        reason="Nota clinica eliminada",
    )
