import json

from fastapi import APIRouter, Request, Response, HTTPException, Depends

from app.core.config import SESSION_TTL, SECURE_COOKIES
from app.core.auth import get_current_admin
from app.services.auth_service import (
    login as do_login,
    do_logout,
    do_logout_all,
    change_password as do_change_password,
    AuthError,
    RateLimitError,
)
from app.services.audit_service import log_action
from app.database.queries import get_admin_by_id

router = APIRouter(prefix="/auth", tags=["Auth"])


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    response.set_cookie(
        key="session_id",
        value=session_token,
        httponly=True,
        secure=SECURE_COOKIES,
        samesite="lax",
        path="/admin",
        max_age=SESSION_TTL,
    )
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        secure=SECURE_COOKIES,
        samesite="lax",
        path="/admin",
        max_age=SESSION_TTL,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("session_id", path="/admin")
    response.delete_cookie("csrf_token", path="/admin")


@router.post("/login")
async def login_route(request: Request, response: Response) -> dict:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    login_input = (body.get("login") or "").strip()
    password = body.get("password") or ""

    if not login_input or not password:
        raise HTTPException(status_code=400, detail="Login and password are required")

    ip = _client_ip(request)

    try:
        result = do_login(login_input, password, ip)
    except RateLimitError:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again later.")
    except AuthError as e:
        log_action(
            admin_login=login_input,
            action="LOGIN",
            object_type="admin",
            ip_address=ip,
            object_id=login_input,
            result="FAILURE",
            description="Invalid credentials",
        )
        raise HTTPException(status_code=e.status_code, detail="Invalid login or password.")

    _set_auth_cookies(response, result["session_token"], result["csrf_token"])

    log_action(
        admin_login=result["admin"]["login"],
        action="LOGIN",
        object_type="admin",
        ip_address=ip,
        object_id=result["admin"]["login"],
    )

    return {
        "ok": True,
        "admin": {
            "login": result["admin"]["login"],
            "last_login_at": result["admin"]["last_login_at"],
            "last_login_ip": result["admin"]["last_login_ip"],
        },
    }


@router.post("/logout")
async def logout_route(
    request: Request,
    response: Response,
    admin: dict = Depends(get_current_admin),
) -> dict:
    session_token = request.cookies.get("session_id", "")
    if session_token:
        do_logout(session_token)

    _clear_auth_cookies(response)

    log_action(
        admin_login=admin["login"],
        action="LOGOUT",
        object_type="admin",
        ip_address=_client_ip(request),
        object_id=admin["login"],
    )

    return {"ok": True}


@router.post("/logout-all")
async def logout_all_route(
    request: Request,
    response: Response,
    admin: dict = Depends(get_current_admin),
) -> dict:
    count = do_logout_all(admin["id"])
    _clear_auth_cookies(response)

    log_action(
        admin_login=admin["login"],
        action="LOGOUT_ALL",
        object_type="admin",
        ip_address=_client_ip(request),
        object_id=admin["login"],
        description=f"Deleted {count} sessions",
    )

    return {"ok": True, "sessions_deleted": count}


@router.get("/profile")
async def profile_route(
    request: Request,
    admin: dict = Depends(get_current_admin),
) -> dict:
    admin_data = get_admin_by_id(admin["id"])
    return {
        "login": admin_data["login"],
        "last_login_at": admin_data["last_login_at"],
        "last_login_ip": admin_data["last_login_ip"],
        "created_at": admin_data["created_at"],
    }


@router.post("/change-password")
async def change_password_route(
    request: Request,
    response: Response,
    admin: dict = Depends(get_current_admin),
) -> dict:
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    old_password = body.get("old_password") or ""
    new_password = body.get("new_password") or ""

    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="Old and new password are required")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    try:
        do_change_password(admin["id"], old_password, new_password)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    # Invalidate all sessions including current
    do_logout_all(admin["id"])
    _clear_auth_cookies(response)

    log_action(
        admin_login=admin["login"],
        action="CHANGE_PASSWORD",
        object_type="admin",
        ip_address=_client_ip(request),
        object_id=admin["login"],
    )

    return {"ok": True}
