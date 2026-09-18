from typing import Any, Optional

from dependencies import get_current_user, get_db
from dependencies_i18n import I18nResponse, get_language
from fastapi import APIRouter, Depends, Query
from schemas.visual_indicator import (
    VisualIndicatorConfig,
    VisualIndicatorConfigCreate,
    VisualIndicatorConfigUpdate,
)
from sqlalchemy.ext.asyncio import AsyncSession

from core import crud_visual_indicator
from models.user import User as UserModel

router = APIRouter(prefix="", tags=["Visual Indicators"])


@router.get(
    "/config",
    response_model=list[VisualIndicatorConfig],
    summary="Get all visual indicator configurations",
)
async def list_visual_config(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
) -> Any:
    """Get all visual indicator configurations."""
    i18n = I18nResponse(language)
    configs = await crud_visual_indicator.get_all_visual_configs(db)
    
    if is_active is not None:
        configs = [c for c in configs if c.is_active == is_active]
    
    return configs


@router.get(
    "/config/{code}",
    response_model=VisualIndicatorConfig,
    summary="Get a visual indicator configuration by code",
)
async def get_visual_config(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Get a visual indicator configuration by its code."""
    i18n = I18nResponse(language)
    config = await crud_visual_indicator.get_visual_config_by_code(db, code)
    if not config:
        raise i18n.error("visual_indicator_not_found", status_code=404)
    return config


@router.post(
    "/config",
    response_model=VisualIndicatorConfig,
    status_code=201,
    summary="Create a new visual indicator configuration",
)
async def create_visual_config(
    *,
    db: AsyncSession = Depends(get_db),
    config_in: VisualIndicatorConfigCreate,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Create a new visual indicator configuration."""
    i18n = I18nResponse(language)
    existing = await crud_visual_indicator.get_visual_config_by_code(db, config_in.code)
    if existing:
        raise i18n.error("visual_indicator_already_exists", status_code=400)
    return await crud_visual_indicator.create_visual_config(db, config_in)


@router.put(
    "/config/{code}",
    response_model=VisualIndicatorConfig,
    summary="Update a visual indicator configuration",
)
async def update_visual_config(
    *,
    db: AsyncSession = Depends(get_db),
    code: str,
    config_in: VisualIndicatorConfigUpdate,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> Any:
    """Update a visual indicator configuration."""
    i18n = I18nResponse(language)
    config = await crud_visual_indicator.get_visual_config_by_code(db, code)
    if not config:
        raise i18n.error("visual_indicator_not_found", status_code=404)
    return await crud_visual_indicator.update_visual_config(db, config, config_in)


@router.delete(
    "/config/{code}",
    summary="Delete a visual indicator configuration",
)
async def delete_visual_config(
    *,
    db: AsyncSession = Depends(get_db),
    code: str,
    current_user: UserModel = Depends(get_current_user),
    language: str = Depends(get_language),
) -> dict[str, str]:
    """Delete a visual indicator configuration."""
    i18n = I18nResponse(language)
    deleted = await crud_visual_indicator.delete_visual_config(db, code)
    if not deleted:
        raise i18n.error("visual_indicator_not_found", status_code=404)
    return {"detail": i18n.get("visual_indicator_deleted")}
