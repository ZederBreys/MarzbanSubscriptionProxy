from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.auth import get_current_admin
from app.services import audit_service
from app.services.audit_service import AuditError

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("")
async def list_audit_handler(
    request: Request,
    admin: dict = Depends(get_current_admin),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Records per page"),
    action: str = Query("", description="Filter by action type"),
    admin_login: str = Query("", alias="admin", description="Filter by admin login substring"),
    result: str = Query("", description="Filter by result"),
) -> dict:
    return audit_service.list_audit(
        page=page,
        limit=limit,
        action=action if action else None,
        admin_login=admin_login if admin_login else None,
        result=result if result else None,
    )


@router.get("/{audit_id}")
async def get_audit_handler(
    audit_id: int,
    request: Request,
    admin: dict = Depends(get_current_admin),
) -> dict:
    try:
        return audit_service.get_audit_detail(audit_id)
    except AuditError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
