from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.security import secure_compare

EXCLUDED_CSRF_PATHS = (
    "/admin/auth/login",
    "/admin/auth/status",
)


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)

        path = request.url.path
        if not path.startswith("/admin/"):
            return await call_next(request)

        for excluded in EXCLUDED_CSRF_PATHS:
            if path.startswith(excluded):
                return await call_next(request)

        origin = request.headers.get("origin", "")
        referer = request.headers.get("referer", "")
        host = request.headers.get("host", "")

        if origin or referer:
            from urllib.parse import urlparse

            if origin:
                parsed_host = urlparse(origin).netloc
            else:
                parsed_host = urlparse(referer).netloc

            if parsed_host and parsed_host != host:
                return JSONResponse(
                    status_code=403, content={"detail": "Invalid origin"}
                )
        else:
            return JSONResponse(
                status_code=403, content={"detail": "Origin or Referer required"}
            )

        cookie_token = request.cookies.get("csrf_token")
        header_token = request.headers.get("x-csrf-token")

        if not cookie_token or not header_token:
            return JSONResponse(
                status_code=403, content={"detail": "CSRF token missing"}
            )

        if not secure_compare(cookie_token, header_token):
            return JSONResponse(
                status_code=403, content={"detail": "CSRF token mismatch"}
            )

        return await call_next(request)
