import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

req_logger = logging.getLogger("requests")
resp_logger = logging.getLogger("responses")
app_logger = logging.getLogger("app")
admin_logger = logging.getLogger("admin")


def setup_logging() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)

    requests_path = str(PROJECT_ROOT / "requests.log")
    responses_path = str(PROJECT_ROOT / "responses.log")
    app_path = str(PROJECT_ROOT / "app.log")
    admin_path = str(PROJECT_ROOT / "admin.log")

    req_handler = RotatingFileHandler(requests_path, maxBytes=10_000_000, backupCount=5)
    resp_handler = RotatingFileHandler(responses_path, maxBytes=10_000_000, backupCount=5)
    app_handler = RotatingFileHandler(app_path, maxBytes=10_000_000, backupCount=5)
    admin_handler = RotatingFileHandler(admin_path, maxBytes=10_000_000, backupCount=5)

    req_handler.setFormatter(logging.Formatter("%(asctime)s\n%(message)s\n" + "-" * 80))
    resp_handler.setFormatter(logging.Formatter("%(asctime)s\n%(message)s\n" + "-" * 80))
    app_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    admin_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    req_logger.addHandler(req_handler)
    resp_logger.addHandler(resp_handler)
    app_logger.addHandler(app_handler)
    admin_logger.addHandler(admin_handler)
