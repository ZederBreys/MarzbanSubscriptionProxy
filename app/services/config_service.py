import json
import logging
import os
from pathlib import Path

from app.core.config import CONFIG_DIR
from app.database.queries import count_users_with_config as _db_count_users_with_config
from app.services.cache_service import update_config_cache
from app.services.audit_service import log_action
from app.core.logging_setup import app_logger

ALLOWED_NAME_PATTERN = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


class ConfigError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def load_configs_from_dir() -> None:
    new_cache: dict[str, str] = {}
    config_dir = Path(CONFIG_DIR)
    if not config_dir.exists():
        config_dir.mkdir(parents=True, exist_ok=True)
        example_path = config_dir / "default.json"
        if not example_path.exists():
            with open(example_path, "w", encoding="utf-8") as f:
                json.dump({"example": "put your full config here"}, f, indent=2)
            logging.warning(f"Created example config at {example_path}. Please edit it.")

    for filepath in config_dir.iterdir():
        if filepath.suffix == ".json" and filepath.is_file():
            name = filepath.stem
            try:
                content = filepath.read_text(encoding="utf-8")
                json.loads(content)
                new_cache[name] = content
                logging.info(f"Loaded config: {name}")
            except Exception as e:
                logging.error(f"Failed to load {filepath.name}: {e}")

    update_config_cache(new_cache)
    logging.info(f"Total configs loaded: {len(new_cache)}")


def _validate_config_name(name: str) -> None:
    if not name or not name.strip():
        raise ConfigError("Config name is required.", 400)
    for char in name:
        if char not in ALLOWED_NAME_PATTERN:
            raise ConfigError(
                f"Invalid config name: '{name}'. "
                f"Allowed characters: A-Z, a-z, 0-9, _, -",
                400,
            )
    if name != name.strip():
        raise ConfigError("Config name must not contain leading or trailing spaces.", 400)


def _resolve_config_path(name: str) -> Path:
    config_dir = Path(CONFIG_DIR).resolve()
    file_path = (config_dir / f"{name}.json").resolve()
    try:
        file_path.relative_to(config_dir)
    except ValueError:
        raise ConfigError("Path traversal is not allowed.", 400)
    return file_path


def _validate_json(content: str) -> None:
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"Invalid JSON at line {e.lineno}, column {e.colno}: {e.msg}",
            400,
        )


def _atomic_write(filepath: Path, content: str) -> None:
    tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    tmp_path.replace(filepath)


def list_configs(
    search: str = "",
    sort_by: str = "name",
    order: str = "asc",
) -> list[dict]:
    ALLOWED_SORT = {"name", "users_count", "size_bytes", "modified_at"}
    if sort_by not in ALLOWED_SORT:
        sort_by = "name"
    reverse = order.lower() == "desc"

    config_dir = Path(CONFIG_DIR).resolve()
    configs: list[dict] = []

    for filepath in config_dir.iterdir():
        if filepath.suffix != ".json" or not filepath.is_file():
            continue

        name = filepath.stem
        if search and search.lower() not in name.lower():
            continue

        stat = filepath.stat()
        users_count = _db_count_users_with_config(name)

        configs.append({
            "name": name,
            "is_default": name == "default",
            "users_count": users_count,
            "size_bytes": stat.st_size,
            "modified_at": stat.st_mtime,
        })

    configs.sort(key=lambda c: c[sort_by], reverse=reverse)
    return configs


def get_config_detail(name: str) -> dict:
    _validate_config_name(name)
    filepath = _resolve_config_path(name)

    if not filepath.is_file():
        raise ConfigError(f"Config '{name}' not found.", 404)

    content = filepath.read_text(encoding="utf-8")
    users_count = _db_count_users_with_config(name)

    return {
        "name": name,
        "json": content,
        "users_count": users_count,
        "is_default": name == "default",
    }


def create_config(
    name: str,
    template: str | None,
    json_data: dict | None,
    admin_login: str,
    ip_address: str,
) -> dict:
    _validate_config_name(name)
    filepath = _resolve_config_path(name)

    if filepath.exists():
        raise ConfigError(f"Config '{name}' already exists.", 409)

    if template is not None:
        template_path = _resolve_config_path(template)
        if not template_path.is_file():
            raise ConfigError(f"Template config '{template}' not found.", 404)
        content = template_path.read_text(encoding="utf-8")
        try:
            final_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"Template config '{template}' contains invalid JSON "
                f"at line {e.lineno}, column {e.colno}: {e.msg}",
                400,
            )
    else:
        final_data = {}

    if json_data is not None:
        final_data = json_data

    new_content = json.dumps(final_data, indent=2, ensure_ascii=False)
    _atomic_write(filepath, new_content)
    load_configs_from_dir()

    log_action(
        admin_login=admin_login,
        ip_address=ip_address,
        action="CREATE_CONFIG",
        object_type="config",
        object_id=name,
        new_value={"json": new_content},
        description=f"Config '{name}' created from template '{template}'" if template else f"Config '{name}' created",
        result="SUCCESS",
    )

    app_logger.info(f"Config '{name}' created by {admin_login}")
    return {
        "name": name,
        "json": new_content,
    }


def update_config(
    name: str,
    json_data: dict,
    admin_login: str,
    ip_address: str,
) -> dict:
    _validate_config_name(name)
    filepath = _resolve_config_path(name)

    if not filepath.is_file():
        raise ConfigError(f"Config '{name}' not found.", 404)

    old_content = filepath.read_text(encoding="utf-8")
    new_content = json.dumps(json_data, indent=2, ensure_ascii=False)

    _validate_json(new_content)

    _atomic_write(filepath, new_content)
    load_configs_from_dir()

    log_action(
        admin_login=admin_login,
        ip_address=ip_address,
        action="EDIT_CONFIG",
        object_type="config",
        object_id=name,
        old_value={"json": old_content},
        new_value={"json": new_content},
        description=f"Config '{name}' edited",
        result="SUCCESS",
    )

    app_logger.info(f"Config '{name}' edited by {admin_login}")
    return {
        "name": name,
        "json": new_content,
    }


def delete_config(
    name: str,
    admin_login: str,
    ip_address: str,
) -> dict:
    _validate_config_name(name)

    if name == "default":
        raise ConfigError("Cannot delete the 'default' config. It is a protected system config.", 403)

    filepath = _resolve_config_path(name)

    if not filepath.is_file():
        raise ConfigError(f"Config '{name}' not found.", 404)

    users_count = _db_count_users_with_config(name)
    if users_count > 0:
        raise ConfigError(
            f"Cannot delete config '{name}'. It is used by {users_count} user(s). "
            f"Remove or reassign users first.",
            409,
        )

    old_content = filepath.read_text(encoding="utf-8")
    filepath.unlink()
    load_configs_from_dir()

    log_action(
        admin_login=admin_login,
        ip_address=ip_address,
        action="DELETE_CONFIG",
        object_type="config",
        object_id=name,
        old_value={"json": old_content},
        description=f"Config '{name}' deleted",
        result="SUCCESS",
    )

    app_logger.info(f"Config '{name}' deleted by {admin_login}")
    return {"name": name, "deleted": True}
