from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.auth import get_current_admin
from app.services import config_service
from app.services.config_service import ConfigError

router = APIRouter(prefix="/configs", tags=["Configs"])


class CreateConfigRequest(BaseModel):
    name: str
    template: Optional[str] = None
    json_content: Optional[dict] = Field(default=None, alias="json")


class UpdateConfigRequest(BaseModel):
    json_content: dict = Field(alias="json")


@router.get("")
async def list_configs(
    admin: dict = Depends(get_current_admin),
    search: str = Query("", description="Search by config name substring"),
    sort_by: str = Query("name", description="Sort column: name, users_count, size_bytes, modified_at"),
    order: str = Query("asc", description="Sort order: asc or desc"),
) -> dict:
    configs = config_service.list_configs(
        search=search,
        sort_by=sort_by,
        order=order,
    )
    return {"ok": True, "configs": configs}


@router.get("/{name}")
async def get_config(
    name: str,
    admin: dict = Depends(get_current_admin),
) -> dict:
    try:
        detail = config_service.get_config_detail(name)
        return {"ok": True, "config": detail}
    except ConfigError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("")
async def create_config(
    request: Request,
    body: CreateConfigRequest,
    admin: dict = Depends(get_current_admin),
) -> dict:
    try:
        result = config_service.create_config(
            name=body.name,
            template=body.template,
            json_data=body.json_content,
            admin_login=admin["login"],
            ip_address=request.client.host if request.client else "",
        )
        return {"ok": True, "config": result}
    except ConfigError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put("/{name}")
async def update_config(
    name: str,
    request: Request,
    body: UpdateConfigRequest,
    admin: dict = Depends(get_current_admin),
) -> dict:
    try:
        result = config_service.update_config(
            name=name,
            json_data=body.json_content,
            admin_login=admin["login"],
            ip_address=request.client.host if request.client else "",
        )
        return {"ok": True, "config": result}
    except ConfigError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.delete("/{name}")
async def delete_config(
    name: str,
    request: Request,
    admin: dict = Depends(get_current_admin),
) -> dict:
    try:
        result = config_service.delete_config(
            name=name,
            admin_login=admin["login"],
            ip_address=request.client.host if request.client else "",
        )
        return result
    except ConfigError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
