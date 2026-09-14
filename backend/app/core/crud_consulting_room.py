import uuid

from models.consulting_room import ConsultingRoom as ConsultingRoomModel
from schemas.consulting_room import ConsultingRoomCreate as ConsultingRoomCreateSchema
from schemas.consulting_room import ConsultingRoomUpdate as ConsultingRoomUpdateSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_consulting_room(
    db: AsyncSession, room_id: str, user_id: uuid.UUID | None = None
) -> ConsultingRoomModel | None:
    stmt = select(ConsultingRoomModel).filter(ConsultingRoomModel.id == room_id)
    if user_id is not None:
        stmt = stmt.where(ConsultingRoomModel.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_consulting_rooms(
    db: AsyncSession, skip: int = 0, limit: int = 100, user_id: uuid.UUID | None = None
) -> list[ConsultingRoomModel]:
    stmt = select(ConsultingRoomModel).offset(skip).limit(limit)
    if user_id is not None:
        stmt = stmt.where(ConsultingRoomModel.user_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_consulting_room(
    db: AsyncSession, room: ConsultingRoomCreateSchema, user_id: uuid.UUID
) -> ConsultingRoomModel:
    db_room = ConsultingRoomModel(**room.model_dump(), user_id=user_id)
    db.add(db_room)
    await db.commit()
    await db.refresh(db_room)
    return db_room


async def update_consulting_room(
    db: AsyncSession, db_room: ConsultingRoomModel, room: ConsultingRoomUpdateSchema
) -> ConsultingRoomModel:
    data = room.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(db_room, field, value)
    await db.commit()
    await db.refresh(db_room)
    return db_room


async def delete_consulting_room(
    db: AsyncSession, room_id: str
) -> ConsultingRoomModel | None:
    result = await db.execute(
        select(ConsultingRoomModel).filter(ConsultingRoomModel.id == room_id)
    )
    db_room = result.scalars().first()
    if db_room:
        await db.delete(db_room)
        await db.commit()
    return db_room
