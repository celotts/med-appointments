from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.cita import Cita as CitaModel
from models.estado_cita import EstadoCita as EstadoCitaModel
from models.nota_medica import NotaMedica as NotaMedicaModel
from schemas.cita import (
    TRANSICIONES_VALIDAS,
    CitaCreate as CitaCreateSchema,
    CitaEstadoUpdate,
    CitaUpdate as CitaUpdateSchema,
    EstadoCitaCodigo,
    NotaMedicaCreate as NotaMedicaCreateSchema,
    NotaMedicaUpdate as NotaMedicaUpdateSchema,
)

# Estados que bloquean el horario del médico (impiden agendamiento en esa franja)
_ESTADOS_QUE_OCUPAN = (
    EstadoCitaCodigo.PENDIENTE.value,
    EstadoCitaCodigo.CONFIRMADA.value,
    EstadoCitaCodigo.REAGENDADA.value,
)

# Estados terminales: no se puede reagendar ni cambiar desde aquí
_ESTADOS_TERMINALES = (
    EstadoCitaCodigo.CANCELADA.value,
    EstadoCitaCodigo.COMPLETADA.value,
)


async def get_estado_by_codigo(
    db: AsyncSession, codigo: str | EstadoCitaCodigo
) -> EstadoCitaModel | None:
    value = codigo.value if isinstance(codigo, EstadoCitaCodigo) else codigo
    result = await db.execute(
        select(EstadoCitaModel).filter(EstadoCitaModel.codigo == value)
    )
    return result.scalars().first()


async def get_estado_by_id(db: AsyncSession, estado_id: int) -> EstadoCitaModel | None:
    return await db.get(EstadoCitaModel, estado_id)


async def get_estados(db: AsyncSession) -> list[EstadoCitaModel]:
    result = await db.execute(
        select(EstadoCitaModel).order_by(EstadoCitaModel.id)
    )
    return result.scalars().all()


async def get_cita(db: AsyncSession, cita_id: int) -> CitaModel | None:
    result = await db.execute(
        select(CitaModel)
        .options(selectinload(CitaModel.estado))
        .where(CitaModel.id == cita_id)
    )
    return result.scalars().first()


async def get_citas(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    paciente_id: int | None = None,
    medico_id: int | None = None,
    estado: str | None = None,
) -> list[CitaModel]:
    stmt = select(CitaModel).options(
        selectinload(CitaModel.estado)
    ).order_by(CitaModel.fecha_hora_inicio.desc())
    if paciente_id is not None:
        stmt = stmt.where(CitaModel.paciente_id == paciente_id)
    if medico_id is not None:
        stmt = stmt.where(CitaModel.medico_id == medico_id)
    if estado is not None:
        sub = select(EstadoCitaModel.id).where(EstadoCitaModel.codigo == estado)
        stmt = stmt.where(CitaModel.estado_id.in_(sub))
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def _hay_conflicto(
    db: AsyncSession,
    *,
    medico_id: int,
    inicio: datetime,
    fin: datetime,
    excluir_cita_id: int | None = None,
) -> bool:
    """Verifica si un médico ya tiene una cita que se solapa en [inicio, fin)."""
    estados_que_ocupan = select(EstadoCitaModel.id).where(
        EstadoCitaModel.codigo.in_(_ESTADOS_QUE_OCUPAN)
    )
    stmt = select(CitaModel.id).where(
        CitaModel.medico_id == medico_id,
        CitaModel.estado_id.in_(estados_que_ocupan),
        CitaModel.fecha_hora_inicio < fin,
        CitaModel.fecha_hora_fin > inicio,
    )
    if excluir_cita_id is not None:
        stmt = stmt.where(CitaModel.id != excluir_cita_id)
    result = await db.execute(stmt.limit(1))
    return result.scalars().first() is not None


