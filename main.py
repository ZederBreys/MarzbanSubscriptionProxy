import asyncio
from contextlib import asynccontextmanager

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import (
    PROXY_PORT,
    CONFIG_DIR,
    DB_PATH,
    CACHE_TTL,
    SESSION_CLEANUP_INTERVAL,
)
from app.core.logging_setup import setup_logging, app_logger
from app.database.connection import init_db
from app.database.queries import delete_expired_sessions
from app.services.config_service import load_configs_from_dir
from app.services.subscription_service import load_all_subscriptions_from_db
from app.api.admin import router as admin_router
from app.api.proxy import proxy_router
from app.middleware.csrf import CSRFMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware

setup_logging()


async def _cleanup_expired_sessions() -> None:
    while True:
        await asyncio.sleep(SESSION_CLEANUP_INTERVAL)
        try:
            count = delete_expired_sessions()
            if count > 0:
                app_logger.info(f"Cleaned up {count} expired sessions")
        except Exception as e:
            app_logger.error(f"Session cleanup failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    load_configs_from_dir()
    load_all_subscriptions_from_db()
    app.state.client = httpx.AsyncClient(
        timeout=30.0, follow_redirects=True, verify=False, trust_env=False
    )
    app.state.cleanup_task = asyncio.create_task(_cleanup_expired_sessions())
    yield
    app.state.cleanup_task.cancel()
    try:
        await app.state.cleanup_task
    except asyncio.CancelledError:
        pass
    await app.state.client.aclose()


app = FastAPI(lifespan=lifespan)

app.add_middleware(CSRFMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(admin_router, prefix="/admin")
app.mount("/admin/panel", StaticFiles(directory="frontend", html=True), name="frontend")
app.include_router(proxy_router)

if __name__ == "__main__":
    print("=" * 60)
    print("PROXY WITH IN-MEMORY CACHE (zero DB latency)")
    print(f"Port: {PROXY_PORT}")
    print(f"Configs: {CONFIG_DIR}/*.json")
    print(f"Database: {DB_PATH}")
    print(f"Cache auto-refresh every {CACHE_TTL} sec")
    print(f"Admin panel: http://127.0.0.1:{PROXY_PORT}/admin/panel/")
    print("=" * 60)
    uvicorn.run(app, host="127.0.0.1", port=PROXY_PORT, log_level="info")
