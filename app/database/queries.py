import time
from typing import List, Optional, Tuple

from app.database.connection import get_connection


def fetch_all_subscriptions() -> List[Tuple[str, str, str | None, int | None]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sud_id, config, profile_title, profile_update_interval "
            "FROM subscription_url"
        )
        return cursor.fetchall()


def fetch_subscription_by_id(sud_id: str) -> Optional[Tuple[str, str, str | None, int | None]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sud_id, config, profile_title, profile_update_interval "
            "FROM subscription_url WHERE sud_id = ?",
            (sud_id,),
        )
        return cursor.fetchone()


def search_subscriptions(
    sud_id_search: str,
    config_filter: str,
    sort_column: str,
    sort_order: str,
) -> List[Tuple[str, str, str | None, int | None]]:
    ALLOWED_SORT_COLUMNS = {"sud_id", "config", "profile_title", "profile_update_interval"}
    if sort_column not in ALLOWED_SORT_COLUMNS:
        sort_column = "sud_id"
    if sort_order not in ("ASC", "DESC"):
        sort_order = "ASC"

    with get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT sud_id, config, profile_title, profile_update_interval FROM subscription_url WHERE 1=1"
        params: list = []

        if sud_id_search:
            query += " AND sud_id LIKE ?"
            params.append(f"%{sud_id_search}%")

        if config_filter:
            query += " AND config = ?"
            params.append(config_filter)

        query += f" ORDER BY {sort_column} {sort_order}"
        cursor.execute(query, params)
        return cursor.fetchall()


def insert_subscription(
    sud_id: str,
    config: str,
    profile_title: str | None,
    profile_update_interval: int,
) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO subscription_url "
            "(sud_id, config, profile_title, profile_update_interval) "
            "VALUES (?, ?, ?, ?)",
            (sud_id, config, profile_title, profile_update_interval),
        )
        conn.commit()


def update_subscription(
    current_sud_id: str,
    new_sud_id: str,
    config: str,
    profile_title: str | None,
    profile_update_interval: int,
) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE subscription_url SET "
            "sud_id = ?, config = ?, profile_title = ?, profile_update_interval = ? "
            "WHERE sud_id = ?",
            (new_sud_id, config, profile_title, profile_update_interval, current_sud_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def count_users_with_config(config: str, exclude_sud_id: str | None = None) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        if exclude_sud_id:
            cursor.execute(
                "SELECT COUNT(*) FROM subscription_url WHERE config = ? AND sud_id != ?",
                (config, exclude_sud_id),
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM subscription_url WHERE config = ?",
                (config,),
            )
        return cursor.fetchone()[0]


def delete_subscription(sud_id: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM subscription_url WHERE sud_id = ?",
            (sud_id,),
        )
        conn.commit()
        return cursor.rowcount > 0


def get_admin_by_login(login: str) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, login, password_hash, last_login_at, last_login_ip, created_at "
            "FROM admin_users WHERE login = ?",
            (login,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "login": row[1],
                "password_hash": row[2],
                "last_login_at": row[3],
                "last_login_ip": row[4],
                "created_at": row[5],
            }
        return None


def get_admin_by_id(admin_id: int) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, login, password_hash, last_login_at, last_login_ip, created_at "
            "FROM admin_users WHERE id = ?",
            (admin_id,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "login": row[1],
                "password_hash": row[2],
                "last_login_at": row[3],
                "last_login_ip": row[4],
                "created_at": row[5],
            }
        return None


def update_admin_last_login(admin_id: int, ip_address: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE admin_users SET last_login_at = ?, last_login_ip = ? WHERE id = ?",
            (time.time(), ip_address, admin_id),
        )
        conn.commit()


def update_admin_password(admin_id: int, password_hash: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE admin_users SET password_hash = ? WHERE id = ?",
            (password_hash, admin_id),
        )
        conn.commit()


def create_session(
    session_hash: str,
    admin_id: int,
    ip_address: str,
    csrf_token_hash: str,
    expires_at: float,
) -> None:
    now = time.time()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO admin_sessions "
            "(session_hash, admin_id, ip_address, csrf_token_hash, expires_at, last_accessed_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_hash, admin_id, ip_address, csrf_token_hash, expires_at, now, now),
        )
        conn.commit()


