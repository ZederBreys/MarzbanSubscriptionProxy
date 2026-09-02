import json
import logging
from typing import Optional

from app.core.logging_setup import app_logger
from app.database.queries import (
    create_audit_record as _create_audit_record,
    fetch_audit_records as _fetch_audit_records,
    get_audit_by_id as _get_audit_by_id,
)


class AuditError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def log_action(
    admin_login: str,
    action: str,
    object_type: str,
    ip_address: str = "",
    object_id: str | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    description: str | None = None,
    result: str = "SUCCESS",
) -> None:
    old_json = json.dumps(old_value, ensure_ascii=False) if old_value else None
    new_json = json.dumps(new_value, ensure_ascii=False) if new_value else None

    try:
        _create_audit_record(
            admin_login=admin_login,
            ip_address=ip_address,
            action=action,
            object_type=object_type,
            object_id=object_id,
            old_value_json=old_json,
            new_value_json=new_json,
            description=description,
            result=result,
        )
    except Exception as e:
        app_logger.error(f"Failed to write audit record: {e}")


def list_audit(
    page: int = 1,
    limit: int = 50,
    action: str | None = None,
    admin_login: str | None = None,
    result: str | None = None,
) -> dict:
    items, total = _fetch_audit_records(
        page=page,
        limit=limit,
        action=action,
        admin_login=admin_login,
        result=result,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "limit": limit,
    }


def get_audit_detail(audit_id: int) -> dict:
    record = _get_audit_by_id(audit_id)
    if not record:
        raise AuditError("Audit record not found.", 404)
    return record