async def create_cita(db: AsyncSession, cita: CitaCreateSchema) -> CitaModel:
    if cita.fecha_hora_fin <= cita.fecha_hora_inicio:
        raise ValueError("fecha_hora_fin debe ser posterior a fecha_hora_inicio")
    if await _hay_conflicto(
        db,
        medico_id=cita.medico_id,
        inicio=cita.fecha_hora_inicio,
        fin=cita.fecha_hora_fin,
    ):
        raise ValueError("El médico ya tiene una cita en ese horario.")

    db_estado = await get_estado_by_codigo(db, EstadoCitaCodigo.PENDIENTE)
    if db_estado is None:
        raise ValueError("No existe el estado base PENDIENTE. Ejecutar la semilla de estados.")

    db_cita = CitaModel(
        paciente_id=cita.paciente_id,
        medico_id=cita.medico_id,
        estado_id=db_estado.id,
        fecha_hora_inicio=cita.fecha_hora_inicio,
        fecha_hora_fin=cita.fecha_hora_fin,
        motivo_consulta=cita.motivo_consulta,
    )
    db.add(db_cita)
    await db.commit()
    await db.refresh(db_cita)
    return await get_cita(db, db_cita.id)


async def reagendar_cita(
    db: AsyncSession, db_cita: CitaModel, cita: CitaUpdateSchema, *, nuevo_estado: bool = True
) -> CitaModel:
    """Reagenda una cita a una nueva franja horaria y la marca como REAGENDADA."""
    if db_cita.estado.codigo in _ESTADOS_TERMINALES:
        raise ValueError(
            "No se puede reagendar una cita cancelada o completada."
        )

    nueva_inicio = cita.fecha_hora_inicio or db_cita.fecha_hora_inicio
    nueva_fin = cita.fecha_hora_fin or db_cita.fecha_hora_fin
    if nueva_fin <= nueva_inicio:
        raise ValueError("fecha_hora_fin debe ser posterior a fecha_hora_inicio")

    if await _hay_conflicto(
        db,
        medico_id=db_cita.medico_id,
        inicio=nueva_inicio,
        fin=nueva_fin,
        excluir_cita_id=db_cita.id,
    ):
        raise ValueError("El médico ya tiene una cita en ese horario.")

    db_cita.fecha_hora_inicio = nueva_inicio
    db_cita.fecha_hora_fin = nueva_fin
    if cita.motivo_consulta:
        db_cita.motivo_consulta = cita.motivo_consulta

    if nuevo_estado:
        estado = await get_estado_by_codigo(db, EstadoCitaCodigo.REAGENDADA)
        if estado is None:
            raise ValueError("No existe el estado REAGENDADA.")
        db_cita.estado_id = estado.id

    await db.commit()
    await db.refresh(db_cita)
    return await get_cita(db, db_cita.id)


async def change_estado(
    db: AsyncSession, db_cita: CitaModel, cambio: CitaEstadoUpdate
) -> CitaModel:
    """Transiciona el estado de una cita siguiendo la máquina de estados."""
    actual = EstadoCitaCodigo(db_cita.estado.codigo)
    permitidas = TRANSICIONES_VALIDAS.get(actual, set())
    if cambio.estado not in permitidas:
        raise ValueError(
            f"Transición inválida de {actual.value} a {cambio.estado.value}."
        )

    destino = await get_estado_by_codigo(db, cambio.estado)
    if destino is None:
        raise ValueError(f"No existe el estado {cambio.estado.value}.")
    db_cita.estado_id = destino.id
    await db.commit()
    await db.refresh(db_cita)
    return await get_cita(db, db_cita.id)


async def update_cita(
    db: AsyncSession, db_cita: CitaModel, cita: CitaUpdateSchema
) -> CitaModel:
    if cita.fecha_hora_inicio is not None or cita.fecha_hora_fin is not None:
        nueva_inicio = cita.fecha_hora_inicio or db_cita.fecha_hora_inicio
        nueva_fin = cita.fecha_hora_fin or db_cita.fecha_hora_fin
        if nueva_fin <= nueva_inicio:
            raise ValueError("fecha_hora_fin debe ser posterior a fecha_hora_inicio")
        if await _hay_conflicto(
            db,
            medico_id=db_cita.medico_id,
            inicio=nueva_inicio,
            fin=nueva_fin,
            excluir_cita_id=db_cita.id,
        ):
            raise ValueError("El médico ya tiene una cita en ese horario.")

    data = cita.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_cita, field, value)
    await db.commit()
    await db.refresh(db_cita)
    return await get_cita(db, db_cita.id)


async def delete_cita(db: AsyncSession, db_cita: CitaModel) -> CitaModel:
    await db.delete(db_cita)
    await db.commit()
    return db_cita
