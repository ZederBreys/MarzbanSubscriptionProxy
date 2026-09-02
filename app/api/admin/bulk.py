from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.auth import get_current_admin
from app.services import bulk_service
from app.services.bulk_service import BulkError

router = APIRouter(prefix="/bulk", tags=["Bulk Operations"])


class DnsRequest(BaseModel):
    servers: list[str] = Field(..., min_length=1, max_length=20)


class DomainRequest(BaseModel):
    domain: str = Field(..., min_length=1)


@router.post("/dns")
async def update_dns(
    request: Request,
    body: DnsRequest,
    admin: dict = Depends(get_current_admin),
) -> dict:
    for srv in body.servers:
        if not srv.strip():
            raise HTTPException(status_code=400, detail="DNS server must not be empty")

    try:
        report = bulk_service.bulk_update_dns(
            servers=[s.strip() for s in body.servers],
            admin_login=admin["login"],
            ip_address=request.client.host if request.client else "",
        )
        return {"ok": True, **report}
    except BulkError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/domain/add")
async def add_domain(
    request: Request,
    body: DomainRequest,
    admin: dict = Depends(get_current_admin),
) -> dict:
    if not body.domain.strip():
        raise HTTPException(status_code=400, detail="Domain must not be empty")

    try:
        report = bulk_service.bulk_add_domain(
            domain_entry=body.domain.strip(),
            admin_login=admin["login"],
            ip_address=request.client.host if request.client else "",
        )
        return {"ok": True, **report}
    except BulkError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/domain/remove")
async def remove_domain(
    request: Request,
    body: DomainRequest,
    admin: dict = Depends(get_current_admin),
) -> dict:
    if not body.domain.strip():
        raise HTTPException(status_code=400, detail="Domain must not be empty")

    try:
        report = bulk_service.bulk_remove_domain(
            domain_entry=body.domain.strip(),
            admin_login=admin["login"],
            ip_address=request.client.host if request.client else "",
        )
        return {"ok": True, **report}
    except BulkError as e:
        raise HTTPException(status_code=400, detail=str(e))
