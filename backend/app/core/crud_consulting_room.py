from models.consulting_room import ConsultingRoom as ConsultingRoomModel
from schemas.consulting_room import ConsultingRoomCreate as ConsultingRoomCreateSchema
from schemas.consulting_room import ConsultingRoomUpdate as ConsultingRoomUpdateSchema
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_consulting_room(
    db: AsyncSession, room_id: str
) -> ConsultingRoomModel | None:
    result = await db.execute(
        select(ConsultingRoomModel).filter(ConsultingRoomModel.id == room_id)
    )
    return result.scalars().first()


async def get_consulting_rooms(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[ConsultingRoomModel]:
    result = await db.execute(select(ConsultingRoomModel).offset(skip).limit(limit))
    return result.scalars().all()


async def create_consulting_room(
    db: AsyncSession, room: ConsultingRoomCreateSchema
) -> ConsultingRoomModel:
    db_room = ConsultingRoomModel(**room.model_dump())
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