def get_session_by_hash(session_hash: str) -> Optional[dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT s.session_hash, s.admin_id, s.ip_address, s.csrf_token_hash, "
            "s.expires_at, s.last_accessed_at, s.created_at, a.login "
            "FROM admin_sessions s "
            "JOIN admin_users a ON s.admin_id = a.id "
            "WHERE s.session_hash = ?",
            (session_hash,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "session_hash": row[0],
                "admin_id": row[1],
                "ip_address": row[2],
                "csrf_token_hash": row[3],
                "expires_at": row[4],
                "last_accessed_at": row[5],
                "created_at": row[6],
                "admin_login": row[7],
            }
        return None


def update_session_access(
    session_hash: str, expires_at: float, last_accessed_at: float
) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE admin_sessions SET expires_at = ?, last_accessed_at = ? "
            "WHERE session_hash = ?",
            (expires_at, last_accessed_at, session_hash),
        )
        conn.commit()


def delete_session(session_hash: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM admin_sessions WHERE session_hash = ?",
            (session_hash,),
        )
        conn.commit()


def delete_sessions_for_admin(admin_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM admin_sessions WHERE admin_id = ?",
            (admin_id,),
        )
        conn.commit()
        return cursor.rowcount


def delete_expired_sessions() -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM admin_sessions WHERE expires_at < ?",
            (time.time(),),
        )
        conn.commit()
        return cursor.rowcount


def create_audit_record(
    admin_login: str,
    action: str,
    object_type: str,
    ip_address: str = "",
    object_id: str | None = None,
    old_value_json: str | None = None,
    new_value_json: str | None = None,
    description: str | None = None,
    result: str = "SUCCESS",
) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO admin_audit_log "
            "(timestamp, admin_login, ip_address, action, object_type, "
            "object_id, old_value_json, new_value_json, description, result) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                time.time(),
                admin_login,
                ip_address,
                action,
                object_type,
                object_id,
                old_value_json,
                new_value_json,
                description,
                result,
            ),
        )
        conn.commit()


def fetch_audit_records(
    page: int = 1,
    limit: int = 50,
    action: str | None = None,
    admin_login: str | None = None,
    result: str | None = None,
) -> tuple[list[dict], int]:
    with get_connection() as conn:
        cursor = conn.cursor()

        conditions: list[str] = []
        params: list = []

        if action:
            conditions.append("action = ?")
            params.append(action)
        if admin_login:
            conditions.append("admin_login LIKE ?")
            params.append(f"%{admin_login}%")
        if result:
            conditions.append("result = ?")
            params.append(result)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        cursor.execute(
            f"SELECT COUNT(*) FROM admin_audit_log {where_clause}",
            list(params),
        )
        total = cursor.fetchone()[0]

        offset = (page - 1) * limit
        params.append(limit)
        params.append(offset)
        cursor.execute(
            f"SELECT id, timestamp, admin_login, ip_address, action, object_type, "
            f"object_id, description, result "
            f"FROM admin_audit_log {where_clause} "
            f"ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params,
        )
        rows = cursor.fetchall()

        items: list[dict] = []
        for row in rows:
            items.append({
                "id": row[0],
                "timestamp": row[1],
                "admin_login": row[2],
                "ip_address": row[3],
                "action": row[4],
                "object_type": row[5],
                "object_id": row[6],
                "description": row[7],
                "result": row[8],
            })

        return items, total


def get_audit_by_id(audit_id: int) -> dict | None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, timestamp, admin_login, ip_address, action, object_type, "
            "object_id, old_value_json, new_value_json, description, result "
            "FROM admin_audit_log WHERE id = ?",
            (audit_id,),
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "timestamp": row[1],
                "admin_login": row[2],
                "ip_address": row[3],
                "action": row[4],
                "object_type": row[5],
                "object_id": row[6],
                "old_value_json": row[7],
                "new_value_json": row[8],
                "description": row[9],
                "result": row[10],
            }
        return None
