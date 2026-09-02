import os
from typing import Optional

from app.core.config import LOG_FILES
from app.core.logging_setup import app_logger

ALLOWED_LOGS: frozenset[str] = frozenset(LOG_FILES.keys())
TAIL_BUFFER_SIZE: int = 8192
BYTES_PER_LINE_ESTIMATE: int = 2048
MIN_LINES: int = 1
MAX_LINES: int = 50000
DEFAULT_LINES: int = 500


class LogError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def list_logs() -> list[str]:
    return sorted(ALLOWED_LOGS)


def read_log(name: str, lines: int = DEFAULT_LINES) -> dict:
    if name not in ALLOWED_LOGS:
        raise LogError(f"Log '{name}' not found.", 404)

    if lines < MIN_LINES or lines > MAX_LINES:
        raise LogError(
            f"Lines must be between {MIN_LINES} and {MAX_LINES}. Got {lines}.",
            400,
        )

    filepath = LOG_FILES[name]
    content = _tail_file(filepath, lines)
    returned_lines = len(content.splitlines()) if content else 0

    return {
        "log": name,
        "requested_lines": lines,
        "returned_lines": returned_lines,
        "total_lines": None,
        "content": content,
    }


def _tail_file(filepath: str, num_lines: int) -> str:
    if not os.path.exists(filepath):
        raise LogError(f"Log '{filepath}' not found.", 404)

    max_bytes = max(num_lines * BYTES_PER_LINE_ESTIMATE, TAIL_BUFFER_SIZE * 16)

    try:
        with open(filepath, "rb") as f:
            file_size = f.seek(0, 2)
            if file_size == 0:
                return ""

            lines_found = 0
            bytes_read = 0
            chunks: list[bytes] = []
            position = file_size
            target_newlines = num_lines + 1

            while position > 0 and lines_found < target_newlines and bytes_read < max_bytes:
                read_size = min(TAIL_BUFFER_SIZE, position)
                position -= read_size
                f.seek(position)
                chunk = f.read(read_size)
                chunks.append(chunk)
                lines_found += chunk.count(b"\n")
                bytes_read += read_size

            data = b"".join(reversed(chunks))
            lines = data.decode("utf-8", errors="replace").splitlines()

            if len(lines) > num_lines:
                lines = lines[-num_lines:]

            return "\n".join(lines)

    except OSError as e:
        app_logger.error(f"Failed to read log file {filepath}: {e}")
        raise LogError("Failed to read log file.", 500)
