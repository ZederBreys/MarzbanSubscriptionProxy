import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

TARGET_SERVICE_URL = os.environ.get("TARGET_SERVICE_URL", "http://127.0.0.1:8000")
PROXY_PORT = int(os.environ.get("PROXY_PORT", "8089"))
CONFIG_DIR = str(PROJECT_ROOT / "configs")
DB_PATH = str(PROJECT_ROOT / "subscriptions.db")
CACHE_TTL = 30

SESSION_TTL = 86400
SESSION_REFRESH_INTERVAL = 1800

BRUTE_FORCE_MAX_ATTEMPTS = 5
BRUTE_FORCE_WINDOW = 900

SECURE_COOKIES = os.environ.get("SECURE_COOKIES", "false").lower() == "true"

SESSION_CLEANUP_INTERVAL = 3600

LOG_FILES: dict[str, str] = {
    "requests": str(PROJECT_ROOT / "requests.log"),
    "responses": str(PROJECT_ROOT / "responses.log"),
    "app": str(PROJECT_ROOT / "app.log"),
    "admin": str(PROJECT_ROOT / "admin.log"),
}
