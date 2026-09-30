"""Alcance de agenda: que citas puede ver cada usuario.

Este modulo resuelve la pregunta que ningun endpoint respondia: **"cuales son
las citas que le corresponden a este usuario?"**.

## El problema

`appointments.user_id` es quien **creo** la cita, no quien la **atiende**. Por eso
filtrar la agenda por `user_id` no da la agenda de un medico: un asistente que
agenda las citas de tres especialistas ve las tres, pero un especialista que
solo atiende las suyas ve las que el mismo creo, que suelen ser ninguna.

Ademas `users` no tiene `doctor_id` y `doctors` no tiene `user_id`. No hay
llave foranea entre ambos. El unico vinculo real es el correo:

    users.email  ==  doctors.email

que es UNIQUE en las dos tablas y es exactamente como las crea
`seed_large_dataset.py:221,253,282`.

## Por que no se migra el esquema

Anadir `doctors.user_id` seria el modelo correcto, pero este proyecto arrasta
un historial de migraciones que ya causo problemas (`alembic revision
--autogenerate` borro tablas no modeladas). Un cambio de esquema que solo
sirve para pintar un dashboard no justifies esa riesgo: el vinculo por correo
es un indice UNIQUE, ya existente, y no puede colisionar.

Si algun dia un medico cambia su correo, este modulo devuelve una agenda vacia
en lugar de la agenda de otro. Es el fallo seguro.

Ver `docs/SEGURIDAD.md` y `docs/IA_AGENTE.md`.
"""

from __future__ import annotations

import uuid

from models.appointment import Appointment as AppointmentModel
from models.assistant_specialist import AssistantSpecialist
from models.doctor import Doctor as DoctorModel
from models.user import User as UserModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core import rbac


async def doctor_id_de_usuario(db: AsyncSession, user: UserModel) -> int | None:
    """Devuelve el `doctors.id` de un usuario, o None si no es medico.

    Se resuelve por correo, que es el vinculo real entre `users` y `doctors`.
    """
    if not user.email:
        return None
    result = await db.execute(
        select(DoctorModel.id).where(DoctorModel.email == user.email).limit(1)
    )
    return result.scalar_one_or_none()


async def ids_de_especialistas_asignados(
    db: AsyncSession, user: UserModel
) -> list[int]:
    """Medicos que un asistente tiene asignados, como lista de `doctors.id`.

    `assistant_specialists` guarda UUIDs de `users`, no de `doctors`, asi que
    hace falta el salto: especialista (users.id) -> correo -> doctors.id.

    Un asistente sin asignaciones ve la agenda completa, que es lo que hacia
    el sistema antes de que existiera esta tabla.
    """
    result = await db.execute(
        select(AssistantSpecialist.specialist_id).where(
            AssistantSpecialist.assistant_id == user.id
        )
    )
    specialist_user_ids = [row for row in result.scalars().all()]
    if not specialist_user_ids:
        return []

    result = await db.execute(
        select(DoctorModel.id).where(DoctorModel.email.in_(await _correos(db, specialist_user_ids)))
    )
    return sorted(result.scalars().all())


async def _correos(db: AsyncSession, user_ids: list[uuid.UUID]) -> list[str]:
    """Correos de los usuarios indicados, en una sola consulta."""
    result = await db.execute(
        select(UserModel.email).where(UserModel.id.in_(user_ids))
    )
    return [row for row in result.scalars().all() if row]


async def alcance_de_agenda(db: AsyncSession, user: UserModel) -> set[int] | None:
    """Los `doctors.id` que este usuario puede ver, o None si ve todo.

    None significa "sin restriccion": es lo que devuelven los administradores.
    Una lista vacia significa "no puede ver ninguna agenda" y produce un
    dashboard honestamente vacio, que es preferible a uno que muestra las
    citas de otro.
    """
    if rbac.has_role(user, rbac.ADMIN_ROLES):
        return None

    if rbac.has_role(user, [rbac.ASSISTANT]):
        return set(await ids_de_especialistas_asignados(db, user))

    if rbac.has_role(user, [rbac.DOCTOR, rbac.SPECIALIST]):
        doctor_id = await doctor_id_de_usuario(db, user)
        return {doctor_id} if doctor_id else set()

    # PATIENT y cualquier rol no previsto: sin agenda clinica.
    return set()
