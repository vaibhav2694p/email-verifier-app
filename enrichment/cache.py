import hashlib
import threading
import time
from typing import Any, Optional


class EnrichmentCache:
    """Thread-safe TTL cache for enrichment results."""

    def __init__(self, default_ttl: int = 86400, max_size: int = 10000):
        self._store: dict = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl
        self._max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._store:
                entry = self._store[key]
                if entry["expires"] > time.time():
                    return entry["value"]
                del self._store[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        with self._lock:
            if len(self._store) >= self._max_size:
                self._evict_oldest()
            self._store[key] = {
                "value": value,
                "expires": time.time() + (ttl or self._default_ttl),
                "created": time.time(),
            }

    def get_or_set(self, key: str, factory, ttl: Optional[int] = None) -> Any:
        val = self.get(key)
        if val is not None:
            return val
        val = factory()
        self.set(key, val, ttl)
        return val

    def clear(self):
        with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        with self._lock:
            now = time.time()
            total = len(self._store)
            valid = sum(1 for v in self._store.values() if v["expires"] > now)
            return {"total": total, "valid": valid, "expired": total - valid}

    def _evict_oldest(self):
        if not self._store:
            return
        oldest_key = min(self._store, key=lambda k: self._store[k]["created"])
        del self._store[oldest_key]

    @staticmethod
    def make_key(*parts) -> str:
        raw = "|".join(str(p) for p in parts)
        return hashlib.md5(raw.encode()).hexdigest()
