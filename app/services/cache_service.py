import threading
import time
from typing import Dict, Optional

config_cache: Dict[str, str] = {}
subscription_cache: Dict[str, dict] = {}
_cache_lock = threading.Lock()
_last_db_load: float = 0.0


def get_config(name: str) -> Optional[str]:
    return config_cache.get(name)


def config_exists(name: str) -> bool:
    return name in config_cache


def update_config_cache(new_cache: Dict[str, str]) -> None:
    config_cache.clear()
    config_cache.update(new_cache)


def get_subscription_from_cache(sub_id: str) -> Optional[dict]:
    with _cache_lock:
        return subscription_cache.get(sub_id)


def update_subscription_cache(new_cache: Dict[str, dict]) -> None:
    global _last_db_load
    with _cache_lock:
        subscription_cache.clear()
        subscription_cache.update(new_cache)
        _last_db_load = time.time()


def is_cache_stale(ttl_seconds: int) -> bool:
    return time.time() - _last_db_load > ttl_seconds
