from fastapi import APIRouter

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/status")
async def settings_status() -> dict:
    return {"module": "settings", "status": "ok"}
