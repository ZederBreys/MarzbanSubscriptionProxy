import json
from pathlib import Path
from typing import Any

from app.core.config import CONFIG_DIR
from app.core.logging_setup import app_logger
from app.services.audit_service import log_action
from app.services.config_service import load_configs_from_dir, _atomic_write


class BulkError(Exception):
    pass


def _list_json_configs() -> list[Path]:
    config_dir = Path(CONFIG_DIR).resolve()
    return sorted(
        [p for p in config_dir.iterdir() if p.suffix == ".json" and p.is_file()],
        key=lambda p: p.stem,
    )


def _read_config(filepath: Path) -> dict[str, Any] | None:
    try:
        raw = filepath.read_text(encoding="utf-8")
        return json.loads(raw)
    except Exception:
        return None


def _build_report(
    configs: list[dict],
    processed: int,
) -> dict:
    modified = sum(1 for c in configs if c["status"] == "modified")
    skipped = sum(1 for c in configs if c["status"] == "skipped")
    failed = sum(1 for c in configs if c["status"] == "failed")
    return {
        "processed": processed,
        "modified": modified,
        "skipped": skipped,
        "failed": failed,
        "details": configs,
    }


def bulk_update_dns(
    servers: list[str],
    admin_login: str,
    ip_address: str,
) -> dict:
    details: list[dict] = []
    processed = 0

    for filepath in _list_json_configs():
        name = filepath.stem
        processed += 1

        data = _read_config(filepath)
        if data is None:
            details.append({"config": name, "status": "failed", "reason": "Invalid JSON"})
            continue

        if "dns" not in data:
            details.append({"config": name, "status": "failed", "reason": "DNS section not found"})
            continue

        data["dns"]["servers"] = servers
        new_content = json.dumps(data, indent=2, ensure_ascii=False)

        try:
            _atomic_write(filepath, new_content)
            details.append({"config": name, "status": "modified"})
        except Exception as e:
            details.append({"config": name, "status": "failed", "reason": str(e)})

    load_configs_from_dir()

    report = _build_report(details, processed)
    log_action(
        admin_login=admin_login,
        ip_address=ip_address,
        action="BULK_DNS_UPDATE",
        object_type="configs",
        new_value={"servers": servers},
        description=(
            f"DNS updated: {report['modified']} modified, "
            f"{report['skipped']} skipped, {report['failed']} failed"
        ),
        result="SUCCESS" if report["failed"] == 0 else "PARTIAL",
    )

    app_logger.info(
        f"BULK_DNS_UPDATE by {admin_login}: "
        f"{report['modified']} modified, {report['failed']} failed"
    )
    return report


def _find_domain_rules(data: dict) -> list[tuple[int, dict]]:
    """Find routing rules that contain a domain array. Returns list of (index, rule)."""
    rules = data.get("routing", {}).get("rules", [])
    results: list[tuple[int, dict]] = []
    for idx, rule in enumerate(rules):
        if isinstance(rule, dict) and "domain" in rule and isinstance(rule["domain"], list):
            results.append((idx, rule))
    return results


def bulk_add_domain(
    domain_entry: str,
    admin_login: str,
    ip_address: str,
) -> dict:
    details: list[dict] = []
    processed = 0

    for filepath in _list_json_configs():
        name = filepath.stem
        processed += 1

        data = _read_config(filepath)
        if data is None:
            details.append({"config": name, "status": "failed", "reason": "Invalid JSON"})
            continue

        domain_rules = _find_domain_rules(data)
        if not domain_rules:
            details.append({"config": name, "status": "skipped", "reason": "No routing.domain found"})
            continue

        already_exists = False
        for _, rule in domain_rules:
            if domain_entry in rule["domain"]:
                already_exists = True
                break

        if already_exists:
            details.append({"config": name, "status": "skipped", "reason": "Domain already exists"})
            continue

        for _, rule in domain_rules:
            rule["domain"].append(domain_entry)

        new_content = json.dumps(data, indent=2, ensure_ascii=False)

        try:
            _atomic_write(filepath, new_content)
            details.append({"config": name, "status": "modified"})
        except Exception as e:
            details.append({"config": name, "status": "failed", "reason": str(e)})

    load_configs_from_dir()

    report = _build_report(details, processed)
    log_action(
        admin_login=admin_login,
        ip_address=ip_address,
        action="BULK_ADD_DOMAIN",
        object_type="configs",
        new_value={"domain": domain_entry},
        description=(
            f"Domain '{domain_entry}' added: {report['modified']} modified, "
            f"{report['skipped']} skipped, {report['failed']} failed"
        ),
        result="SUCCESS" if report["failed"] == 0 else "PARTIAL",
    )

    app_logger.info(
        f"BULK_ADD_DOMAIN '{domain_entry}' by {admin_login}: "
        f"{report['modified']} modified, {report['failed']} failed"
    )
    return report


def bulk_remove_domain(
    domain_entry: str,
    admin_login: str,
    ip_address: str,
) -> dict:
    details: list[dict] = []
    processed = 0

    for filepath in _list_json_configs():
        name = filepath.stem
        processed += 1

        data = _read_config(filepath)
        if data is None:
            details.append({"config": name, "status": "failed", "reason": "Invalid JSON"})
            continue

        domain_rules = _find_domain_rules(data)
        if not domain_rules:
            details.append({"config": name, "status": "skipped", "reason": "No routing.domain found"})
            continue

        removed = False
        for _, rule in domain_rules:
            domain_list: list = rule["domain"]
            if domain_entry in domain_list:
                domain_list.remove(domain_entry)
                removed = True

        if not removed:
            details.append({"config": name, "status": "skipped", "reason": "Domain not found"})
            continue

        new_content = json.dumps(data, indent=2, ensure_ascii=False)

        try:
            _atomic_write(filepath, new_content)
            details.append({"config": name, "status": "modified"})
        except Exception as e:
            details.append({"config": name, "status": "failed", "reason": str(e)})

    load_configs_from_dir()

    report = _build_report(details, processed)
    log_action(
        admin_login=admin_login,
        ip_address=ip_address,
        action="BULK_REMOVE_DOMAIN",
        object_type="configs",
        old_value={"domain": domain_entry},
        description=(
            f"Domain '{domain_entry}' removed: {report['modified']} modified, "
            f"{report['skipped']} skipped, {report['failed']} failed"
        ),
        result="SUCCESS" if report["failed"] == 0 else "PARTIAL",
    )

    app_logger.info(
        f"BULK_REMOVE_DOMAIN '{domain_entry}' by {admin_login}: "
        f"{report['modified']} modified, {report['failed']} failed"
    )
    return report
