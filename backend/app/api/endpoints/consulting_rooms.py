from core import crud_consulting_room
from core.db import get_db
from fastapi import APIRouter, Depends, HTTPException
from schemas.consulting_room import (
    ConsultingRoomCreate,
    ConsultingRoomResponse,
    ConsultingRoomUpdate,
)
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/consulting-rooms", tags=["Consulting Rooms"])


@router.get("/", response_model=list[ConsultingRoomResponse])
async def list_consulting_rooms(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    return await crud_consulting_room.get_consulting_rooms(db, skip, limit)


@router.get("/{room_id}", response_model=ConsultingRoomResponse)
async def get_consulting_room(room_id: str, db: AsyncSession = Depends(get_db)):
    room = await crud_consulting_room.get_consulting_room(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Consulting room not found")
    return room


@router.post("/", response_model=ConsultingRoomResponse, status_code=201)
async def create_consulting_room(
    room: ConsultingRoomCreate, db: AsyncSession = Depends(get_db)
):
    return await crud_consulting_room.create_consulting_room(db, room)


@router.put("/{room_id}", response_model=ConsultingRoomResponse)
async def update_consulting_room(
    room_id: str, room: ConsultingRoomUpdate, db: AsyncSession = Depends(get_db)
):
    db_room = await crud_consulting_room.update_consulting_room(db, room_id, room)
    if not db_room:
        raise HTTPException(status_code=404, detail="Consulting room not found")
    return db_room


@router.delete("/{room_id}", status_code=204)
async def delete_consulting_room(room_id: str, db: AsyncSession = Depends(get_db)):
    db_room = await crud_consulting_room.delete_consulting_room(db, room_id)
    if not db_room:
        raise HTTPException(status_code=404, detail="Consulting room not found")
    return None
