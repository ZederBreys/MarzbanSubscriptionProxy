import json
import logging
from pathlib import Path
from typing import Any, Optional

from app.core.config import CACHE_TTL, CONFIG_DIR
from app.core.logging_setup import app_logger
from app.database.queries import (
    fetch_all_subscriptions,
    fetch_subscription_by_id,
    insert_subscription,
    update_subscription,
    delete_subscription,
    search_subscriptions,
    count_users_with_config,
)
from app.services.cache_service import (
    get_subscription_from_cache,
    update_subscription_cache,
    config_exists,
    is_cache_stale,
)
from app.services.config_service import load_configs_from_dir
from app.services.audit_service import log_action


class UserError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def load_all_subscriptions_from_db() -> None:
    new_cache: dict[str, dict] = {}
    try:
        rows = fetch_all_subscriptions()
        for row in rows:
            new_cache[row[0]] = {
                "config": row[1],
                "profile_title": row[2],
                "profile_update_interval": row[3] if row[3] is not None else 12,
            }
    except Exception as e:
        app_logger.error(f"Failed to load subscriptions from DB: {e}")
        return

    update_subscription_cache(new_cache)
    app_logger.info(f"Loaded {len(new_cache)} subscriptions from DB")


def get_subscription_config(sub_id: str) -> Optional[dict]:
    if is_cache_stale(CACHE_TTL):
        load_all_subscriptions_from_db()
    return get_subscription_from_cache(sub_id)


def _validate_sud_id(sud_id: str) -> None:
    if not sud_id or not sud_id.strip():
        raise UserError("sud_id is required.")


def _validate_config(config_name: str) -> None:
    if not config_name:
        raise UserError("config is required.")
    if not config_exists(config_name):
        raise UserError(f"Config '{config_name}' does not exist.", 404)


def _validate_profile_title(title: Optional[str]) -> None:
    if title is not None and len(title) > 30:
        raise UserError("profile_title must not exceed 30 characters.")


def _validate_update_interval(interval: Optional[int]) -> None:
    if interval is not None and (not isinstance(interval, int) or interval < 1):
        raise UserError("profile_update_interval must be a positive integer.")


def _subscription_to_dict(row, config_val=None, title_val=None, interval_val=None):
    return {
        "sud_id": row[0],
        "config": row[1] if config_val is None else config_val,
        "profile_title": row[2] if title_val is None else title_val,
        "profile_update_interval": row[3] if interval_val is None else interval_val if row[3] is not None else 12,
    }


def list_users(
    sort_by: str = "sud_id",
    order: str = "asc",
    search: str = "",
    config_filter: str = "",
) -> dict:
    ALLOWED_SORT = {"sud_id", "config", "profile_title", "profile_update_interval"}
    if sort_by not in ALLOWED_SORT:
        sort_by = "sud_id"
    sort_order = "DESC" if order.lower() == "desc" else "ASC"

    rows = search_subscriptions(search, config_filter, sort_by, sort_order)

    users = []
    for row in rows:
        users.append({
            "sud_id": row[0],
            "config": row[1],
            "profile_title": row[2],
            "profile_update_interval": row[3] if row[3] is not None else 12,
        })

    return {
        "users": users,
        "total": len(users),
        "sort_by": sort_by,
        "order": order.lower(),
    }


def get_user_by_id(sud_id: str) -> dict:
    row = fetch_subscription_by_id(sud_id)
    if not row:
        raise UserError(f"User '{sud_id}' not found.", 404)
    return {
        "sud_id": row[0],
        "config": row[1],
        "profile_title": row[2],
        "profile_update_interval": row[3] if row[3] is not None else 12,
    }


def create_user(
    admin_login: str,
    ip_address: str,
    sud_id: str,
    config: str = "default",
    profile_title: Optional[str] = None,
    profile_update_interval: int = 12,
) -> dict:
    _validate_sud_id(sud_id)
    _validate_config(config)
    _validate_profile_title(profile_title)
    _validate_update_interval(profile_update_interval)

    existing = fetch_subscription_by_id(sud_id)
    if existing:
        raise UserError(f"User with sud_id '{sud_id}' already exists.", 409)

    insert_subscription(sud_id, config, profile_title, profile_update_interval)
    load_all_subscriptions_from_db()

    user = {
        "sud_id": sud_id,
        "config": config,
        "profile_title": profile_title,
        "profile_update_interval": profile_update_interval,
    }
    log_action(
        admin_login=admin_login,
        ip_address=ip_address,
        action="CREATE_USER",
        object_type="subscription",
        object_id=sud_id,
        new_value=user,
        result="SUCCESS",
    )
    app_logger.info(f"User '{sud_id}' created by {admin_login}")

    return user


