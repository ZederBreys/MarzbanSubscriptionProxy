from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.auth import get_current_admin
from app.services import subscription_service
from app.services.subscription_service import UserError

router = APIRouter(prefix="/users", tags=["Users"])


class CreateUserRequest(BaseModel):
    sud_id: str
    config: str = "default"
    profile_title: Optional[str] = None
    profile_update_interval: int = Field(default=12, ge=1)


class UpdateUserRequest(BaseModel):
    sud_id: Optional[str] = None
    config: Optional[str] = None
    profile_title: Optional[str] = None
    profile_update_interval: Optional[int] = Field(default=None, ge=1)


@router.get("")
async def list_users(
    admin: dict = Depends(get_current_admin),
    sort_by: str = Query("sud_id", description="Sort column"),
    order: str = Query("asc", description="Sort order: asc or desc"),
    search: str = Query("", description="Search by sud_id substring"),
    config: str = Query("", description="Filter by exact config name"),
) -> dict:
    return subscription_service.list_users(
        sort_by=sort_by,
        order=order,
        search=search,
        config_filter=config,
    )


@router.get("/{sud_id}")
async def get_user(
    sud_id: str,
    admin: dict = Depends(get_current_admin),
) -> dict:
    try:
        return subscription_service.get_user_by_id(sud_id)
    except UserError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("")
async def create_user(
    request: Request,
    body: CreateUserRequest,
    admin: dict = Depends(get_current_admin),
) -> dict:
    try:
        user = subscription_service.create_user(
            admin_login=admin["login"],
            ip_address=request.client.host if request.client else "",
            sud_id=body.sud_id,
            config=body.config,
            profile_title=body.profile_title,
            profile_update_interval=body.profile_update_interval,
        )
        return {"ok": True, "user": user}
    except UserError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put("/{sud_id}")
async def update_user(
    sud_id: str,
    request: Request,
    body: UpdateUserRequest,
    admin: dict = Depends(get_current_admin),
) -> dict:
    try:
        user = subscription_service.update_user_by_id(
            admin_login=admin["login"],
            ip_address=request.client.host if request.client else "",
            current_sud_id=sud_id,
            new_sud_id=body.sud_id,
            config=body.config,
            profile_title=body.profile_title,
            profile_update_interval=body.profile_update_interval,
        )
        return {"ok": True, "user": user}
    except UserError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/{sud_id}")
async def delete_user(
    sud_id: str,
    request: Request,
    admin: dict = Depends(get_current_admin),
    delete_config: bool = Query(False, description="Also delete associated JSON config"),
) -> dict:
    try:
        result = subscription_service.delete_user_by_id(
            admin_login=admin["login"],
            ip_address=request.client.host if request.client else "",
            sud_id=sud_id,
            delete_config=delete_config,
        )
        return result
    except UserError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
