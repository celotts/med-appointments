from __future__ import annotations

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.branch import Branch
from .schemas import BranchCreate, BranchUpdate


async def get_branch(db: AsyncSession, branch_id: int) -> Optional[Branch]:
    result = await db.execute(select(Branch).where(Branch.id == branch_id))
    return result.scalar_one_or_none()


async def get_branches(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Branch]:
    result = await db.execute(select(Branch).offset(skip).limit(limit))
    return list(result.scalars().all())


async def create_branch(db: AsyncSession, branch_in: BranchCreate) -> Branch:
    db_branch = Branch(
        name=branch_in.name,
        address=branch_in.address,
        phone=branch_in.phone,
        email=branch_in.email,
        is_active=branch_in.is_active,
    )
    db.add(db_branch)
    await db.commit()
    await db.refresh(db_branch)
    return db_branch


async def update_branch(db: AsyncSession, branch_id: int, branch_in: BranchUpdate) -> Optional[Branch]:
    db_branch = await get_branch(db, branch_id)
    if not db_branch:
        return None
    update_data = branch_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_branch, field, value)
    await db.commit()
    await db.refresh(db_branch)
    return db_branch


async def delete_branch(db: AsyncSession, branch_id: int) -> bool:
    db_branch = await get_branch(db, branch_id)
    if not db_branch:
        return False
    await db.delete(db_branch)
    await db.commit()
    return True
