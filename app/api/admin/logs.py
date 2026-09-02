from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.auth import get_current_admin
from app.services import log_service
from app.services.log_service import DEFAULT_LINES, LogError

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("")
async def list_logs_handler(
    admin: dict = Depends(get_current_admin),
) -> list[str]:
    return log_service.list_logs()


@router.get("/{name}")
async def read_log_handler(
    name: str,
    request: Request,
    admin: dict = Depends(get_current_admin),
    lines: int = Query(DEFAULT_LINES, description="Number of lines to read from the end of the file"),
) -> dict:
    try:
        return log_service.read_log(name, lines)
    except LogError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
