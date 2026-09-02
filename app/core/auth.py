import time

from fastapi import Request, Response, HTTPException, Depends

from app.core.security import hash_token
from app.core.config import SESSION_TTL, SECURE_COOKIES
from app.services.auth_service import (
    verify_session,
    refresh_session_if_needed,
    AuthError,
)


async def get_current_admin(request: Request, response: Response) -> dict:
    session_token = request.cookies.get("session_id")
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = verify_session(session_token)
    if not session:
        raise HTTPException(status_code=401, detail="Session invalid or expired")

    if refresh_session_if_needed(session["session_hash"], session["last_accessed_at"]):
        response.set_cookie(
            key="session_id",
            value=session_token,
            httponly=True,
            secure=SECURE_COOKIES,
            samesite="lax",
            path="/admin",
            max_age=SESSION_TTL,
        )
        csrf_token = request.cookies.get("csrf_token")
        if csrf_token:
            response.set_cookie(
                key="csrf_token",
                value=csrf_token,
                httponly=False,
                secure=SECURE_COOKIES,
                samesite="lax",
                path="/admin",
                max_age=SESSION_TTL,
            )

    return {
        "id": session["admin_id"],
        "login": session["admin_login"],
    }
