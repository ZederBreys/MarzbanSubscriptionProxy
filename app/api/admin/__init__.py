from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.api.admin import auth, users, configs, logs, bulk, settings, audit

router = APIRouter(tags=["Admin"])


@router.get("/")
async def admin_redirect():
    return RedirectResponse(url="/admin/panel/")


router.include_router(auth.router)
router.include_router(users.router)
router.include_router(configs.router)
router.include_router(logs.router)
router.include_router(bulk.router)
router.include_router(settings.router)
router.include_router(audit.router)
