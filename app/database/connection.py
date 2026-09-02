import sqlite3
from contextlib import contextmanager
from typing import Generator

from app.core.config import DB_PATH
from app.database.models import (
    SUBSCRIPTION_URL_SCHEMA,
    ADMIN_USERS_SCHEMA,
    ADMIN_USERS_MIGRATIONS,
    ADMIN_SESSIONS_SCHEMA,
    ADMIN_SESSIONS_MIGRATIONS,
    ADMIN_SESSIONS_INDEXES,
    AUDIT_LOG_SCHEMA,
    AUDIT_LOG_MIGRATIONS,
    AUDIT_LOG_INDEXES,
)
from app.core.logging_setup import app_logger


def _safe_add_column(conn: sqlite3.Connection, sql: str) -> None:
    try:
        conn.execute(sql)
    except sqlite3.OperationalError:
        pass


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys = ON")

        conn.execute(SUBSCRIPTION_URL_SCHEMA)

        conn.execute(ADMIN_USERS_SCHEMA)
        for migration in ADMIN_USERS_MIGRATIONS:
            _safe_add_column(conn, migration)

        conn.execute(ADMIN_SESSIONS_SCHEMA)
        for migration in ADMIN_SESSIONS_MIGRATIONS:
            _safe_add_column(conn, migration)
        for idx in ADMIN_SESSIONS_INDEXES:
            conn.execute(idx)

        conn.execute(AUDIT_LOG_SCHEMA)
        for migration in AUDIT_LOG_MIGRATIONS:
            _safe_add_column(conn, migration)
        for idx in AUDIT_LOG_INDEXES:
            conn.execute(idx)

    app_logger.info("Database initialized.")


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()