def update_user_by_id(
    admin_login: str,
    ip_address: str,
    current_sud_id: str,
    new_sud_id: Optional[str] = None,
    config: Optional[str] = None,
    profile_title: Optional[str] = None,
    profile_update_interval: Optional[int] = None,
) -> dict:
    existing = fetch_subscription_by_id(current_sud_id)
    if not existing:
        raise UserError(f"User '{current_sud_id}' not found.", 404)

    old_user = {
        "sud_id": existing[0],
        "config": existing[1],
        "profile_title": existing[2],
        "profile_update_interval": existing[3] if existing[3] is not None else 12,
    }

    effective_sud_id = new_sud_id if new_sud_id is not None else old_user["sud_id"]
    effective_config = config if config is not None else old_user["config"]
    effective_title = profile_title if profile_title is not None else old_user["profile_title"]
    effective_interval = profile_update_interval if profile_update_interval is not None else old_user["profile_update_interval"]

    _validate_sud_id(effective_sud_id)
    _validate_config(effective_config)
    _validate_profile_title(effective_title)
    _validate_update_interval(effective_interval)

    if effective_sud_id != current_sud_id:
        conflict = fetch_subscription_by_id(effective_sud_id)
        if conflict:
            raise UserError(f"User with sud_id '{effective_sud_id}' already exists.", 409)

    updated = update_subscription(
        current_sud_id, effective_sud_id, effective_config, effective_title, effective_interval
    )
    if not updated:
        raise UserError("Failed to update user.", 500)

    load_all_subscriptions_from_db()

    new_user = {
        "sud_id": effective_sud_id,
        "config": effective_config,
        "profile_title": effective_title,
        "profile_update_interval": effective_interval,
    }
    log_action(
        admin_login=admin_login,
        ip_address=ip_address,
        action="EDIT_USER",
        object_type="subscription",
        object_id=effective_sud_id,
        old_value=old_user,
        new_value=new_user,
        result="SUCCESS",
    )
    app_logger.info(f"User '{current_sud_id}' updated to '{effective_sud_id}' by {admin_login}")

    return new_user


def delete_user_by_id(
    admin_login: str,
    ip_address: str,
    sud_id: str,
    delete_config: bool = False,
) -> dict:
    existing = fetch_subscription_by_id(sud_id)
    if not existing:
        raise UserError(f"User '{sud_id}' not found.", 404)

    user_config = existing[1]
    config_deleted = False
    config_skip_reason: str | None = None

    if delete_config and user_config == "default":
        config_skip_reason = (
            "Config 'default' is a system config; config file NOT deleted."
        )
    elif delete_config and user_config != "default":
        other_users = count_users_with_config(user_config, exclude_sud_id=sud_id)
        if other_users > 0:
            config_skip_reason = (
                f"Config '{user_config}' is used by {other_users} other user(s); "
                "config file NOT deleted."
            )
        else:
            config_dir = Path(CONFIG_DIR).resolve()
            config_path = (config_dir / f"{user_config}.json").resolve()
            try:
                config_path.relative_to(config_dir)
            except ValueError:
                raise UserError("Invalid config path.", 400)
            if config_path.exists():
                try:
                    config_path.unlink()
                    config_deleted = True
                    load_configs_from_dir()
                    app_logger.info(f"Config '{user_config}' deleted by {admin_login}")
                except Exception as e:
                    app_logger.error(f"Failed to delete config file '{user_config}': {e}")
                    raise UserError(f"Failed to delete config file: {e}", 500)

    deleted = delete_subscription(sud_id)
    if not deleted:
        raise UserError("Failed to delete user.", 500)

    load_all_subscriptions_from_db()

    old_user = {
        "sud_id": existing[0],
        "config": existing[1],
        "profile_title": existing[2],
        "profile_update_interval": existing[3] if existing[3] is not None else 12,
    }
    description = f"config_deleted={config_deleted}"
    if config_skip_reason:
        description += f"; {config_skip_reason}"

    log_action(
        admin_login=admin_login,
        ip_address=ip_address,
        action="DELETE_USER",
        object_type="subscription",
        object_id=sud_id,
        old_value=old_user,
        result="SUCCESS",
        description=description,
    )
    app_logger.info(f"User '{sud_id}' deleted by {admin_login}")

    return {"ok": True, "config_deleted": config_deleted}
